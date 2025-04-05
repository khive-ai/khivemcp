#!/usr/bin/env python3
"""
AutoMCP Verification Script

This script provides a simple way for users to validate their AutoMCP installation.
It offers various commands to test different aspects of the AutoMCP configuration system.

Usage:
    python -m verification.verify_automcp single-group
    python -m verification.verify_automcp multi-group
    python -m verification.verify_automcp timeout --timeout 5.0
    python -m verification.verify_automcp schema
    python -m verification.verify_automcp all
"""

import asyncio
import platform
import sys
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add parent directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from automcp.types import GroupConfig, ServiceConfig

app = typer.Typer(
    help="AutoMCP Verification Script - Validate your AutoMCP installation",
    add_completion=False,
)
console = Console()


class VerificationResult:
    """Class to track verification results."""

    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details = []

    def add_result(
        self, test_name: str, passed: bool, message: str = "", skipped: bool = False
    ):
        """Add a test result."""
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


class AutoMCPVerifier:
    """Class to verify AutoMCP functionality."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.config_dir = Path(__file__).parent / "config"
        self.results = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose or level == "ERROR":
            if level == "ERROR":
                console.print(f"[bold red][{level}][/bold red] {message}")
            else:
                console.print(f"[{level}] {message}")

    def check_environment(self) -> VerificationResult:
        """Verify the Python environment and dependencies."""
        result = VerificationResult("Environment Verification")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
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

    async def test_example_group(self) -> VerificationResult:
        """Test the ExampleGroup functionality."""
        result = VerificationResult("ExampleGroup Verification")
        config_path = self.config_dir / "example_group.json"
        self.log(f"Testing example group with config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing ExampleGroup...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command="python",
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

                        has_hello_world = "example.hello_world" in tool_names
                        has_echo = "example.echo" in tool_names
                        has_count_to = "example.count_to" in tool_names

                        result.add_result(
                            "Available tools",
                            has_hello_world and has_echo and has_count_to,
                            f"Found tools: {', '.join(tool_names)}",
                        )
                        self.log(f"Available tools: {tool_names}")

                        # Test hello_world operation
                        try:
                            response = await client.call_tool("example.hello_world", {})
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected = "Hello, World!"
                            passed = expected in response_text
                            result.add_result(
                                "hello_world operation",
                                passed,
                                f"Expected '{expected}' in '{response_text}'",
                            )
                            self.log(f"hello_world result: {response_text}")
                        except Exception as e:
                            result.add_result("hello_world operation", False, str(e))
                            self.log(f"hello_world error: {e}", "ERROR")

                        # Test echo operation
                        try:
                            test_text = "Testing AutoMCP"
                            response = await client.call_tool(
                                "example.echo", {"text": test_text}
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected = f"Echo: {test_text}"
                            passed = expected in response_text
                            result.add_result(
                                "echo operation",
                                passed,
                                f"Expected '{expected}' in '{response_text}'",
                            )
                            self.log(f"echo result: {response_text}")
                        except Exception as e:
                            result.add_result("echo operation", False, str(e))
                            self.log(f"echo error: {e}", "ERROR")

                        # Test count_to operation
                        try:
                            test_number = 5
                            response = await client.call_tool(
                                "example.count_to", {"number": test_number}
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected = "1, 2, 3, 4, 5"
                            passed = expected in response_text
                            result.add_result(
                                "count_to operation",
                                passed,
                                f"Expected '{expected}' in '{response_text}'",
                            )
                            self.log(f"count_to result: {response_text}")
                        except Exception as e:
                            result.add_result("count_to operation", False, str(e))
                            self.log(f"count_to error: {e}", "ERROR")

            except Exception as e:
                result.add_result("Example group server setup", False, str(e))
                self.log(f"Example group server setup error: {e}", "ERROR")

            progress.update(task, completed=True)

        return result

    async def test_schema_group(self) -> VerificationResult:
        """Test the SchemaGroup functionality."""
        result = VerificationResult("SchemaGroup Verification")
        config_path = self.config_dir / "schema_group.json"
        self.log(f"Testing schema group with config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing SchemaGroup...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command="python",
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

                        has_greet_person = "schema.greet_person" in tool_names
                        has_repeat_message = "schema.repeat_message" in tool_names
                        has_process_list = "schema.process_list" in tool_names

                        result.add_result(
                            "Available schema tools",
                            has_greet_person
                            and has_repeat_message
                            and has_process_list,
                            f"Found tools: {', '.join(tool_names)}",
                        )
                        self.log(f"Available schema tools: {tool_names}")

                        # Test greet_person operation
                        try:
                            response = await client.call_tool(
                                "schema.greet_person",
                                {
                                    "name": "John Doe",
                                    "age": 30,
                                    "email": "john@example.com",
                                },
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected_parts = [
                                "Hello, John Doe!",
                                "You are 30 years old",
                                "john@example.com",
                            ]
                            passed = all(
                                part in response_text for part in expected_parts
                            )
                            result.add_result(
                                "greet_person operation",
                                passed,
                                f"Response: '{response_text}'",
                            )
                            self.log(f"greet_person result: {response_text}")
                        except Exception as e:
                            result.add_result("greet_person operation", False, str(e))
                            self.log(f"greet_person error: {e}", "ERROR")

                        # Test repeat_message operation
                        try:
                            response = await client.call_tool(
                                "schema.repeat_message", {"text": "Test", "repeat": 3}
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected = "Test Test Test"
                            passed = expected in response_text
                            result.add_result(
                                "repeat_message operation",
                                passed,
                                f"Expected '{expected}' in '{response_text}'",
                            )
                            self.log(f"repeat_message result: {response_text}")
                        except Exception as e:
                            result.add_result("repeat_message operation", False, str(e))
                            self.log(f"repeat_message error: {e}", "ERROR")

                        # Test process_list operation
                        try:
                            response = await client.call_tool(
                                "schema.process_list",
                                {
                                    "items": ["apple", "banana", "cherry"],
                                    "prefix": "Fruit:",
                                    "uppercase": True,
                                },
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected_parts = ["APPLE", "BANANA", "CHERRY", "Fruit:"]
                            passed = all(
                                part in response_text for part in expected_parts
                            )
                            result.add_result(
                                "process_list operation",
                                passed,
                                f"Response contains expected parts: {passed}",
                            )
                            self.log(f"process_list result: {response_text}")
                        except Exception as e:
                            result.add_result("process_list operation", False, str(e))
                            self.log(f"process_list error: {e}", "ERROR")

            except Exception as e:
                result.add_result("Schema group server setup", False, str(e))
                self.log(f"Schema group server setup error: {e}", "ERROR")

            progress.update(task, completed=True)

        return result

    async def test_timeout_group(self, timeout: float = 1.0) -> VerificationResult:
        """Test the TimeoutGroup functionality."""
        result = VerificationResult("TimeoutGroup Verification")
        config_path = self.config_dir / "timeout_group.json"
        self.log(f"Testing timeout group with config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing TimeoutGroup...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command="python",
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

                        has_sleep = "timeout.sleep" in tool_names
                        has_slow_counter = "timeout.slow_counter" in tool_names
                        has_cpu_intensive = "timeout.cpu_intensive" in tool_names

                        result.add_result(
                            "Available timeout tools",
                            has_sleep and has_slow_counter and has_cpu_intensive,
                            f"Found tools: {', '.join(tool_names)}",
                        )
                        self.log(f"Available timeout tools: {tool_names}")

                        # Test sleep operation that completes before timeout
                        try:
                            sleep_time = timeout / 5  # Use a fraction of the timeout
                            response = await client.call_tool(
                                "timeout.sleep", {"seconds": sleep_time}
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            expected = f"Slept for {sleep_time} seconds"
                            passed = expected in response_text
                            result.add_result(
                                "sleep operation (completes before timeout)",
                                passed,
                                f"Expected '{expected}' in '{response_text}'",
                            )
                            self.log(f"sleep result: {response_text}")
                        except Exception as e:
                            result.add_result(
                                "sleep operation (completes before timeout)",
                                False,
                                str(e),
                            )
                            self.log(f"sleep error: {e}", "ERROR")

                        # Test sleep operation that exceeds timeout
                        try:
                            sleep_time = timeout * 2  # Double the timeout
                            response = await client.call_tool(
                                "timeout.sleep", {"seconds": sleep_time}
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            # For the timeout test, we expect either "timeout" in the response or "Operation timed out"
                            has_timeout = (
                                "timeout" in response_text.lower()
                                or "operation timed out" in response_text.lower()
                            )
                            result.add_result(
                                "sleep operation (exceeds timeout)",
                                has_timeout,
                                f"Response: '{response_text}'",
                            )
                            self.log(f"sleep timeout result: {response_text}")
                        except Exception as e:
                            # If the exception is related to timeout, that's expected
                            if "timeout" in str(e).lower():
                                result.add_result(
                                    "sleep operation (exceeds timeout)",
                                    True,
                                    f"Expected timeout exception: {e}",
                                )
                                self.log(f"sleep timeout: got timeout exception")
                            else:
                                result.add_result(
                                    "sleep operation (exceeds timeout)", False, str(e)
                                )
                                self.log(f"sleep timeout error: {e}", "ERROR")

            except Exception as e:
                result.add_result("Timeout group server setup", False, str(e))
                self.log(f"Timeout group server setup error: {e}", "ERROR")

            progress.update(task, completed=True)

        return result

    async def test_multi_group_config(self) -> VerificationResult:
        """Test loading and using a multi-group configuration."""
        result = VerificationResult("Multi-Group Configuration Verification")
        config_path = self.config_dir / "multi_group.yaml"
        self.log(f"Testing multi-group config: {config_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing Multi-Group Configuration...", total=None)

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command="python",
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

                        # Check for tools from each group
                        has_example = any(
                            name.startswith("example.") for name in tool_names
                        )
                        has_schema = any(
                            name.startswith("schema.") for name in tool_names
                        )
                        has_timeout = any(
                            name.startswith("timeout.") for name in tool_names
                        )

                        result.add_result(
                            "Multi-group tools available",
                            has_example and has_schema and has_timeout,
                            f"Found example: {has_example}, schema: {has_schema}, timeout: {has_timeout}",
                        )
                        self.log(f"Multi-group tools: {tool_names}")

                        # Test one operation from each group
                        try:
                            # Example group
                            response = await client.call_tool("example.hello_world", {})
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            example_ok = "Hello, World!" in response_text
                            result.add_result(
                                "Multi-group example operation",
                                example_ok,
                                f"Response: '{response_text}'",
                            )
                            self.log(f"Multi-group example operation: {response_text}")

                            # Schema group
                            response = await client.call_tool(
                                "schema.greet_person",
                                {
                                    "name": "Jane Doe",
                                    "age": 25,
                                    "email": "jane@example.com",
                                },
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            schema_ok = (
                                "Jane Doe" in response_text and "25" in response_text
                            )
                            result.add_result(
                                "Multi-group schema operation",
                                schema_ok,
                                f"Response: '{response_text}'",
                            )
                            self.log(f"Multi-group schema operation: {response_text}")

                            # Timeout group
                            response = await client.call_tool(
                                "timeout.sleep", {"seconds": 0.1}
                            )
                            # Get the text from the first content item
                            response_text = (
                                response.content[0].text if response.content else ""
                            )
                            timeout_ok = "Slept for 0.1 seconds" in response_text
                            result.add_result(
                                "Multi-group timeout operation",
                                timeout_ok,
                                f"Response: '{response_text}'",
                            )
                            self.log(f"Multi-group timeout operation: {response_text}")

                        except Exception as e:
                            result.add_result("Multi-group operations", False, str(e))
                            self.log(f"Multi-group operations error: {e}", "ERROR")

            except Exception as e:
                result.add_result("Multi-group server setup", False, str(e))
                self.log(f"Multi-group server setup error: {e}", "ERROR")

            progress.update(task, completed=True)

        return result

    async def run_verification(
        self, test_type: str = "all", timeout: float = 1.0
    ) -> List[VerificationResult]:
        """Run verification tests based on the test type."""
        self.results = []

        # Always check the environment
        env_result = self.check_environment()
        self.results.append(env_result)

        # Run the requested tests
        if test_type in ["all", "single-group"]:
            console.print("\n[bold]Running single-group tests...[/bold]")
            example_result = await self.test_example_group()
            self.results.append(example_result)

        if test_type in ["all", "schema"]:
            console.print("\n[bold]Running schema validation tests...[/bold]")
            schema_result = await self.test_schema_group()
            self.results.append(schema_result)

        if test_type in ["all", "timeout"]:
            console.print(
                f"\n[bold]Running timeout tests (timeout={timeout}s)...[/bold]"
            )
            timeout_result = await self.test_timeout_group(timeout)
            self.results.append(timeout_result)

        if test_type in ["all", "multi-group"]:
            console.print("\n[bold]Running multi-group tests...[/bold]")
            multi_result = await self.test_multi_group_config()
            self.results.append(multi_result)

        return self.results

    def print_results(self):
        """Print the verification results."""
        console.print("\n[bold]AutoMCP Verification Results[/bold]", style="green")

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

        console.print(table)

        if self.verbose:
            for result in self.results:
                console.print(result.detailed_report())

        if total_failed > 0:
            console.print(
                "\n[bold red]⚠️  Some tests failed. See details above.[/bold red]"
            )
            console.print(
                "\nRecommendations:",
                style="yellow",
            )
            console.print("- Check that all required packages are installed correctly")
            console.print("- Verify that your AutoMCP configuration files are valid")
            console.print(
                "- Run with --verbose flag for more detailed error information"
            )
        else:
            console.print("\n[bold green]✅ All tests passed![/bold green]")
            console.print(
                "\nYour AutoMCP installation is working correctly.",
                style="green",
            )


@app.command()
def single_group(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """
    Verify single-group configuration loading.

    This command tests the basic functionality of loading and using a single ServiceGroup.
    It verifies that operations can be called and return the expected results.
    """
    console.print(Panel.fit("AutoMCP Single-Group Verification", style="green"))
    verifier = AutoMCPVerifier(verbose=verbose)
    asyncio.run(verifier.run_verification("single-group"))
    verifier.print_results()


@app.command()
def multi_group(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """
    Verify multi-group configuration loading.

    This command tests the ability to load and use multiple ServiceGroups from a single
    configuration file. It verifies that operations from all groups can be called.
    """
    console.print(Panel.fit("AutoMCP Multi-Group Verification", style="green"))
    verifier = AutoMCPVerifier(verbose=verbose)
    asyncio.run(verifier.run_verification("multi-group"))
    verifier.print_results()


@app.command()
def timeout(
    timeout: float = typer.Option(1.0, help="Timeout value in seconds"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Verify timeout functionality.

    This command tests the timeout handling in AutoMCP. It verifies that operations
    that complete before the timeout return successfully, and operations that exceed
    the timeout are interrupted.
    """
    console.print(
        Panel.fit(f"AutoMCP Timeout Verification (timeout={timeout}s)", style="green")
    )
    verifier = AutoMCPVerifier(verbose=verbose)
    asyncio.run(verifier.run_verification("timeout", timeout))
    verifier.print_results()


@app.command()
def schema(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """
    Verify schema validation.

    This command tests the Pydantic schema validation functionality in AutoMCP.
    It verifies that operations with schemas correctly validate input parameters.
    """
    console.print(Panel.fit("AutoMCP Schema Validation Verification", style="green"))
    verifier = AutoMCPVerifier(verbose=verbose)
    asyncio.run(verifier.run_verification("schema"))
    verifier.print_results()


@app.command()
def all(
    timeout: float = typer.Option(1.0, help="Timeout value in seconds"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Run a full verification of all aspects.

    This command runs all verification tests to provide a comprehensive validation
    of the AutoMCP installation.
    """
    console.print(Panel.fit("AutoMCP Full Verification", style="green"))
    verifier = AutoMCPVerifier(verbose=verbose)
    asyncio.run(verifier.run_verification("all", timeout))
    verifier.print_results()


if __name__ == "__main__":
    app()
