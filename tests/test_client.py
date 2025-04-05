"""
Unit tests for the automcp.client module.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from mcp.client.session import ClientSession
from pydantic import BaseModel

from automcp.client import (
    AutoMCPClient,
    ProgressUpdate,
    connect_to_automcp_server,
    list_operations,
    parse_json_response,
    parse_model_response,
    parse_text_response,
)


class TestAutoMCPClient:
    """Tests for the AutoMCPClient class."""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test the list_tools method."""
        # Create mock session
        mock_session = AsyncMock(spec=ClientSession)

        # Create mock tool list
        mock_tool = MagicMock()
        mock_tool.name = "group.operation"
        mock_tool2 = MagicMock()
        mock_tool2.name = "group.operation2"

        # Mock the session list_tools response
        mock_session.list_tools.return_value.tools = [mock_tool, mock_tool2]

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation", "group.operation2"])

        # Call list_tools
        tools = await client.list_tools()

        # Verify the result
        assert tools == ["group.operation", "group.operation2"]
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tool_details(self):
        """Test the get_tool_details method."""
        # Create mock session
        mock_session = AsyncMock(spec=ClientSession)

        # Create mock tools with details
        mock_tool = MagicMock()
        mock_tool.name = "group.operation"
        mock_tool.description = "Test operation"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
        }

        mock_tool2 = MagicMock()
        mock_tool2.name = "group.operation2"
        mock_tool2.description = "Another test operation"
        mock_tool2.inputSchema = {
            "type": "object",
            "properties": {"param": {"type": "integer"}},
        }

        # Mock the session list_tools response
        mock_session.list_tools.return_value.tools = [mock_tool, mock_tool2]

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation", "group.operation2"])

        # Call get_tool_details
        details = await client.get_tool_details()

        # Verify the result
        assert "group.operation" in details
        assert "group.operation2" in details
        assert details["group.operation"]["description"] == "Test operation"
        assert details["group.operation"]["schema"] == {
            "type": "object",
            "properties": {"test": {"type": "string"}},
        }
        assert details["group.operation2"]["description"] == "Another test operation"
        assert details["group.operation2"]["schema"] == {
            "type": "object",
            "properties": {"param": {"type": "integer"}},
        }
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_method(self):
        """Test the call method."""
        # Create mock session
        mock_session = AsyncMock(spec=ClientSession)

        # Create mock response
        mock_content = MagicMock()
        mock_content.text = "Test response"
        mock_session.call_tool.return_value.content = [mock_content]

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation"])

        # Call operation
        result = await client.call("group.operation", {"param": "value"})

        # Verify the result
        assert result == "Test response"
        mock_session.call_tool.assert_called_once_with(
            "group.operation", {"param": "value"}
        )

    @pytest.mark.asyncio
    async def test_call_with_model(self):
        """Test the call method with model parsing."""
        # Create mock session
        mock_session = AsyncMock(spec=ClientSession)

        # Create mock response with JSON
        mock_content = MagicMock()
        mock_content.text = '{"name": "Test", "value": 42}'
        mock_session.call_tool.return_value.content = [mock_content]

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation"])

        # Create model class
        class TestModel(BaseModel):
            name: str
            value: int

        # Call operation with model class
        result = await client.call("group.operation", {"param": "value"}, TestModel)

        # Verify the result
        assert isinstance(result, TestModel)
        assert result.name == "Test"
        assert result.value == 42
        mock_session.call_tool.assert_called_once_with(
            "group.operation", {"param": "value"}
        )

    @pytest.mark.asyncio
    async def test_call_invalid_operation(self):
        """Test calling an invalid operation."""
        # Create mock session
        mock_session = AsyncMock(spec=ClientSession)

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation"])

        # Call an operation that doesn't exist
        with pytest.raises(ValueError) as excinfo:
            await client.call("group.invalid_operation", {"param": "value"})

        # Verify the error message
        assert "Operation group.invalid_operation not available" in str(excinfo.value)
        # Verify the session wasn't called
        mock_session.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_class_method(self):
        """Test the connect class method."""
        # Mock the connect_to_automcp_server function
        with patch("automcp.client.connect_to_automcp_server") as mock_connect:
            # Set up the mock return value
            mock_session = AsyncMock(spec=ClientSession)
            mock_connect.return_value = (mock_session, ["group.operation"])

            # Call the connect method
            client = await AutoMCPClient.connect("config.json", timeout=60.0)

            # Verify the client was created correctly
            assert isinstance(client, AutoMCPClient)
            assert client.session == mock_session
            assert client.available_tools == ["group.operation"]

            # Verify connect_to_automcp_server was called correctly
            mock_connect.assert_called_once_with("config.json", 60.0)

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test the close method."""
        # Create mock session
        mock_session = AsyncMock()  # Don't use spec to avoid attribute errors

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation"])

        # Call close
        await client.close()

        # Verify shutdown was called
        mock_session.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method_with_exception(self):
        """Test the close method when shutdown raises an exception."""
        # Create mock session that raises an exception on shutdown
        mock_session = AsyncMock()  # Don't use spec to avoid attribute errors
        mock_session.shutdown.side_effect = Exception("Shutdown error")

        # Create client with mock session
        client = AutoMCPClient(mock_session, ["group.operation"])

        # Call close - should not raise an exception
        await client.close()

        # Verify shutdown was called
        mock_session.shutdown.assert_called_once()


class TestProgressUpdate:
    """Tests for the ProgressUpdate class."""

    def test_progress_update(self):
        """Test creating and using a ProgressUpdate."""
        # Create a progress update
        progress = ProgressUpdate(current=50, total=100)

        # Check the values
        assert progress.current == 50
        assert progress.total == 100


class TestClientFunctions:
    """Tests for the client module utility functions."""

    def test_parse_text_response(self):
        """Test parse_text_response function."""
        # Create a mock response with text content
        mock_content = MagicMock()
        mock_content.text = "Hello, World!"
        mock_response = MagicMock()
        mock_response.content = [mock_content]

        # Parse the response
        result = parse_text_response(mock_response)

        # Verify the result
        assert result == "Hello, World!"

    def test_parse_text_response_empty(self):
        """Test parse_text_response with empty content."""
        # Create a mock response with no content
        mock_response = MagicMock()
        mock_response.content = []

        # Parse the response
        result = parse_text_response(mock_response)

        # Verify the result
        assert result == ""

    def test_parse_json_response(self):
        """Test parse_json_response function."""
        # Create a mock response with JSON content
        mock_content = MagicMock()
        mock_content.text = '{"name": "Test", "value": 42}'
        mock_response = MagicMock()
        mock_response.content = [mock_content]

        # Parse the response
        result = parse_json_response(mock_response)

        # Verify the result
        assert result == {"name": "Test", "value": 42}

    def test_parse_model_response(self):
        """Test parse_model_response function."""
        # Create a mock response with JSON content
        mock_content = MagicMock()
        mock_content.text = '{"name": "Test", "value": 42}'
        mock_response = MagicMock()
        mock_response.content = [mock_content]

        # Create a model class
        class TestModel(BaseModel):
            name: str
            value: int

        # Parse the response
        result = parse_model_response(mock_response, TestModel)

        # Verify the result
        assert isinstance(result, TestModel)
        assert result.name == "Test"
        assert result.value == 42

    def test_parse_model_response_invalid_model(self):
        """Test parse_model_response with an invalid model class."""
        # Create a mock response
        mock_response = MagicMock()

        # Try to parse with a non-BaseModel class
        with pytest.raises(TypeError) as excinfo:
            parse_model_response(mock_response, dict)

        # Verify the error message
        assert "model_class must be a Pydantic BaseModel subclass" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_list_operations(self):
        """Test list_operations function."""
        # Create mock client
        mock_client = AsyncMock(spec=ClientSession)

        # Create mock tools
        mock_tool = MagicMock()
        mock_tool.name = "group.operation"
        mock_tool.description = "Test operation"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
        }

        mock_tool2 = MagicMock()
        mock_tool2.name = "group.operation2"
        mock_tool2.description = "Another test operation"
        mock_tool2.inputSchema = {
            "type": "object",
            "properties": {"param": {"type": "integer"}},
        }

        # Mock the client list_tools response
        mock_client.list_tools.return_value.tools = [mock_tool, mock_tool2]

        # Call list_operations
        operations = await list_operations(mock_client)

        # Verify the result
        assert "group.operation" in operations
        assert "group.operation2" in operations
        assert operations["group.operation"]["description"] == "Test operation"
        assert operations["group.operation"]["schema"] == {
            "type": "object",
            "properties": {"test": {"type": "string"}},
        }
        assert operations["group.operation2"]["description"] == "Another test operation"
        assert operations["group.operation2"]["schema"] == {
            "type": "object",
            "properties": {"param": {"type": "integer"}},
        }
        mock_client.list_tools.assert_called_once()


@pytest.mark.asyncio
@patch("automcp.client.create_client_connection")
async def test_connect_to_automcp_server(mock_create_client):
    """Test connect_to_automcp_server function."""
    # Mock the create_client_connection function
    mock_session = AsyncMock(spec=ClientSession)
    mock_create_client.return_value = (mock_session, ["group.operation"])

    # Call connect_to_automcp_server
    session, tools = await connect_to_automcp_server("config.json", timeout=60.0)

    # Verify the result
    assert session == mock_session
    assert tools == ["group.operation"]

    # Verify create_client_connection was called correctly with the right arguments
    import sys

    mock_create_client.assert_called_once_with(
        command=sys.executable,
        args=["-m", "automcp.cli", "run", "config.json", "--timeout", "60.0"],
    )
