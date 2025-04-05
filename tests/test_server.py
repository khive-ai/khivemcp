"""
AutoMCP server tests.

This module contains tests for the AutoMCPServer class, verifying its
initialization, request handling, timeout behavior, and error reporting.
"""

import asyncio
import logging
from unittest.mock import MagicMock, patch

import mcp.types as types
import pytest
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from automcp.exceptions import OperationTimeoutError
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
    async def test_op(
        self, input: TestSchema, ctx: Context
    ) -> ExecutionResponse:
        """Test operation with context."""
        return ExecutionResponse(
            content=types.TextContent(
                type="text", text=f"Result: {input.value}"
            )
        )

    @operation(schema=TestSchema)
    async def no_ctx_op(self, input: TestSchema) -> ExecutionResponse:
        """Test operation without context."""
        return ExecutionResponse(
            content=types.TextContent(
                type="text", text=f"Simple: {input.value}"
            )
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
                name="test-group",
                description="Test group",
                config={"test": True},
            )
        },
    )


@pytest.mark.asyncio
async def test_group_server_initialization(group_config):
    """Test server initialization with single group."""
    with patch("automcp.server.FastMCP") as mock_fastmcp:
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
    with patch("automcp.server.FastMCP") as mock_fastmcp:
        mock_instance = MagicMock()
        mock_fastmcp.return_value = mock_instance

        server = AutoMCPServer("test", service_config)

        # Verify FastMCP initialization
        mock_fastmcp.assert_called_once()

        # Verify groups initialization
        assert "test-group" in server.groups
        assert isinstance(server.groups["test-group"], TestGroup)


@pytest.mark.asyncio
async def test_tool_registration(group_config):
    """Test tool registration with FastMCP."""
    with patch("automcp.server.FastMCP") as mock_fastmcp:
        mock_instance = MagicMock()
        mock_fastmcp.return_value = mock_instance

        # Create a test group with operations and add it to the server
        test_group = TestGroup()

        server = AutoMCPServer("test", group_config)
        server.groups["test-group"] = test_group

        # Re-run setup handlers to register the operations
        server._setup_handlers()

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

    # Add a test group with operations
    test_group = TestGroup()
    server.groups["test-group"] = test_group

    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="test_op", arguments={"value": 42})
        ]
    )

    response = await server._handle_service_request("test-group", request)
    assert "Result: 42" in response.content.text
    assert not response.errors


@pytest.mark.asyncio
async def test_concurrent_requests(group_config):
    """Test concurrent request handling."""
    server = AutoMCPServer("test", group_config)

    # Add a test group with operations
    test_group = TestGroup()
    server.groups["test-group"] = test_group

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
        requests=[
            ExecutionRequest(operation="slow_op", arguments={"value": 1})
        ]
    )
    response = await server._handle_service_request("test-group", request)
    assert "timeout" in response.content.text.lower()
    assert response.errors
    assert "slow_op" in response.content.text


@pytest.mark.asyncio
async def test_server_start():
    """Test server start method."""
    with patch("automcp.server.FastMCP") as mock_fastmcp:
        mock_instance = MagicMock()
        mock_fastmcp.return_value = mock_instance

        server = AutoMCPServer("test", GroupConfig(name="test"))

        # Create a spy to track calls to run
        run_called_with = []

        async def mock_run(transport):
            run_called_with.append(transport)
            return None

        mock_instance.run = mock_run
        await server.start()

        # Verify FastMCP run was called with stdio transport
        assert len(run_called_with) == 1
        assert run_called_with[0] == "stdio"


@pytest.mark.asyncio
async def test_raw_config_storage():
    """Test that the raw config is stored as an attribute."""
    config = GroupConfig(name="test-group")
    server = AutoMCPServer("test", config)

    # Verify raw_config is stored
    assert server.raw_config is config
    assert isinstance(server.raw_config, GroupConfig)


@pytest.mark.asyncio
async def test_invalid_config_type():
    """Test that an invalid config type raises TypeError."""
    with pytest.raises(TypeError) as excinfo:
        # Pass a string instead of a proper config object
        AutoMCPServer("test", "invalid-config")

    assert "Configuration must be ServiceConfig or GroupConfig" in str(
        excinfo.value
    )


@pytest.mark.asyncio
async def test_group_not_found_error():
    """Test error handling when a group is not found."""
    server = AutoMCPServer("test", GroupConfig(name="test-group"))

    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="test_op", arguments={"value": 42})
        ]
    )

    # Request for a non-existent group
    response = await server._handle_service_request(
        "non-existent-group", request
    )

    assert "Group not found: non-existent-group" in response.content.text
    assert response.errors
    assert "Group not found: non-existent-group" in response.errors[0]


@pytest.mark.asyncio
async def test_operation_error_handling(group_config):
    """Test handling of operation execution errors."""
    server = AutoMCPServer("test", group_config)

    class ErrorGroup(ServiceGroup):
        @operation(schema=TestSchema)
        async def error_op(self, input: TestSchema) -> ExecutionResponse:
            raise ValueError("Test error")

    server.groups["test-group"] = ErrorGroup()

    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="error_op", arguments={"value": 42})
        ]
    )

    response = await server._handle_service_request("test-group", request)

    assert "error" in response.content.text.lower()
    assert response.errors
    assert "Test error" in str(response.errors[0])
