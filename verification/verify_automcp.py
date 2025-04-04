#!/usr/bin/env python3
"""
AutoMCP End-to-End Verification Script

This script performs comprehensive verification of the AutoMCP system,
testing various configurations and functionality.
"""

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Add parent directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.types import TextContent

from automcp.server import AutoMCPServer

# Import AutoMCP components
from automcp.types import GroupConfig

# Import verification groups
from verification.groups.example_group import ExampleGroup
from verification.groups.schema_group import SchemaGroup
from verification.groups.timeout_group import TimeoutGroup
from verification.schemas import ListProcessingSchema, MessageSchema, PersonSchema


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
            print(f"[{level}] {message}")

    def check_environment(self) -> VerificationResult:
        """Verify the Python environment and dependencies."""
        result = VerificationResult("Environment Verification")

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

        return result

    async def test_example_group(self) -> VerificationResult:
        """Test the ExampleGroup functionality."""
        result = VerificationResult("ExampleGroup Verification")

        # Create an instance of ExampleGroup
        group = ExampleGroup()

        # Test hello_world operation
        try:
            response = await group.hello_world()
            expected = "Hello, World!"
            passed = response == expected
            result.add_result(
                "hello_world operation",
                passed,
                f"Expected '{expected}', got '{response}'",
            )
            self.log(f"hello_world result: {response}")
        except Exception as e:
            result.add_result("hello_world operation", False, str(e))
            self.log(f"hello_world error: {e}", "ERROR")

        # Test echo operation
        try:
            test_text = "Testing AutoMCP"
            response = await group.echo(test_text)
            expected = f"Echo: {test_text}"
            passed = response == expected
            result.add_result(
                "echo operation", passed, f"Expected '{expected}', got '{response}'"
            )
            self.log(f"echo result: {response}")
        except Exception as e:
            result.add_result("echo operation", False, str(e))
            self.log(f"echo error: {e}", "ERROR")

        # Test count_to operation
        try:
            test_number = 5
            response = await group.count_to(test_number)
            expected = "1, 2, 3, 4, 5"
            passed = response == expected
            result.add_result(
                "count_to operation", passed, f"Expected '{expected}', got '{response}'"
            )
            self.log(f"count_to result: {response}")
        except Exception as e:
            result.add_result("count_to operation", False, str(e))
            self.log(f"count_to error: {e}", "ERROR")

        return result

    async def test_schema_group(self) -> VerificationResult:
        """Test the SchemaGroup functionality."""
        result = VerificationResult("SchemaGroup Verification")

        # Create an instance of SchemaGroup
        group = SchemaGroup()

        # Test greet_person operation
        try:
            # Pass schema parameters as keyword arguments
            response = await group.greet_person(
                name="John Doe", age=30, email="john@example.com"
            )
            expected_parts = [
                "Hello, John Doe!",
                "You are 30 years old.",
                "Your email is john@example.com",
            ]
            passed = all(part in response for part in expected_parts)
            result.add_result(
                "greet_person operation", passed, f"Response: '{response}'"
            )
            self.log(f"greet_person result: {response}")
        except Exception as e:
            result.add_result("greet_person operation", False, str(e))
            self.log(f"greet_person error: {e}", "ERROR")

        # Test repeat_message operation
        try:
            # Create a TextContent object to use as Context
            ctx = TextContent(type="text", text="")

            # Add the required methods for testing
            async def report_progress(current, total):
                pass

            def info(message):
                pass

            ctx.report_progress = report_progress
            ctx.info = info

            # Pass schema parameters as keyword arguments
            response = await group.repeat_message(text="Test", repeat=3, ctx=ctx)
            expected = "Test Test Test"
            passed = response == expected
            result.add_result(
                "repeat_message operation",
                passed,
                f"Expected '{expected}', got '{response}'",
            )
            self.log(f"repeat_message result: {response}")
        except Exception as e:
            result.add_result("repeat_message operation", False, str(e))
            self.log(f"repeat_message error: {e}", "ERROR")

        # Test process_list operation
        try:
            # Pass schema parameters as keyword arguments
            response = await group.process_list(
                items=["apple", "banana", "cherry"], prefix="Fruit:", uppercase=True
            )
            expected = ["Fruit: APPLE", "Fruit: BANANA", "Fruit: CHERRY"]
            passed = response == expected
            result.add_result(
                "process_list operation", passed, f"Expected {expected}, got {response}"
            )
            self.log(f"process_list result: {response}")
        except Exception as e:
            result.add_result("process_list operation", False, str(e))
            self.log(f"process_list error: {e}", "ERROR")

        return result

    async def test_timeout_group(self) -> VerificationResult:
        """Test the TimeoutGroup functionality."""
        result = VerificationResult("TimeoutGroup Verification")

        # Create an instance of TimeoutGroup
        group = TimeoutGroup()

        # Test sleep operation
        try:
            start_time = time.time()
            sleep_time = 0.2
            response = await group.sleep(sleep_time)
            elapsed = time.time() - start_time
            expected = f"Slept for {sleep_time} seconds"
            time_ok = sleep_time <= elapsed <= sleep_time + 0.1
            passed = expected in response and time_ok
            result.add_result(
                "sleep operation",
                passed,
                f"Expected '{expected}' in '{response}', elapsed time: {elapsed:.2f}s",
            )
            self.log(f"sleep result: {response}, elapsed: {elapsed:.2f}s")
        except Exception as e:
            result.add_result("sleep operation", False, str(e))
            self.log(f"sleep error: {e}", "ERROR")

        # Test slow_counter operation
        try:
            # Create a TextContent object to use as Context
            ctx = TextContent(type="text", text="")

            # Add the required methods for testing
            async def report_progress(current, total):
                pass

            def info(message):
                pass

            ctx.report_progress = report_progress
            ctx.info = info

            response = await group.slow_counter(3, 0.1, ctx)
            passed = "Counted to 3" in response and "1, 2, 3" in response
            result.add_result(
                "slow_counter operation", passed, f"Response: '{response}'"
            )
            self.log(f"slow_counter result: {response}")
        except Exception as e:
            result.add_result("slow_counter operation", False, str(e))
            self.log(f"slow_counter error: {e}", "ERROR")

        # Test cpu_intensive operation with a small iteration count
        try:
            # Create a TextContent object to use as Context
            ctx = TextContent(type="text", text="")

            # Add the required methods for testing
            async def report_progress(current, total):
                pass

            def info(message):
                pass

            ctx.report_progress = report_progress
            ctx.info = info

            response = await group.cpu_intensive(
                100, ctx
            )  # Small iteration count for testing
            passed = "Completed 100 iterations" in response and "result:" in response
            result.add_result(
                "cpu_intensive operation",
                passed,
                f"Response contains expected text: {passed}",
            )
            self.log(f"cpu_intensive result: {response}")
        except Exception as e:
            result.add_result("cpu_intensive operation", False, str(e))
            self.log(f"cpu_intensive error: {e}", "ERROR")

        return result

    async def test_timeout_functionality(self) -> VerificationResult:
        """Test the timeout functionality with different timeout values."""
        result = VerificationResult("Timeout Functionality Verification")

        # Create a TextContent object to use as Context
        ctx = TextContent(type="text", text="")

        # Add the required methods for testing
        async def report_progress(current, total):
            pass

        def info(message):
            pass

        ctx.report_progress = report_progress
        ctx.info = info

        # Test with operation that completes before timeout
        try:
            group = TimeoutGroup()

            # Create a task with a timeout
            task = asyncio.create_task(group.sleep(0.2))
            try:
                response = await asyncio.wait_for(task, timeout=1.0)
                passed = "Slept for 0.2 seconds" in response
                result.add_result(
                    "Operation completes before timeout",
                    passed,
                    f"Response: '{response}'",
                )
                self.log(f"Timeout test (should succeed): {response}")
            except asyncio.TimeoutError:
                result.add_result(
                    "Operation completes before timeout",
                    False,
                    "Operation timed out unexpectedly",
                )
                self.log(
                    "Timeout test (should succeed) failed: unexpected timeout", "ERROR"
                )
        except Exception as e:
            result.add_result("Operation completes before timeout", False, str(e))
            self.log(f"Timeout test (should succeed) error: {e}", "ERROR")

        # Test with operation that exceeds timeout
        try:
            group = TimeoutGroup()

            # Create a task with a timeout
            task = asyncio.create_task(group.sleep(1.0))
            try:
                response = await asyncio.wait_for(task, timeout=0.2)
                result.add_result(
                    "Operation exceeds timeout",
                    False,
                    "Operation completed when it should have timed out",
                )
                self.log(
                    f"Timeout test (should timeout) failed: operation completed",
                    "ERROR",
                )
            except asyncio.TimeoutError:
                result.add_result(
                    "Operation exceeds timeout", True, "Operation timed out as expected"
                )
                self.log("Timeout test (should timeout): timed out as expected")
        except Exception as e:
            result.add_result("Operation exceeds timeout", False, str(e))
            self.log(f"Timeout test (should timeout) error: {e}", "ERROR")

        return result

    async def test_multi_group_config(self) -> VerificationResult:
        """Test loading and using a multi-group configuration."""
        result = VerificationResult("Multi-Group Configuration Verification")

        config_path = self.config_dir / "multi_group.yaml"
        self.log(f"Testing multi-group config: {config_path}")

        try:
            # Load the YAML configuration
            import yaml

            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            # Verify the configuration structure
            has_name = "name" in config_data
            has_groups = "groups" in config_data
            has_example = (
                "verification.groups.example_group:ExampleGroup"
                in config_data.get("groups", {})
            )
            has_schema = (
                "verification.groups.schema_group:SchemaGroup"
                in config_data.get("groups", {})
            )
            has_timeout = (
                "verification.groups.timeout_group:TimeoutGroup"
                in config_data.get("groups", {})
            )

            result.add_result(
                "Multi-group config structure",
                has_name and has_groups and has_example and has_schema and has_timeout,
                f"Config has name: {has_name}, groups: {has_groups}, example: {has_example}, schema: {has_schema}, timeout: {has_timeout}",
            )
            self.log(
                f"Multi-group config structure validation: {has_name and has_groups and has_example and has_schema and has_timeout}"
            )

            # Try to create a server with this configuration
            # Note: We don't actually start the server to avoid conflicts with running processes
            try:
                from automcp.server import AutoMCPServer
                from automcp.types import ServiceConfig

                # Convert to ServiceConfig
                service_config = ServiceConfig(**config_data)

                # Create server (but don't start it)
                server = AutoMCPServer("verification-test", service_config)

                result.add_result(
                    "Create server with multi-group config",
                    True,
                    "Server created successfully",
                )
                self.log("Server created successfully with multi-group config")
            except Exception as e:
                result.add_result(
                    "Create server with multi-group config", False, str(e)
                )
                self.log(
                    f"Failed to create server with multi-group config: {e}", "ERROR"
                )

        except Exception as e:
            result.add_result("Load multi-group config", False, str(e))
            self.log(f"Failed to load multi-group config: {e}", "ERROR")

        return result

    async def test_concurrent_requests(self) -> VerificationResult:
        """Test handling of concurrent requests."""
        result = VerificationResult("Concurrent Requests Verification")

        # Create instances of the groups
        example_group = ExampleGroup()
        timeout_group = TimeoutGroup()

        # Create a TextContent object to use as Context
        ctx = TextContent(type="text", text="")

        # Add the required methods for testing
        async def report_progress(current, total):
            pass

        def info(message):
            pass

        ctx.report_progress = report_progress
        ctx.info = info

        try:
            # Create multiple tasks to run concurrently
            tasks = [
                example_group.hello_world(),
                example_group.echo("Concurrent test"),
                example_group.count_to(3),
                timeout_group.sleep(0.2),
                timeout_group.slow_counter(2, 0.1, ctx),
            ]

            # Run all tasks concurrently
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            elapsed = time.time() - start_time

            # Verify all responses
            expected_responses = [
                "Hello, World!",
                "Echo: Concurrent test",
                "1, 2, 3",
                "Slept for 0.2 seconds",
                # The slow_counter response will contain timing info, so we just check for "Counted to 2"
            ]

            all_match = True
            for i, (expected, actual) in enumerate(zip(expected_responses, responses)):
                if i < 4:  # For the first 4 responses, we expect exact matches
                    if expected not in actual:
                        all_match = False
                        self.log(
                            f"Response {i} mismatch: expected '{expected}', got '{actual}'",
                            "ERROR",
                        )
                else:  # For the slow_counter response, we just check for "Counted to 2"
                    if "Counted to 2" not in actual:
                        all_match = False
                        self.log(
                            f"Response {i} mismatch: expected 'Counted to 2' in '{actual}'",
                            "ERROR",
                        )

            # Check if the elapsed time is reasonable
            # The slowest operation is sleep(0.2), so the total time should be around 0.2-0.3 seconds
            time_ok = 0.2 <= elapsed <= 0.5

            result.add_result(
                "Concurrent operations",
                all_match and time_ok,
                f"All responses match: {all_match}, elapsed time: {elapsed:.2f}s",
            )
            self.log(
                f"Concurrent operations test: all match: {all_match}, elapsed: {elapsed:.2f}s"
            )

        except Exception as e:
            result.add_result("Concurrent operations", False, str(e))
            self.log(f"Concurrent operations test error: {e}", "ERROR")

        return result

    async def run_verification(
        self, test_type: str = "all"
    ) -> List[VerificationResult]:
        """Run all verification tests."""
        self.results = []

        # Always check the environment
        env_result = self.check_environment()
        self.results.append(env_result)

        # Run the requested tests
        if test_type in ["all", "single"]:
            self.log("Running single-group tests...")
            example_result = await self.test_example_group()
            self.results.append(example_result)

            schema_result = await self.test_schema_group()
            self.results.append(schema_result)

        if test_type in ["all", "timeout"]:
            self.log("Running timeout tests...")
            timeout_result = await self.test_timeout_group()
            self.results.append(timeout_result)

            timeout_func_result = await self.test_timeout_functionality()
            self.results.append(timeout_func_result)

        if test_type in ["all", "multi"]:
            self.log("Running multi-group tests...")
            multi_result = await self.test_multi_group_config()
            self.results.append(multi_result)

        if test_type in ["all", "concurrent"]:
            self.log("Running concurrent request tests...")
            concurrent_result = await self.test_concurrent_requests()
            self.results.append(concurrent_result)

        return self.results

    def print_results(self):
        """Print the verification results."""
        print("\n=== AutoMCP Verification Results ===")

        total_passed = sum(result.passed for result in self.results)
        total_failed = sum(result.failed for result in self.results)
        total_skipped = sum(result.skipped for result in self.results)
        total_tests = total_passed + total_failed + total_skipped

        for result in self.results:
            print(result.summary())

        print("\nOverall Summary:")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Skipped: {total_skipped}")

        if self.verbose:
            for result in self.results:
                print(result.detailed_report())

        if total_failed > 0:
            print("\n⚠️  Some tests failed. See details above.")
        else:
            print("\n✅ All tests passed!")


async def main():
    """Main entry point for the verification script."""
    parser = argparse.ArgumentParser(
        description="AutoMCP End-to-End Verification Script"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--test-type",
        "-t",
        choices=["all", "single", "multi", "timeout", "concurrent"],
        default="all",
        help="Type of tests to run",
    )
    args = parser.parse_args()

    print("=== AutoMCP Verification ===")
    print(f"Running {args.test_type} tests...")

    verifier = AutoMCPVerifier(verbose=args.verbose)
    await verifier.run_verification(args.test_type)
    verifier.print_results()


if __name__ == "__main__":
    asyncio.run(main())
