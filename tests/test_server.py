"""AutoMCP server tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import mcp.types as types
import pytest
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.server import AutoMCPServer
from automcp.types import (
    ExecutionRequest,
    ExecutionResponse,
    GroupConfig,
    ServiceConfig,
    ServiceRequest,
)


class TestSchema(BaseModel):
    value: int


class TestGroup(ServiceGroup):
    @operation(schema=TestSchema)
    async def test_op(self, input: TestSchema, ctx: Context) -> ExecutionResponse:
        """Test operation with context."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text=f"Result: {input.value}")
        )

    @operation(schema=TestSchema)
    async def no_ctx_op(self, input: TestSchema) -> ExecutionResponse:
        """Test operation without context."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text=f"Simple: {input.value}")
        )


@pytest.fixture
def group_config():
    return GroupConfig(
        name="test-group",
        description="Test group",
        config={"test": True},
        packages=["test.package"],
    )


@pytest.fixture
def service_config():
    return ServiceConfig(
        name="test-service",
        packages=["test.package"],
        groups={
            "test_server:TestGroup": GroupConfig(
                name="test-group", description="Test group", config={"test": True}
            )
        },
    )


@pytest.mark.asyncio
async def test_group_server_initialization(group_config):
    """Test server initialization with single group."""
    with patch("mcp.server.fastmcp.FastMCP") as mock_fastmcp:
        server = AutoMCPServer("test", group_config)

        # Verify FastMCP initialization
        mock_fastmcp.assert_called_once_with(
            name="test",
            instructions="Test group",
            dependencies=["test.package"],
            lifespan=None,
        )

        # Verify group initialization
        assert "test-group" in server.groups
        assert isinstance(server.groups["test-group"], ServiceGroup)


@pytest.mark.asyncio
async def test_service_server_initialization(service_config):
    """Test server initialization with service config."""
    with patch("mcp.server.fastmcp.FastMCP") as mock_fastmcp:
        server = AutoMCPServer("test", service_config)

        # Verify FastMCP initialization
        mock_fastmcp.assert_called_once()

        # Verify groups initialization
        assert "test-group" in server.groups
        assert isinstance(server.groups["test-group"], TestGroup)


@pytest.mark.asyncio
async def test_tool_registration(group_config):
    """Test tool registration with FastMCP."""
    with patch("mcp.server.fastmcp.FastMCP") as mock_fastmcp:
        mock_instance = MagicMock()
        mock_fastmcp.return_value = mock_instance

        server = AutoMCPServer("test", group_config)

        # Verify tools were registered
        assert mock_instance.add_tool.call_count >= 2

        # Verify tool registration parameters
        calls = mock_instance.add_tool.call_args_list
        tool_names = [call.kwargs["name"] for call in calls]
        assert "test-group.test_op" in tool_names
        assert "test-group.no_ctx_op" in tool_names


@pytest.mark.asyncio
async def test_request_handling(group_config):
    """Test service request handling."""
    server = AutoMCPServer("test", group_config)

    request = ServiceRequest(
        requests=[ExecutionRequest(operation="test_op", arguments={"value": 42})]
    )

    response = await server._handle_service_request("test-group", request)
    assert response.content.text == "Result: 42"
    assert not response.errors


@pytest.mark.asyncio
async def test_concurrent_requests(group_config):
    """Test concurrent request handling."""
    server = AutoMCPServer("test", group_config)

    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="test_op", arguments={"value": i})
            for i in range(5)
        ]
    )

    response = await server._handle_service_request("test-group", request)
    assert "Result: 0" in response.content.text
    assert "Result: 4" in response.content.text
    assert not response.errors


@pytest.mark.asyncio
async def test_timeout_handling(group_config):
    """Test operation timeout."""
    server = AutoMCPServer("test", group_config, timeout=0.1)

    class SlowGroup(ServiceGroup):
        @operation(schema=TestSchema)
        async def slow_op(self, input: TestSchema) -> ExecutionResponse:
            await asyncio.sleep(1)
            return ExecutionResponse(
                content=types.TextContent(type="text", text="Done")
            )

    server.groups["test-group"] = SlowGroup()

    request = ServiceRequest(
        requests=[ExecutionRequest(operation="slow_op", arguments={"value": 1})]
    )

    response = await server._handle_service_request("test-group", request)
    assert "timeout" in response.content.text.lower()
    assert response.errors


@pytest.mark.asyncio
async def test_server_start():
    """Test server start method."""
    with patch("mcp.server.fastmcp.FastMCP") as mock_fastmcp:
        mock_instance = MagicMock()
        mock_fastmcp.return_value = mock_instance

        server = AutoMCPServer("test", GroupConfig(name="test"))
        await server.start()

        # Verify FastMCP run was called with stdio transport
        mock_instance.run.assert_called_once_with("stdio")
