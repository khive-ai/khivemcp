# Enhanced AutoMCP CLI Test Documentation

This document outlines the test strategy and procedures for verifying the enhanced AutoMCP CLI implementation.

## Test Strategy

The test suite uses multiple approaches to ensure comprehensive coverage:

1. **Unit Tests**: Focused tests for specific CLI functionality using pytest and Typer's testing utilities
2. **Integration Tests**: End-to-end tests validating the CLI's interaction with the DataProcessorGroup
3. **Manual Verification**: Real-world usage scenarios to validate expected behavior

## Test Coverage

The tests verify the following features:

### 1. Basic Functionality
- Running in normal mode
- Running in stdio mode
- Using environment variables for configuration
- Proper handling of the verbose flag

### 2. Error Handling
- Proper error messages when a config file doesn't exist
- Proper error messages for invalid configurations
- Correct exit codes for different error scenarios

### 3. DataProcessorGroup Integration
- Verify the DataProcessorGroup is properly loaded and registered
- Test operations of the DataProcessorGroup through the CLI

## Test Files

- `verification/tests/test_cli.py`: Unit tests for CLI functionality
- `verification/tests/test_cli_data_processor_integration.py`: Integration tests focusing on DataProcessorGroup
- `verification/run_cli_tests.py`: Main test runner script
- `verification/run_cli_tests.sh`: Shell script for easy test execution

## Running Tests

### Prerequisites

- Python 3.10+
- The `uv` package manager
- pytest and pytest-asyncio

### Method 1: Using the Shell Script

```bash
# Make the script executable if not already
chmod +x verification/run_cli_tests.sh

# Run the test suite
./verification/run_cli_tests.sh
```

### Method 2: Using pytest Directly

```bash
# Run all CLI tests
uv run pytest verification/tests/test_cli.py verification/tests/test_cli_data_processor_integration.py -v

# Run specific test file
uv run pytest verification/tests/test_cli.py -v
```

### Method 3: Using the Python Test Runner

```bash
# Run the test runner script
python verification/run_cli_tests.py
```

## Test Report

After running the tests, a report is generated at `verification/TEST_REPORT_CLI.md` which includes:

- Overall test status
- Individual test results
- List of verified features

## Manual Verification Steps

In addition to automated tests, the test runner performs the following manual verification steps:

1. Testing normal mode with DataProcessorGroup
2. Testing environment variable configuration
3. Testing error handling for nonexistent config files

## Extending the Tests

To add new tests:

1. Add test functions to the existing test files or create new test files
2. Update the test runner script to include the new tests
3. Ensure any new dependencies are documented

## Troubleshooting

If tests fail, check the following:

- Ensure the CLI implementation matches the design document
- Verify that the DataProcessorGroup is properly registered
- Check that all environment variables are being correctly processed
- Make sure error handling is working as expected

## Notes for Test Development

When developing new tests:

- Use mocks for time-consuming operations
- For stdio mode tests, carefully manage input/output streams
- Add appropriate markers for tests that require special handling
- Ensure proper cleanup of resources in test teardown