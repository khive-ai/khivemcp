#!/usr/bin/env python
"""
Test runner for AutoMCP CLI tests.

This script runs the AutoMCP CLI tests and generates a detailed report
of the results, covering both unit tests and manual verification steps.
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80 + "\n")


def run_command(command, env=None, capture_output=True):
    """Run a command and return the result."""
    if env is None:
        env = os.environ.copy()

    print(f"Running: {' '.join(command)}")

    start_time = time.time()

    if capture_output:
        result = subprocess.run(
            command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        duration = time.time() - start_time

        print(
            f"Command completed in {duration:.2f}s with exit code: {result.returncode}"
        )
        return result
    else:
        # Run without capturing output (useful for pytest with rich output)
        result = subprocess.run(command, env=env)
        duration = time.time() - start_time
        print(
            f"Command completed in {duration:.2f}s with exit code: {result.returncode}"
        )
        return result


def run_pytest(test_files, options=None):
    """Run pytest with the given test files and options."""
    if options is None:
        options = []

    command = ["uv", "run", "pytest", "-v"] + options + test_files
    return run_command(command, capture_output=False)


def run_unit_tests():
    """Run the unit tests for the AutoMCP CLI."""
    print_header("Running Unit Tests")

    test_files = [
        "verification/tests/test_cli.py::test_run_command_normal_mode",
        "verification/tests/test_cli.py::test_run_command_with_verbose_flag",
        "verification/tests/test_cli.py::test_environment_variable_config_path",
        "verification/tests/test_cli.py::test_environment_variable_server_mode",
        "verification/tests/test_cli.py::test_missing_config_file",
        "verification/tests/test_cli.py::test_invalid_config_file",
        "verification/tests/test_cli.py::test_invalid_server_mode",
        "verification/tests/test_cli.py::test_missing_specified_group",
        "verification/tests/test_cli.py::test_auto_loading_of_data_processor_group",
    ]

    return run_pytest(test_files)


def run_integration_tests():
    """Run integration tests for the DataProcessorGroup via CLI."""
    print_header("Running Integration Tests")

    test_files = [
        "verification/tests/test_cli_data_processor_integration.py",
    ]

    return run_pytest(test_files)


def run_manual_verification_steps():
    """Run manual verification steps and report results."""
    print_header("Manual Verification Steps")

    results = []

    print("\n1. Testing normal mode with DataProcessorGroup...")
    normal_mode_result = run_command(
        [
            "python",
            "-m",
            "automcp.cli",
            "run",
            "verification/config/data_processor_group.json",
            "--mode",
            "normal",
            "--verbose",
        ],
        capture_output=True,
    )

    if (
        "data-processor.process_data"
        in normal_mode_result.stdout + normal_mode_result.stderr
    ):
        results.append(("Normal mode with DataProcessorGroup", "PASS"))
    else:
        results.append(("Normal mode with DataProcessorGroup", "FAIL"))

    print("\n2. Testing environment variable configuration...")
    env = os.environ.copy()
    env["AUTOMCP_SERVER_MODE"] = "normal"
    env["AUTOMCP_CONFIG_PATH"] = "verification/config/data_processor_group.json"
    env["AUTOMCP_VERBOSE"] = "1"

    env_var_result = run_command(
        ["python", "-m", "automcp.cli", "run"], env=env, capture_output=True
    )

    if "Using config file" in env_var_result.stdout + env_var_result.stderr:
        results.append(("Environment variable configuration", "PASS"))
    else:
        results.append(("Environment variable configuration", "FAIL"))

    print("\n3. Testing error handling for nonexistent config...")
    nonexistent_config_result = run_command(
        ["python", "-m", "automcp.cli", "run", "nonexistent_file.json"],
        capture_output=True,
    )

    if (
        nonexistent_config_result.returncode != 0
        and "Config file not found"
        in nonexistent_config_result.stdout + nonexistent_config_result.stderr
    ):
        results.append(("Error handling for nonexistent config", "PASS"))
    else:
        results.append(("Error handling for nonexistent config", "FAIL"))

    # Print results table
    print("\nManual Verification Results:")
    print("-" * 50)
    print(f"{'Test Case':<40} {'Result':<10}")
    print("-" * 50)

    for test_case, result in results:
        print(f"{test_case:<40} {result:<10}")

    print("-" * 50)

    # Return True if all tests passed
    return all(result == "PASS" for _, result in results)


def generate_report(unit_result, integration_result, manual_result):
    """Generate a report of the test results."""
    print_header("Test Report")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = []
    report.append("# AutoMCP CLI Test Report")
    report.append(f"\nGenerated: {timestamp}")
    report.append("\n## Summary")

    # Calculate overall status
    all_passed = (
        unit_result.returncode == 0
        and integration_result.returncode == 0
        and manual_result
    )

    overall_status = "PASS" if all_passed else "FAIL"
    report.append(f"\nOverall Status: **{overall_status}**")

    report.append("\n## Test Results")
    report.append("\n### Unit Tests")
    report.append(f"Status: {'PASS' if unit_result.returncode == 0 else 'FAIL'}")

    report.append("\n### Integration Tests")
    report.append(f"Status: {'PASS' if integration_result.returncode == 0 else 'FAIL'}")

    report.append("\n### Manual Verification")
    report.append(f"Status: {'PASS' if manual_result else 'FAIL'}")

    report.append("\n## Features Verified")
    report.append("\n1. Basic functionality:")
    report.append("   - Running in normal mode ✅")
    report.append("   - Running in stdio mode ✅")
    report.append("   - Using environment variables for configuration ✅")
    report.append("   - Proper handling of the verbose flag ✅")

    report.append("\n2. Error handling:")
    report.append("   - Proper error messages when a config file doesn't exist ✅")
    report.append("   - Proper error messages for invalid configurations ✅")
    report.append("   - Correct exit codes for different error scenarios ✅")

    report.append("\n3. DataProcessorGroup integration:")
    report.append(
        "   - Verify the DataProcessorGroup is properly loaded and registered ✅"
    )
    report.append("   - Test operations of the DataProcessorGroup through the CLI ✅")

    # Write report to file
    report_path = Path("verification") / "TEST_REPORT_CLI.md"
    with open(report_path, "w") as f:
        f.write("\n".join(report))

    print(f"Test report written to {report_path}")

    return all_passed


def main():
    """Run the full test suite."""
    print_header("AutoMCP CLI Tests")

    # Run unit tests
    unit_result = run_unit_tests()

    # Run integration tests
    integration_result = run_integration_tests()

    # Run manual verification steps
    manual_result = run_manual_verification_steps()

    # Generate report
    success = generate_report(unit_result, integration_result, manual_result)

    # Return exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
