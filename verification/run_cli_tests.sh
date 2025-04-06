#!/bin/bash
# Run tests for the enhanced AutoMCP CLI implementation

set -e  # Exit on error

echo "=== AutoMCP CLI Test Suite ==="
echo

# Check for uv package manager
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' package manager not found."
    echo "Please install it first: pip install uv"
    exit 1
fi

# Ensure pytest is installed
if ! uv pip list | grep -q pytest; then
    echo "Installing test dependencies..."
    uv pip install pytest pytest-asyncio
fi

# Change to the project root directory
cd "$(dirname "$0")/.."
echo "Running tests from directory: $(pwd)"
echo

# Execute the test runner
python verification/run_cli_tests.py

# Check for the test report
if [ -f verification/TEST_REPORT_CLI.md ]; then
    echo
    echo "Test report generated at: verification/TEST_REPORT_CLI.md"
    
    # Extract and display overall status
    OVERALL_STATUS=$(grep -A 1 "Overall Status" verification/TEST_REPORT_CLI.md | tail -1)
    echo
    echo "Overall Test Result: $OVERALL_STATUS"
fi