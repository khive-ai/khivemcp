"""
AutoMCP Testing Utilities

This module provides classes and utilities for testing AutoMCP servers.
It includes tools for verifying server functionality, connecting to servers,
and validating operation results.
"""

import asyncio
import contextlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    Union,
)

import anyio
import mcp.types as types
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import JSONRPCMessage, TextContent, Tool
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig


class VerificationResult:
    """Class to track test results."""

    def __init__(self, name: str):
        """Initialize with a test name.

        Args:
            name: Name of the test or test suite
        """
        self.name = name
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details = []

    def add_result(
        self, test_name: str, passed: bool, message: str = "", skipped: bool = False
    ):
        """Add a test result.

        Args:
            test_name: Name of the specific test
            passed: Whether the test passed
            message: Additional information about the test result
            skipped: Whether the test was skipped
        """
        if skipped:
            self.skipped += 1
            status = "SKIPPED"
        elif passed:
            self.passed += 1
            status = "PASSED"
        else:
            self.failed += 1
            status = "FAILED"

        self.details.append({"test": test_name, "status": status, "message": message})

    def summary(self) -> str:
        """Get a summary of the verification results."""
        return f"{self.name}: {self.passed} passed, {self.failed} failed, {self.skipped} skipped"

    def detailed_report(self) -> str:
        """Get a detailed report of the verification results."""
        report = [f"\n=== {self.name} ==="]
        for detail in self.details:
            report.append(f"{detail['status']}: {detail['test']}")
            if detail["message"]:
                report.append(f"  {detail['message']}")
        return "\n".join(report)


# Define a type for memory-based message streams
MessageStream = Tuple[
    MemoryObjectReceiveStream[JSONRPCMessage | Exception],
    MemoryObjectSendStream[JSONRPCMessage],
]


@contextlib.asynccontextmanager
async def create_client_server_memory_streams() -> (
    AsyncGenerator[Tuple[MessageStream, MessageStream], None]
):
    """
    Creates a pair of bidirectional memory streams for client-server communication.

    Returns:
        A tuple of (client_streams, server_streams) where each is a tuple of
        (read_stream, write_stream)
    """
    # Create streams for both directions
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream[
        JSONRPCMessage | Exception
    ](1)
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream[
        JSONRPCMessage | Exception
    ](1)

    client_streams = (server_to_client_receive, client_to_server_send)
    server_streams = (client_to_server_receive, server_to_client_send)

    async with (
        server_to_client_receive,
        client_to_server_send,
        client_to_server_receive,
        server_to_client_send,
    ):
        yield client_streams, server_streams


