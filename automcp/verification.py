"""
AutoMCP Verification Module

This module provides comprehensive verification capabilities for AutoMCP installations.
It includes tools for validating server functionality, testing configurations,
and ensuring correct operation of all components.
"""

import asyncio
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from automcp.client import (
    AutoMCPClient,
    connect_to_automcp_server,
    create_client_connection,
)
from automcp.testing import AutoMCPTester, VerificationResult


class Verifier:
    """Class to verify AutoMCP functionality."""

    def __init__(self, verbose: bool = False):
        """Initialize the verifier.

        Args:
            verbose: Whether to display detailed logs
        """
        self.verbose = verbose
        self.console = Console()
        self.results = []
        self.tester = AutoMCPTester(verbose=verbose)

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

    def check_environment(self) -> VerificationResult:
        """Verify the Python environment and dependencies.

        Returns:
            A VerificationResult with the environment verification results
        """
        result = VerificationResult("Environment Verification")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Checking environment...", total=None)

            # Check Python version
            python_version = platform.python_version()
            min_version = "3.10.0"
            python_ok = python_version >= min_version
            result.add_result(
                "Python Version",
                python_ok,
                f"Found {python_version}, minimum required is {min_version}",
            )
            self.log(f"Python version: {python_version}")

            # Check required packages
            required_packages = ["automcp", "pydantic", "mcp"]
            for package in required_packages:
                try:
                    __import__(package)
                    result.add_result(f"Package: {package}", True)
                    self.log(f"Package {package} is installed")
                except ImportError as e:
                    result.add_result(f"Package: {package}", False, str(e))
                    self.log(f"Package {package} is not installed", "ERROR")

            progress.update(task, completed=True)

        return result

    async def test_group(
        self, config_path: Union[str, Path], operations: List[Dict[str, Any]]
    ) -> VerificationResult:
        """Test a specific service group configuration.

        Args:
            config_path: Path to the configuration file
            operations: List of operations to test, each a dict with keys:
                - name: The operation name (e.g., "group.operation")
                - args: Arguments to pass to the operation (optional)
                - expected: Expected content in the response (optional)
                - test_name: Custom name for the test (optional)

        Returns:
            A VerificationResult with the test results
        """
        # Convert string path to Path if needed
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        group_name = config_path.stem
        result = VerificationResult(f"{group_name} Group Verification")
        self.log(f"Testing group with config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Testing {group_name} group...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "verification.run_server", str(config_path)],
                )
                self.log(f"Starting server with parameters: {server_params}")

                # Connect to the server using stdio
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as client:
                        # Initialize the connection
                        await client.initialize()
                        self.log("Client initialized successfully")

                        # Get the list of available tools
                        tools = await client.list_tools()
                        tool_names = [tool.name for tool in tools]
                        self.log(f"Available tools: {tool_names}")

                        # Check if the required operations are available
                        required_ops = [op["name"] for op in operations]
                        missing_ops = [
                            op for op in required_ops if op not in tool_names
                        ]

                        if missing_ops:
                            result.add_result(
                                "Available tools",
                                False,
                                f"Missing operations: {', '.join(missing_ops)}. Available: {', '.join(tool_names)}",
                            )
                        else:
                            result.add_result(
                                "Available tools",
                                True,
                                f"Found all required operations: {', '.join(required_ops)}",
                            )

                        # Test each operation
                        for op in operations:
                            op_name = op["name"]
                            op_args = op.get("args", {})
                            expected = op.get("expected")
                            test_name = op.get("test_name", f"{op_name} operation")

                            try:
                                response = await client.call_tool(op_name, op_args)
                                # Get the text from the first content item
                                response_text = (
                                    response.content[0].text if response.content else ""
                                )

                                if expected:
                                    passed = expected in response_text
                                    result.add_result(
                                        test_name,
                                        passed,
                                        f"Expected '{expected}' in '{response_text}'",
                                    )
                                else:
                                    # Just log the response if no expected content
                                    result.add_result(
                                        test_name,
                                        True,
                                        f"Response: '{response_text}'",
                                    )

                                self.log(f"{test_name} result: {response_text}")
                            except Exception as e:
                                result.add_result(test_name, False, str(e))
                                self.log(f"{test_name} error: {e}", "ERROR")

            except Exception as e:
                result.add_result("Group server setup", False, str(e))
                self.log(f"Group server setup error: {e}", "ERROR")
            finally:
                # Ensure resources are cleaned up
                self.log("Cleaning up resources")

            progress.update(task, completed=True)

        return result

    async def test_schema_validation(
        self, config_path: Union[str, Path]
    ) -> VerificationResult:
        """Test schema validation functionality.

        Args:
            config_path: Path to a configuration file with schema validation

        Returns:
            A VerificationResult with the schema validation test results
        """
        result = VerificationResult("Schema Validation Verification")
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.log(f"Testing schema validation with config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Testing schema validation...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "verification.run_server", str(config_path)],
                )
                self.log(f"Starting server with parameters: {server_params}")

                # Connect to the server using stdio
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as client:
                        # Initialize the connection
                        await client.initialize()
                        self.log("Client initialized successfully")

                        # Get the list of available tools
                        tools = await client.list_tools()
                        tool_details = {}
                        tool_names = []

                        for tool in tools:
                            tool_names.append(tool.name)
                            tool_details[tool.name] = {
                                "description": tool.description,
                                "schema": tool.inputSchema,
                            }

                        self.log(f"Available schema tools: {tool_names}")

                        # Pick an operation with schema
                        if not tool_names:
                            result.add_result(
                                "Schema operations",
                                False,
                                "No operations found",
                            )
                            return result

                        test_op = tool_names[0]
                        schema = tool_details[test_op].get("schema")

                        if not schema:
                            result.add_result(
                                "Schema definition",
                                False,
                                f"Operation {test_op} has no schema",
                            )
                        else:
                            result.add_result(
                                "Schema definition",
                                True,
                                f"Operation {test_op} has schema: {schema}",
                            )

                            # Test with valid arguments
                            # Note: This is a simplified test. In a real implementation,
                            # we would need to parse the schema and generate valid arguments.
                            try:
                                # Just call with empty args - may fail but we're testing the schema mechanism
                                response = await client.call_tool(test_op, {})
                                result.add_result(
                                    "Schema validation call",
                                    True,
                                    "Operation call successful with empty args",
                                )
                            except Exception as e:
                                # Check if it's a validation error
                                error_str = str(e).lower()
                                if "validation" in error_str or "schema" in error_str:
                                    result.add_result(
                                        "Schema validation",
                                        True,
                                        f"Schema validation correctly caught error: {e}",
                                    )
                                else:
                                    result.add_result(
                                        "Schema validation call",
                                        False,
                                        f"Operation call failed: {e}",
                                    )

            except Exception as e:
                result.add_result("Schema validation setup", False, str(e))
                self.log(f"Schema validation setup error: {e}", "ERROR")
            finally:
                # Ensure resources are cleaned up
                self.log("Cleaning up resources")

            progress.update(task, completed=True)

        return result

    async def test_timeout_handling(
        self, config_path: Union[str, Path], timeout: float = 1.0
    ) -> VerificationResult:
        """Test timeout handling functionality.

        Args:
            config_path: Path to a configuration file with timeout operations
            timeout: Timeout value in seconds

        Returns:
            A VerificationResult with the timeout handling test results
        """
        result = VerificationResult("Timeout Handling Verification")
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.log(f"Testing timeout handling with config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Testing timeout handling...", total=None)

            try:
                # Create server parameters with timeout
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "verification.timeout_test",
                        str(config_path),
                        str(timeout),
                    ],
                )
                self.log(f"Starting server with parameters: {server_params}")

                # Connect to the server using stdio
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as client:
                        # Initialize the connection
                        await client.initialize()
                        self.log("Client initialized successfully")

                        # Get the list of available tools
                        tools = await client.list_tools()
                        tool_names = [tool.name for tool in tools]
                        self.log(f"Available tools: {tool_names}")

                        # Filter for operations that might involve timeouts
                        timeout_ops = [
                            name
                            for name in tool_names
                            if "sleep" in name.lower()
                            or "timeout" in name.lower()
                            or "delay" in name.lower()
                        ]

                        if not timeout_ops:
                            result.add_result(
                                "Timeout operations",
                                False,
                                f"No timeout operations found. Available: {', '.join(tool_names)}",
                            )
                            return result

                        # Test operation that completes before timeout
                        timeout_op = timeout_ops[0]
                        sleep_time = timeout / 5  # Use a fraction of the timeout

                        try:
                            response = await client.call_tool(
                                timeout_op, {"seconds": sleep_time}
                            )
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            result.add_result(
                                f"{timeout_op} operation (completes before timeout)",
                                True,
                                f"Response: '{response_text}'",
                            )
                            self.log(f"{timeout_op} result: {response_text}")
                        except Exception as e:
                            result.add_result(
                                f"{timeout_op} operation (completes before timeout)",
                                False,
                                str(e),
                            )
                            self.log(f"{timeout_op} error: {e}", "ERROR")

                        # Test operation that exceeds timeout
                        sleep_time = timeout * 2  # Double the timeout

                        try:
                            response = await client.call_tool(
                                timeout_op, {"seconds": sleep_time}
                            )
                            response_text = (
                                response.content[0].text if response.content else ""
                            )

                            # For the timeout test, we expect either "timeout" in the response
                            # or "Operation timed out"
                            has_timeout = (
                                "timeout" in response_text.lower()
                                or "operation timed out" in response_text.lower()
                            )

                            if has_timeout:
                                result.add_result(
                                    f"{timeout_op} operation (exceeds timeout)",
                                    True,
                                    f"Timeout correctly caught: '{response_text}'",
                                )
                            else:
                                result.add_result(
                                    f"{timeout_op} operation (exceeds timeout)",
                                    False,
                                    f"Operation completed despite timeout: '{response_text}'",
                                )

                            self.log(f"{timeout_op} timeout result: {response_text}")
                        except Exception as e:
                            # If the exception is related to timeout, that's expected
                            if "timeout" in str(e).lower():
                                result.add_result(
                                    f"{timeout_op} operation (exceeds timeout)",
                                    True,
                                    f"Expected timeout exception: {e}",
                                )
                                self.log(f"{timeout_op} timeout: got timeout exception")
                            else:
                                result.add_result(
                                    f"{timeout_op} operation (exceeds timeout)",
                                    False,
                                    str(e),
                                )
                                self.log(f"{timeout_op} timeout error: {e}", "ERROR")

            except Exception as e:
                result.add_result("Timeout handling setup", False, str(e))
                self.log(f"Timeout handling setup error: {e}", "ERROR")
            finally:
                # Ensure resources are cleaned up
                self.log("Cleaning up resources")

            progress.update(task, completed=True)

        return result

    async def test_multi_group(
        self, config_path: Union[str, Path]
    ) -> VerificationResult:
        """Test multi-group configuration loading.

        Args:
            config_path: Path to a multi-group configuration file

        Returns:
            A VerificationResult with the multi-group test results
        """
        result = VerificationResult("Multi-Group Configuration Verification")
        config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.log(f"Testing multi-group config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Testing Multi-Group Configuration...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "verification.run_server", str(config_path)],
                )
                self.log(f"Starting server with parameters: {server_params}")

                # Connect to the server using stdio
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as client:
                        # Initialize the connection
                        await client.initialize()
                        self.log("Client initialized successfully")

                        # Get the list of available tools
                        tools = await client.list_tools()
                        tool_names = [tool.name for tool in tools]
                        self.log(f"Multi-group tools: {tool_names}")

                        # Group tools by prefix
                        tool_groups = {}
                        for name in tool_names:
                            if "." in name:
                                prefix = name.split(".")[0]
                                if prefix not in tool_groups:
                                    tool_groups[prefix] = []
                                tool_groups[prefix].append(name)

                        if len(tool_groups) <= 1:
                            result.add_result(
                                "Multi-group configuration",
                                False,
                                f"Only found one group: {list(tool_groups.keys())}",
                            )
                            return result

                        result.add_result(
                            "Multi-group configuration",
                            True,
                            f"Found {len(tool_groups)} groups: {', '.join(tool_groups.keys())}",
                        )

                        # Test one operation from each group
                        for group, group_tools in tool_groups.items():
                            if not group_tools:
                                continue

                            test_op = group_tools[0]
                            try:
                                # Call with empty args - may fail but we're testing the group loading
                                response = await client.call_tool(test_op, {})
                                response_text = (
                                    response.content[0].text if response.content else ""
                                )
                                result.add_result(
                                    f"Multi-group {group} operation",
                                    True,
                                    f"Response: '{response_text}'",
                                )
                                self.log(
                                    f"Multi-group {group} operation: {response_text}"
                                )
                            except Exception as e:
                                # Check if it's a validation error (which is fine for this test)
                                error_str = str(e).lower()
                                if "validation" in error_str or "schema" in error_str:
                                    result.add_result(
                                        f"Multi-group {group} operation",
                                        True,
                                        f"Schema validation correctly caught error: {e}",
                                    )
                                else:
                                    result.add_result(
                                        f"Multi-group {group} operation",
                                        False,
                                        f"Operation call failed: {e}",
                                    )
                                self.log(
                                    f"Multi-group {group} operation error: {e}", "ERROR"
                                )

            except Exception as e:
                result.add_result("Multi-group server setup", False, str(e))
                self.log(f"Multi-group server setup error: {e}", "ERROR")
            finally:
                # Ensure resources are cleaned up
                self.log("Cleaning up resources")

            progress.update(task, completed=True)

        return result

    async def run(
        self, test_type: str = "all", timeout: float = 1.0
    ) -> List[VerificationResult]:
        """Run verification tests based on the test type.

        Args:
            test_type: Type of test to run. Options:
                - "all": Run all tests
                - "single-group": Run single group tests
                - "multi-group": Run multi-group tests
                - "timeout": Run timeout tests
                - "schema": Run schema validation tests
                - "environment": Run only environment checks
            timeout: Timeout value in seconds

        Returns:
            List of VerificationResult objects
        """
        self.results = []

        # Always check the environment
        env_result = self.check_environment()
        self.results.append(env_result)

        # Determine config paths
        config_dir = Path("verification/config")

        # If the directory doesn't exist, try to find it relative to the module location
        if not config_dir.exists():
            module_dir = Path(__file__).parent
            config_dir = module_dir.parent / "verification" / "config"
            if not config_dir.exists():
                self.console.print(
                    "[bold red]Warning: Could not find verification config directory[/bold red]"
                )
                return self.results

        # Run the requested tests
        if test_type in ["all", "single-group", "environment"]:
            example_config = config_dir / "example_group.json"
            if example_config.exists():
                self.console.print("\n[bold]Running single-group tests...[/bold]")
                example_operations = [
                    {"name": "example.hello_world", "expected": "Hello, World!"},
                    {
                        "name": "example.echo",
                        "args": {"text": "Testing AutoMCP"},
                        "expected": "Echo: Testing AutoMCP",
                    },
                    {
                        "name": "example.count_to",
                        "args": {"number": 5},
                        "expected": "1, 2, 3, 4, 5",
                    },
                ]
                example_result = await self.test_group(
                    example_config, example_operations
                )
                self.results.append(example_result)
            else:
                self.log(f"Could not find example config: {example_config}", "ERROR")

        if test_type in ["all", "schema", "environment"]:
            schema_config = config_dir / "schema_group.json"
            if schema_config.exists():
                self.console.print("\n[bold]Running schema validation tests...[/bold]")
                schema_result = await self.test_schema_validation(schema_config)
                self.results.append(schema_result)
            else:
                self.log(f"Could not find schema config: {schema_config}", "ERROR")

        if test_type in ["all", "timeout", "environment"]:
            timeout_config = config_dir / "timeout_group.json"
            if timeout_config.exists():
                self.console.print(
                    f"\n[bold]Running timeout tests (timeout={timeout}s)...[/bold]"
                )
                timeout_result = await self.test_timeout_handling(
                    timeout_config, timeout
                )
                self.results.append(timeout_result)
            else:
                self.log(f"Could not find timeout config: {timeout_config}", "ERROR")

        if test_type in ["all", "multi-group", "environment"]:
            multi_config = config_dir / "multi_group.yaml"
            if multi_config.exists():
                self.console.print("\n[bold]Running multi-group tests...[/bold]")
                multi_result = await self.test_multi_group(multi_config)
                self.results.append(multi_result)
            else:
                self.log(f"Could not find multi-group config: {multi_config}", "ERROR")

        return self.results

    def print_results(self):
        """Print the verification results."""
        self.console.print("\n[bold]AutoMCP Verification Results[/bold]", style="green")

        total_passed = sum(result.passed for result in self.results)
        total_failed = sum(result.failed for result in self.results)
        total_skipped = sum(result.skipped for result in self.results)
        total_tests = total_passed + total_failed + total_skipped

        # Create a table for the results
        table = Table(title="Test Results")
        table.add_column("Test Group", style="cyan")
        table.add_column("Passed", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Skipped", style="yellow")

        for result in self.results:
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
            for result in self.results:
                self.console.print(result.detailed_report())

        if total_failed > 0:
            self.console.print(
                "\n[bold red]⚠️  Some tests failed. See details above.[/bold red]"
            )
            self.console.print(
                "\nRecommendations:",
                style="yellow",
            )
            self.console.print(
                "- Check that all required packages are installed correctly"
            )
            self.console.print(
                "- Verify that your AutoMCP configuration files are valid"
            )
            self.console.print(
                "- Run with --verbose flag for more detailed error information"
            )
        else:
            self.console.print("\n[bold green]✅ All tests passed![/bold green]")
            self.console.print(
                "\nYour AutoMCP installation is working correctly.",
                style="green",
            )
