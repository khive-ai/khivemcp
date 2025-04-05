"""
Unit tests for the automcp.testing module.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from mcp.client.session import ClientSession

from automcp.testing import AutoMCPTester, VerificationResult


class TestAutoMCPTester:
    """Tests for the AutoMCPTester class."""

    def test_init(self):
        """Test initializing the AutoMCPTester class."""
        tester = AutoMCPTester(verbose=True)
        assert tester.verbose is True
        assert tester.results == []

        tester = AutoMCPTester(verbose=False)
        assert tester.verbose is False

    @pytest.mark.asyncio
    async def test_test_operation(self):
        """Test the test_operation method."""
        # Mock client
        mock_client = AsyncMock(spec=ClientSession)

        # Mock response
        mock_content = MagicMock()
        mock_content.text = "Test response"
        mock_client.call_tool.return_value.content = [mock_content]

        # Create tester
        tester = AutoMCPTester()

        # Test with no expected content
        result = await tester.test_operation(
            mock_client, "test.operation", {"param": "value"}
        )

        assert isinstance(result, VerificationResult)
        assert result.name == "test.operation operation"
        assert result.passed == 1
        assert result.failed == 0

        # Verify mock was called correctly
        mock_client.call_tool.assert_called_once_with(
            "test.operation", {"param": "value"}
        )

        # Reset mock
        mock_client.reset_mock()

        # Test with expected content (match)
        result = await tester.test_operation(
            mock_client,
            "test.operation",
            {"param": "value"},
            "Test",
            "Custom Test Name",
        )

        assert result.name == "Custom Test Name"
        assert result.passed == 1
        assert result.failed == 0

        # Test with expected content (no match)
        mock_client.reset_mock()
        mock_content.text = "Different response"
        mock_client.call_tool.return_value.content = [mock_content]

        result = await tester.test_operation(
            mock_client,
            "test.operation",
            {"param": "value"},
            "Test",
        )

        assert result.passed == 0
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_verify_operation_schema(self):
        """Test the verify_operation_schema method."""
        # Mock client
        mock_client = AsyncMock(spec=ClientSession)

        # Mock response for valid args
        mock_valid_content = MagicMock()
        mock_valid_content.text = "Valid response"
        mock_valid_response = MagicMock()
        mock_valid_response.content = [mock_valid_content]

        # For invalid args, simulate a validation error
        mock_invalid_exception = Exception(
            "Validation error: 'required_field' is a required property"
        )

        # Set up the call_tool method to return different responses based on arguments
        async def mock_call_tool(operation_name, args):
            if args == {"valid": "data"}:
                return mock_valid_response
            else:
                raise mock_invalid_exception

        mock_client.call_tool.side_effect = mock_call_tool

        # Create tester
        tester = AutoMCPTester()

        # Test schema validation
        result = await tester.verify_operation_schema(
            mock_client, "test.schema_operation", {"valid": "data"}, {"invalid": "data"}
        )

        assert isinstance(result, VerificationResult)
        assert result.name == "test.schema_operation schema validation"
        assert result.passed == 2  # Both valid and invalid tests should pass
        assert result.failed == 0

        # Ensure both calls were made
        assert mock_client.call_tool.call_count == 2
        calls = [
            call("test.schema_operation", {"valid": "data"}),
            call("test.schema_operation", {"invalid": "data"}),
        ]
        mock_client.call_tool.assert_has_calls(calls, any_order=True)

        # Test with custom name
        mock_client.reset_mock()
        result = await tester.verify_operation_schema(
            mock_client,
            "test.schema_operation",
            {"valid": "data"},
            {"invalid": "data"},
            "Custom Schema Test",
        )

        assert result.name == "Custom Schema Test"

    @pytest.mark.asyncio
    @patch("automcp.testing.start_server_process")
    async def test_verify_operation_schemas(self, mock_start_server):
        """Test the verify_operation_schemas method."""
        # Mock client and tool names
        mock_client = AsyncMock(spec=ClientSession)
        # Add shutdown method to mock
        mock_client.shutdown = AsyncMock()
        mock_start_server.return_value = (
            mock_client,
            ["test.schema_op1", "test.schema_op2"],
        )

        # Set up the call_tool method to handle different operations
        async def mock_call_tool(operation_name, args):
            mock_content = MagicMock()

            if operation_name == "test.schema_op1":
                if args == {"valid": "data"}:
                    mock_content.text = "Valid response from op1"
                    return MagicMock(content=[mock_content])
                else:
                    raise Exception("Validation error in op1")
            elif operation_name == "test.schema_op2":
                if args == {"valid": "data2"}:
                    mock_content.text = "Valid response from op2"
                    return MagicMock(content=[mock_content])
                else:
                    raise Exception("Schema error in op2")
            return MagicMock(content=[])

        mock_client.call_tool.side_effect = mock_call_tool

        # Create tester
        tester = AutoMCPTester()

        # Test schema validations
        schema_tests = [
            {
                "name": "test.schema_op1",
                "valid_args": {"valid": "data"},
                "invalid_args": {"invalid": "data"},
                "test_name": "Schema Test 1",
            },
            {
                "name": "test.schema_op2",
                "valid_args": {"valid": "data2"},
                "invalid_args": {"invalid": "data2"},
            },
        ]

        # Mock verify_operation_schema to ensure we get expected results
        async def mock_verify_schema(
            client, op_name, valid_args, invalid_args, test_name=None
        ):
            result = VerificationResult(test_name or f"{op_name} schema validation")
            result.add_result(f"{op_name} test", True, "Test passed")
            return result

        with patch.object(
            tester, "verify_operation_schema", side_effect=mock_verify_schema
        ):
            results = await tester.verify_operation_schemas(
                "test_config.json", schema_tests
            )

            assert isinstance(results, list)
            assert len(results) == 3  # Available Tools result + 2 schema test results
        assert len(results) == 3  # Available Tools result + 2 schema test results
        assert results[0].name == "Available Tools"
        assert results[1].name == "Schema Test 1"
        assert "test.schema_op2" in results[2].name

        # Verify start_server_process was called correctly
        mock_start_server.assert_called_once()

        # Verify shutdown was called
        mock_client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    @patch("automcp.testing.start_server_process")
    async def test_verify_operation_schemas_exception(self, mock_start_server):
        """Test verify_operation_schemas handles exceptions properly."""
        # Mock server start to raise an exception
        mock_start_server.side_effect = Exception("Failed to start server")

        # Mock client with shutdown method to avoid AttributeError if test tries to clean up
        mock_client = AsyncMock(spec=ClientSession)
        mock_client.shutdown = AsyncMock()
        # This won't be used due to the exception, but prevents errors if cleanup is attempted
        mock_start_server.return_value = (mock_client, [])

        # Create tester
        tester = AutoMCPTester()

        # Test with server start exception
        results = await tester.verify_operation_schemas(
            "test_config.json",
            [{"name": "test.op", "valid_args": {}, "invalid_args": {}}],
        )

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].name == "Schema Validation Test"
        assert results[0].failed == 1
        assert "Failed to start server" in results[0].details[0]["message"]