@contextlib.asynccontextmanager
async def create_connected_server_and_client(
    server: AutoMCPServer,
    read_timeout: Optional[float] = None,
) -> AsyncGenerator[Tuple[AutoMCPServer, ClientSession], None]:
    """
    Creates a ClientSession that is connected to a running AutoMCP server.

    Args:
        server: The AutoMCPServer instance to connect to
        read_timeout: Optional timeout for read operations (in seconds)

    Returns:
        A tuple of (server, client_session)
    """
    # Convert timeout to timedelta if provided
    read_timeout_timedelta = anyio.to_timedelta(read_timeout) if read_timeout else None

    async with create_client_server_memory_streams() as (
        client_streams,
        server_streams,
    ):
        client_read, client_write = client_streams
        server_read, server_write = server_streams

        # Create a cancel scope for the server task
        async with anyio.create_task_group() as tg:
            # Start the server's internal MCP server
            tg.start_soon(
                lambda: server.server.run(
                    server_read,
                    server_write,
                    InitializationOptions(
                        server_name=server.name,
                        server_version="1.0.0",
                        capabilities=server.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
            )

            try:
                # Create and initialize the client session
                async with ClientSession(
                    read_stream=client_read,
                    write_stream=client_write,
                    read_timeout_seconds=read_timeout_timedelta,
                ) as client_session:
                    await client_session.initialize()
                    yield server, client_session
            finally:
                tg.cancel_scope.cancel()


async def start_server_process(
    config_path: Path, timeout: float = 30.0
) -> Tuple[ClientSession, List[str]]:
    """
    Start an AutoMCP server in a separate process and connect to it.

    Args:
        config_path: Path to the server configuration file
        timeout: Operation timeout in seconds

    Returns:
        A tuple of (client_session, tool_names) where tool_names is a list of available tools
    """
    # Create server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "automcp.cli", "run", str(config_path), "--timeout", str(timeout)],
    )

    # Connect to the server using stdio
    read_stream, write_stream = await stdio_client(server_params).__aenter__()
    client = ClientSession(read_stream, write_stream)

    # Initialize the connection
    await client.initialize()

    # Get the list of available tools
    tools_result = await client.list_tools()
    tool_names = [tool.name for tool in tools_result.tools]

    return client, tool_names


class AutoMCPTester:
    """Class to test AutoMCP server functionality."""

    def __init__(self, verbose: bool = False):
        """Initialize the tester.

        Args:
            verbose: Whether to output detailed logs
        """
        self.verbose = verbose
        self.console = Console()
        self.results = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled.

        Args:
            message: The message to log
            level: Log level (INFO, ERROR, etc.)
        """
        if self.verbose or level == "ERROR":
            if level == "ERROR":
                self.console.print(f"[bold red][{level}][/bold red] {message}")
            else:
                self.console.print(f"[{level}] {message}")

    async def test_operation(
        self,
        client: ClientSession,
        operation_name: str,
        arguments: Dict[str, Any] = None,
        expected_content: Optional[str] = None,
        test_name: Optional[str] = None,
    ) -> VerificationResult:
        """Test a specific operation with the given arguments.

        Args:
            client: The connected client session
            operation_name: Name of the operation to test
            arguments: Arguments to pass to the operation
            expected_content: Optional content to verify in the response
            test_name: Optional custom test name

        Returns:
            A VerificationResult object with the test results
        """
        if arguments is None:
            arguments = {}

        display_name = test_name or f"{operation_name} operation"
        result = VerificationResult(display_name)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Testing {display_name}...", total=None)

            try:
                # Call the operation
                response = await client.call_tool(operation_name, arguments)

                # Get the text from the first content item
                response_text = response.content[0].text if response.content else ""

                # Check if we need to verify expected content
                if expected_content:
                    passed = expected_content in response_text
                    result.add_result(
                        display_name,
                        passed,
                        f"Expected '{expected_content}' in '{response_text}'",
                    )
                else:
                    # Just record the response if no expected content
                    result.add_result(
                        display_name,
                        True,
                        f"Response: '{response_text}'",
                    )

                self.log(f"{display_name} result: {response_text}")

            except Exception as e:
                result.add_result(display_name, False, str(e))
                self.log(f"{display_name} error: {e}", "ERROR")

            progress.update(task, completed=True)

        return result

    async def test_group(
        self, config_path: Union[str, Path], operations: List[Dict[str, Any]]
    ) -> List[VerificationResult]:
        """Test operations for a service group.

        Args:
            config_path: Path to the configuration file
            operations: List of dicts with operation details. Each dict should have:
                - 'name': operation name (including group prefix)
                - 'args': arguments to pass to the operation (optional)
                - 'expected': expected content in response (optional)
                - 'test_name': custom test name (optional)

        Returns:
            List of VerificationResult objects
        """
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.log(f"Testing group with config: {config_path}")
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Connecting to server...", total=None)

            try:
                # Start server and connect client
                client, tool_names = await start_server_process(config_path)

                # Add result for available tools
                tools_result = VerificationResult("Available Tools")
                tools_result.add_result(
                    "Tools list",
                    True,
                    f"Found tools: {', '.join(tool_names)}",
                )
                results.append(tools_result)
                self.log(f"Available tools: {tool_names}")

                # Update progress
                progress.update(task, description="Testing operations...")

                # Test each operation
                for op in operations:
                    op_result = await self.test_operation(
                        client,
                        op["name"],
                        op.get("args", {}),
                        op.get("expected"),
                        op.get("test_name"),
                    )
                    results.append(op_result)

            except Exception as e:
                group_result = VerificationResult("Group Test")
                group_result.add_result("Group server setup", False, str(e))
                self.log(f"Group server setup error: {e}", "ERROR")
                results.append(group_result)

            finally:
                progress.update(task, completed=True)

                # Close the client if it was opened
                if "client" in locals():
                    await client.shutdown()

        return results

    async def verify_operation_schema(
        self,
        client: ClientSession,
        operation_name: str,
        valid_args: Dict[str, Any],
        invalid_args: Dict[str, Any],
        test_name: Optional[str] = None,
    ) -> VerificationResult:
        """Verify that an operation correctly validates its schema.

        Args:
            client: The connected client session
            operation_name: Name of the operation to test
            valid_args: Arguments that should pass schema validation
            invalid_args: Arguments that should fail schema validation
            test_name: Optional custom test name

        Returns:
            A VerificationResult object with the schema validation test results
        """
        display_name = test_name or f"{operation_name} schema validation"
        result = VerificationResult(display_name)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Testing {display_name}...", total=None)

            # Test with valid arguments
            try:
                self.log(f"Testing {operation_name} with valid args: {valid_args}")
                response = await client.call_tool(operation_name, valid_args)

                # Get the text from the first content item
                response_text = response.content[0].text if response.content else ""

                result.add_result(
                    f"{operation_name} (valid args)",
                    True,
                    f"Valid arguments accepted. Response: '{response_text}'",
                )
                self.log(f"{operation_name} valid args result: {response_text}")

            except Exception as e:
                result.add_result(
                    f"{operation_name} (valid args)",
                    False,
                    f"Valid arguments rejected: {e}",
                )
                self.log(f"{operation_name} valid args error: {e}", "ERROR")

            # Test with invalid arguments
            try:
                self.log(f"Testing {operation_name} with invalid args: {invalid_args}")
                response = await client.call_tool(operation_name, invalid_args)

                # Get the text from the first content item
                response_text = response.content[0].text if response.content else ""

                # Check if the response indicates validation failure
                if (
                    "validation" in response_text.lower()
                    or "invalid" in response_text.lower()
                    or "error" in response_text.lower()
                ):
                    result.add_result(
                        f"{operation_name} (invalid args)",
                        True,
                        f"Invalid arguments correctly rejected with message: '{response_text}'",
                    )
                else:
                    result.add_result(
                        f"{operation_name} (invalid args)",
                        False,
                        f"Invalid arguments incorrectly accepted. Response: '{response_text}'",
                    )
                self.log(f"{operation_name} invalid args result: {response_text}")

            except Exception as e:
                error_str = str(e).lower()
                # Check if the exception is related to validation
                if (
                    "validation" in error_str
                    or "invalid" in error_str
                    or "schema" in error_str
                ):
                    result.add_result(
                        f"{operation_name} (invalid args)",
                        True,
                        f"Invalid arguments correctly rejected with error: {e}",
                    )
                    self.log(f"{operation_name} invalid args correctly rejected: {e}")
                else:
                    result.add_result(
                        f"{operation_name} (invalid args)",
                        False,
                        f"Invalid arguments rejected with unexpected error: {e}",
                    )
                    self.log(f"{operation_name} invalid args error: {e}", "ERROR")

            progress.update(task, completed=True)

        return result

    async def verify_operation_schemas(
        self, config_path: Union[str, Path], schema_tests: List[Dict[str, Any]]
    ) -> List[VerificationResult]:
        """Test schema validation for multiple operations.

        Args:
            config_path: Path to the configuration file
            schema_tests: List of dicts with schema test details. Each dict should have:
                - 'name': operation name (including group prefix)
                - 'valid_args': arguments that should pass schema validation
                - 'invalid_args': arguments that should fail schema validation
                - 'test_name': custom test name (optional)

        Returns:
            List of VerificationResult objects
        """
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.log(f"Testing schema validation with config: {config_path}")
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Connecting to server...", total=None)

            try:
                # Start server and connect client
                client, tool_names = await start_server_process(config_path)

                # Add result for available tools
                tools_result = VerificationResult("Available Tools")
                tools_result.add_result(
                    "Tools list",
                    True,
                    f"Found tools: {', '.join(tool_names)}",
                )
                results.append(tools_result)
                self.log(f"Available tools: {tool_names}")

                # Update progress
                progress.update(task, description="Testing schema validation...")

                # Test each operation's schema
                for test in schema_tests:
                    schema_result = await self.verify_operation_schema(
                        client,
                        test["name"],
                        test["valid_args"],
                        test["invalid_args"],
                        test.get("test_name"),
                    )
                    results.append(schema_result)

            except Exception as e:
                schema_result = VerificationResult("Schema Validation Test")
                schema_result.add_result("Schema validation setup", False, str(e))
                self.log(f"Schema validation setup error: {e}", "ERROR")
                results.append(schema_result)

            finally:
                progress.update(task, completed=True)

                # Close the client if it was opened
                if "client" in locals():
                    await client.shutdown()

        return results

    def print_results(self, results: Optional[List[VerificationResult]] = None):
        """Print test results in a formatted way.

        Args:
            results: Optional list of VerificationResult objects (uses self.results if None)
        """
        if results is None:
            results = self.results

        self.console.print("\n[bold]AutoMCP Test Results[/bold]", style="green")

        total_passed = sum(result.passed for result in results)
        total_failed = sum(result.failed for result in results)
        total_skipped = sum(result.skipped for result in results)

        # Create a table for the results
        from rich.table import Table

        table = Table(title="Test Results")
        table.add_column("Test Group", style="cyan")
        table.add_column("Passed", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Skipped", style="yellow")

        for result in results:
            table.add_row(
                result.name,
                str(result.passed),
                str(result.failed),
                str(result.skipped),
            )

        table.add_row(
            "Total",
            str(total_passed),
            str(total_failed),
            str(total_skipped),
            style="bold",
        )

        self.console.print(table)

        if self.verbose:
            for result in results:
                self.console.print(result.detailed_report())

        if total_failed > 0:
            self.console.print(
                "\n[bold red]⚠️  Some tests failed. See details above.[/bold red]"
            )
        else:
            self.console.print("\n[bold green]✅ All tests passed![/bold green]")
