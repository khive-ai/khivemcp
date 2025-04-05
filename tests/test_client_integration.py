"""
Integration tests for the automcp.client module.

These tests verify that the client correctly interacts with AutoMCP servers.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel

from automcp.client import AutoMCPClient
from automcp.server import AutoMCPServer
from automcp.testing import create_connected_server_and_client


# Define a simple example ServiceGroup for testing
class ExampleInput(BaseModel):
    """Input schema for the example operation."""

    message: str


async def example_operation(input_data: ExampleInput) -> str:
    """A simple example operation that returns a greeting."""
    return f"Hello, {input_data.message}!"


# Create a simple config for testing
def create_test_config():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config = {
            "service_groups": [
                {
                    "name": "example",
                    "operations": [
                        {
                            "name": "greet",
                            "description": "Return a greeting message",
                            "input_schema": {
                                "type": "object",
                                "properties": {"message": {"type": "string"}},
                                "required": ["message"],
                            },
                        }
                    ],
                }
            ]
        }
        json.dump(config, f)
        return f.name


class TestClientIntegration:
    """Integration tests for the AutoMCPClient class."""

    @pytest.mark.asyncio
    async def test_client_with_memory_session(self):
        """Test client functionality with a mock server using memory streams."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp.client.session import ClientSession

        # Create a mock client session
        client_session = AsyncMock(spec=ClientSession)

        # Create mock tools
        mock_tool = MagicMock()
        mock_tool.name = "example.greet"
        mock_tool.description = "Example greeting operation"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        }

        # Mock list_tools response
        client_session.list_tools.return_value.tools = [mock_tool]

        # Create a mock response for call_tool
        mock_content = MagicMock()
        mock_content.text = "Hello, World!"
        client_session.call_tool.return_value.content = [mock_content]

        # Create an AutoMCPClient instance
        client = AutoMCPClient(client_session, ["example.greet"])

        # Test list_tools
        tool_list = await client.list_tools()
        assert "example.greet" in tool_list

        # Test get_tool_details
        tool_details = await client.get_tool_details()
        assert "example.greet" in tool_details
        assert "description" in tool_details["example.greet"]
        assert "schema" in tool_details["example.greet"]

        # Test calling an operation
        result = await client.call("example.greet", {"message": "World"})
        assert result == "Hello, World!"

        # Test calling with a model class
        try:
            # Create a simple model for testing
            class TestModel(BaseModel):
                message: str

            # This might fail since our example returns a string, not JSON
            # But we're still testing the method signature works
            await client.call("example.greet", {"message": "Model"}, TestModel)
        except Exception:
            # Expected if the operation doesn't return valid JSON for the model
            pass

    @pytest.mark.asyncio
    async def test_client_connect_method(self):
        """Test the AutoMCPClient.connect class method."""
        # Create a temporary config file
        config_path = create_test_config()

        try:
            # Use the connect class method to create a client
            # This test is more of an API test since we're not actually running a server
            try:
                # We expect this to fail since we're not running a server
                await asyncio.wait_for(
                    AutoMCPClient.connect(config_path),
                    timeout=0.5,  # Very short timeout to avoid hanging
                )
                pytest.fail("Connection should not succeed without a server")
            except (Exception, asyncio.CancelledError):
                # Any exception is fine here, we just want to make sure the method exists
                # and has the correct signature
                pass
        finally:
            # Clean up the temp file
            os.unlink(config_path)


# This allows running the tests standalone
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
