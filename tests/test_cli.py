"""Tests for the AutoMCP CLI commands."""

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from automcp.cli import app


@pytest.fixture
def runner():
    """Create a test CLI runner."""
    return CliRunner()


def test_version_command(runner):
    """Test the version command."""
    from automcp.version import __version__

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


class MockVerificationResult:
    """Mock verification result for testing."""

    def __init__(self, name, passed=1, failed=0, skipped=0):
        self.name = name
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.details = []

    def add_result(self, test_name, passed, message="", skipped=False):
        """Mock add_result method."""
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1

        status = "SKIPPED" if skipped else "PASSED" if passed else "FAILED"
        self.details.append({"test": test_name, "status": status, "message": message})

    def summary(self):
        """Mock summary method."""
        return f"{self.name}: {self.passed} passed, {self.failed} failed, {self.skipped} skipped"

    def detailed_report(self):
        """Mock detailed_report method."""
        report = [f"\n=== {self.name} ==="]
        for detail in self.details:
            report.append(f"{detail['status']}: {detail['test']}")
            if detail["message"]:
                report.append(f"  {detail['message']}")
        return "\n".join(report)


class MockVerifier:
    """Mock Verifier for testing."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = []

    async def run(self, test_type="all", timeout=1.0):
        """Mock run method."""
        env_result = MockVerificationResult("Environment Verification", passed=3)
        self.results.append(env_result)

        if test_type in ["all", "single-group"]:
            example_result = MockVerificationResult(
                "Example Group Verification", passed=3
            )
            self.results.append(example_result)

        if test_type in ["all", "schema"]:
            schema_result = MockVerificationResult(
                "Schema Validation Verification", passed=2
            )
            self.results.append(schema_result)

        if test_type in ["all", "timeout"]:
            timeout_result = MockVerificationResult(
                "Timeout Handling Verification", passed=2
            )
            self.results.append(timeout_result)

        if test_type in ["all", "multi-group"]:
            multi_result = MockVerificationResult(
                "Multi-Group Configuration Verification", passed=3
            )
            self.results.append(multi_result)

        return self.results

    def print_results(self):
        """Mock print_results method."""
        return


@patch("automcp.verification.Verifier", MockVerifier)
@patch("asyncio.run")
def test_verify_command(mock_run, runner):
    """Test the verify command."""
    mock_run.return_value = None

    # Test with default options
    result = runner.invoke(app, ["verify"])
    assert result.exit_code == 0

    # Test with specific test type
    result = runner.invoke(app, ["verify", "--test-type", "single-group"])
    assert result.exit_code == 0

    # Test with timeout
    result = runner.invoke(app, ["verify", "--timeout", "2.0"])
    assert result.exit_code == 0

    # Test with verbose flag
    result = runner.invoke(app, ["verify", "--verbose"])
    assert result.exit_code == 0


@patch("automcp.utils.run_tests")
@patch("automcp.utils.generate_test_report")
def test_test_command(mock_generate_report, mock_run_tests, runner):
    """Test the test command."""
    mock_run_tests.return_value = 0  # Simulate successful tests
    mock_generate_report.return_value = Path("test_report.md")

    # Test with default options
    result = runner.invoke(app, ["test"])
    assert result.exit_code == 0
    assert "Test report generated" in result.stdout

    # Test with verbose flag
    result = runner.invoke(app, ["test", "--verbose"])
    assert result.exit_code == 0

    # Test with coverage flag
    result = runner.invoke(app, ["test", "--coverage"])
    assert result.exit_code == 0

    # Test with HTML report flag
    result = runner.invoke(app, ["test", "--coverage", "--html-report"])
    assert result.exit_code == 0
    # Test with custom report path
    result = runner.invoke(app, ["test", "--report", "custom_report.md"])
    assert result.exit_code == 0

    # Test with failed tests
    mock_run_tests.return_value = 1  # Simulate failed tests
    result = runner.invoke(app, ["test"])
    assert result.exit_code == 1  # Should exit with non-zero code
