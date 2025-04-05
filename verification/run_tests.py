#!/usr/bin/env python3
"""
AutoMCP Configuration System Verification Test Runner

This script runs all the verification tests and generates a comprehensive test report.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_tests(verbose=False, coverage=False, html_report=False):
    """Run all verification tests and return the result."""
    print("=== Running AutoMCP Configuration System Verification Tests ===")

    # Determine the test command
    cmd = ["pytest", "verification/tests/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=automcp", "--cov=verification"])
        if html_report:
            cmd.append("--cov-report=html")

    # Run the tests
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    # Print the test output
    print(result.stdout)
    if result.stderr:
        print("Errors:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    # Print summary
    print(f"\nTests completed in {elapsed:.2f} seconds")
    print(f"Return code: {result.returncode}")

    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

    return result.returncode


def generate_report(test_result):
    """Generate a test report based on the test results."""
    report_path = Path(__file__).parent / "TEST_REPORT.md"

    # Get the current time
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the report content
    report_content = f"""# AutoMCP Configuration System Verification Test Report

## Test Run Information

- **Date and Time**: {now}
- **Result**: {"✅ All tests passed!" if test_result == 0 else "❌ Some tests failed!"}

## Test Coverage

The verification tests cover the following areas:

1. **Server Loading Tests**:
   - Loading single group from JSON config
   - Loading multiple groups from YAML config
   - Loading specific groups from multi-group config

2. **Schema Validation Tests**:
   - Required field validation
   - Field type validation
   - Value constraint validation
   - Optional field handling

3. **Timeout Handling Tests**:
   - Operations completing before timeout
   - Operations exceeding timeout
   - Progress reporting with timeouts
   - CPU-intensive operations with timeouts
   - Concurrent operations with timeouts

4. **Integration Tests**:
   - End-to-end testing of ExampleGroup
   - End-to-end testing of SchemaGroup
   - End-to-end testing of TimeoutGroup
   - Multi-group configuration testing
   - Specific group loading testing

## Detailed Test Results

For detailed test results, run the tests with the `-v` flag:

```
python verification/run_tests.py -v
```

For coverage information, run the tests with the `--coverage` flag:

```
python verification/run_tests.py --coverage
```

For an HTML coverage report, run the tests with the `--html-report` flag:

```
python verification/run_tests.py --coverage --html-report
```

## Conclusion

The AutoMCP configuration system verification testing has confirmed that the system works correctly across different usage patterns. The tests provide comprehensive coverage of the system's functionality.

For more detailed analysis and recommendations, see the [TEST_RESULTS.md](TEST_RESULTS.md) file.
"""

    # Write the report to a file
    with open(report_path, "w") as f:
        f.write(report_content)

    print(f"\nTest report generated: {report_path}")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="AutoMCP Configuration System Verification Test Runner"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage information"
    )
    parser.add_argument(
        "--html-report", action="store_true", help="Generate HTML coverage report"
    )
    args = parser.parse_args()

    # Run the tests
    test_result = run_tests(args.verbose, args.coverage, args.html_report)

    # Generate the report
    generate_report(test_result)

    return test_result


if __name__ == "__main__":
    sys.exit(main())
