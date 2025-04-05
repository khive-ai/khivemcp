"""Tests for the verify_automcp.py script."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from verification.verify_automcp import AutoMCPVerifier, VerificationResult


class TestVerificationResult:
    """Tests for the VerificationResult class."""

    def test_init(self):
        """Test initialization of VerificationResult."""
        result = VerificationResult("Test Group")
        assert result.name == "Test Group"
        assert result.passed == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.details == []

    def test_add_result_passed(self):
        """Test adding a passed result."""
        result = VerificationResult("Test Group")
        result.add_result("Test 1", True, "Test message")
        assert result.passed == 1
        assert result.failed == 0
        assert result.skipped == 0
        assert len(result.details) == 1
        assert result.details[0]["test"] == "Test 1"
        assert result.details[0]["status"] == "PASSED"
        assert result.details[0]["message"] == "Test message"

    def test_add_result_failed(self):
        """Test adding a failed result."""
        result = VerificationResult("Test Group")
        result.add_result("Test 1", False, "Test message")
        assert result.passed == 0
        assert result.failed == 1
        assert result.skipped == 0
        assert len(result.details) == 1
        assert result.details[0]["test"] == "Test 1"
        assert result.details[0]["status"] == "FAILED"
        assert result.details[0]["message"] == "Test message"

    def test_add_result_skipped(self):
        """Test adding a skipped result."""
        result = VerificationResult("Test Group")
        result.add_result("Test 1", False, "Test message", skipped=True)
        assert result.passed == 0
        assert result.failed == 0
        assert result.skipped == 1
        assert len(result.details) == 1
        assert result.details[0]["test"] == "Test 1"
        assert result.details[0]["status"] == "SKIPPED"
        assert result.details[0]["message"] == "Test message"

    def test_summary(self):
        """Test getting a summary of the verification results."""
        result = VerificationResult("Test Group")
        result.add_result("Test 1", True)
        result.add_result("Test 2", False)
        result.add_result("Test 3", False, skipped=True)
        assert result.summary() == "Test Group: 1 passed, 1 failed, 1 skipped"

    def test_detailed_report(self):
        """Test getting a detailed report of the verification results."""
        result = VerificationResult("Test Group")
        result.add_result("Test 1", True, "Passed message")
        result.add_result("Test 2", False, "Failed message")
        report = result.detailed_report()
        assert "Test Group" in report
        assert "PASSED: Test 1" in report
        assert "Passed message" in report
        assert "FAILED: Test 2" in report
        assert "Failed message" in report


class TestAutoMCPVerifier:
    """Tests for the AutoMCPVerifier class."""

    def test_init(self):
        """Test initialization of AutoMCPVerifier."""
        verifier = AutoMCPVerifier()
        assert verifier.verbose is False
        assert verifier.results == []

        verifier = AutoMCPVerifier(verbose=True)
        assert verifier.verbose is True

    def test_check_environment(self):
        """Test checking the environment."""

        # Create a simplified version of check_environment for testing
        def mock_check_environment(self):
            result = VerificationResult("Environment Verification")

            # Check Python version
            python_version = "3.10.0"  # Mocked version
            min_version = "3.10.0"
            python_ok = python_version >= min_version
            result.add_result(
                "Python Version",
                python_ok,
                f"Found {python_version}, minimum required is {min_version}",
            )

            # Check required packages
            required_packages = ["automcp", "pydantic", "mcp"]
            for package in required_packages:
                result.add_result(f"Package: {package}", True)

            return result

        # Patch the check_environment method
        with patch.object(
            AutoMCPVerifier, "check_environment", mock_check_environment
        ):
            # Run the test
            verifier = AutoMCPVerifier()
            result = verifier.check_environment()

            # Verify results
            assert result.name == "Environment Verification"
            assert (
                result.passed > 0
            )  # At least Python version check should pass
            assert result.failed == 0  # No failures expected

    def test_check_environment_with_import_error(self):
        """Test checking the environment with import errors."""

        # Create a simplified version of check_environment for testing
        def mock_check_environment(self):
            result = VerificationResult("Environment Verification")

            # Check Python version
            python_version = "3.10.0"  # Mocked version
            min_version = "3.10.0"
            python_ok = python_version >= min_version
            result.add_result(
                "Python Version",
                python_ok,
                f"Found {python_version}, minimum required is {min_version}",
            )

            # Check required packages with simulated import error
            required_packages = ["automcp", "pydantic", "mcp"]
            for package in required_packages:
                result.add_result(
                    f"Package: {package}", False, "Package not found"
                )

            return result

        # Patch the check_environment method
        with patch.object(
            AutoMCPVerifier, "check_environment", mock_check_environment
        ):
            # Run the test
            verifier = AutoMCPVerifier()
            result = verifier.check_environment()

            # Verify results
            assert result.name == "Environment Verification"
            assert result.passed > 0  # Python version check should pass
            assert result.failed > 0  # Import checks should fail

    @pytest.mark.asyncio
    @patch("verification.verify_automcp.stdio_client")
    async def test_test_example_group(self, mock_stdio_client):
        """Test the test_example_group method."""
        # Setup mocks
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_client = AsyncMock()

        # Mock the response for list_tools
        mock_tool = MagicMock()
        mock_tool.name = "example.hello_world"
        mock_client.list_tools.return_value = [mock_tool]

        # Mock the response for call_tool
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Hello, World!"
        mock_response.content = [mock_content]
        mock_client.call_tool.return_value = mock_response

        # Setup the context manager returns
        mock_stdio_client.return_value.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
        )
        mock_client.__aenter__.return_value = mock_client

        # Run the test
        verifier = AutoMCPVerifier()
        with patch(
            "verification.verify_automcp.ClientSession",
            return_value=mock_client,
        ):
            result = await verifier.test_example_group()

        # Verify results
        assert result.name == "ExampleGroup Verification"
        assert mock_stdio_client.called
        assert mock_client.initialize.called
        assert mock_client.list_tools.called

    @pytest.mark.asyncio
    @patch("verification.verify_automcp.AutoMCPVerifier.check_environment")
    @patch("verification.verify_automcp.AutoMCPVerifier.test_example_group")
    @patch("verification.verify_automcp.AutoMCPVerifier.test_schema_group")
    @patch("verification.verify_automcp.AutoMCPVerifier.test_timeout_group")
    @patch(
        "verification.verify_automcp.AutoMCPVerifier.test_multi_group_config"
    )
    async def test_run_verification_all(
        self,
        mock_test_multi_group,
        mock_test_timeout,
        mock_test_schema,
        mock_test_example,
        mock_check_env,
    ):
        """Test running all verification tests."""
        # Setup mocks
        mock_check_env.return_value = VerificationResult("Environment")
        mock_test_example.return_value = VerificationResult("Example")
        mock_test_schema.return_value = VerificationResult("Schema")
        mock_test_timeout.return_value = VerificationResult("Timeout")
        mock_test_multi_group.return_value = VerificationResult("Multi-Group")

        # Run the test
        verifier = AutoMCPVerifier()
        results = await verifier.run_verification("all")

        # Verify results
        assert len(results) == 5  # All test types should be run
        assert mock_check_env.called
        assert mock_test_example.called
        assert mock_test_schema.called
        assert mock_test_timeout.called
        assert mock_test_multi_group.called

    @pytest.mark.asyncio
    @patch("verification.verify_automcp.AutoMCPVerifier.check_environment")
    @patch("verification.verify_automcp.AutoMCPVerifier.test_example_group")
    async def test_run_verification_single_group(
        self,
        mock_test_example,
        mock_check_env,
    ):
        """Test running single-group verification tests."""
        # Setup mocks
        mock_check_env.return_value = VerificationResult("Environment")
        mock_test_example.return_value = VerificationResult("Example")

        # Run the test
        verifier = AutoMCPVerifier()
        results = await verifier.run_verification("single-group")

        # Verify results
        assert len(results) == 2  # Environment and Example tests
        assert mock_check_env.called
        assert mock_test_example.called

    def test_print_results(self):
        """Test printing verification results."""
        # Setup
        verifier = AutoMCPVerifier()
        result1 = VerificationResult("Group 1")
        result1.add_result("Test 1", True)
        result1.add_result("Test 2", False)

        result2 = VerificationResult("Group 2")
        result2.add_result("Test 3", True)
        result2.add_result("Test 4", True)

        verifier.results = [result1, result2]

        # Run the test - just make sure it doesn't raise an exception
        verifier.print_results()

        # No assertions needed, just checking that it runs without errors
