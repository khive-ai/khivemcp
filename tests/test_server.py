"""Tests for AutoMCP server implementation."""

import asyncio
import json
import tempfile
from pathlib import Path

import mcp.types as types
import pytest
import yaml

from automcp import (
    AutoMCPServer,
    ExecutionRequest,
    ExecutionResponse,
    GroupConfig,
    ServiceConfig,
    ServiceGroup,
    ServiceRequest,
    ServiceResponse,
    operation,
)


class TestOperation(ServiceGroup):
    """Test operation group."""

    @operation()
    async def test(self) -> ExecutionResponse:
        """Test operation."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text="Test successful")
        )


def create_test_config(tmp_path: Path, config_type: str = "service"):
    """Create test configuration file."""
    if config_type == "service":
        config = {
            "name": "test-service",
            "description": "Test service",
            "groups": {
                "tests.test_server:TestOperation": {
                    "name": "test-group",
                    "description": "Test group",
                }
            },
        }
        path = tmp_path / "service.yaml"
        with open(path, "w") as f:
            yaml.dump(config, f)
    else:
        config = {"name": "test-group", "description": "Test group"}
        path = tmp_path / "group.json"
        with open(path, "w") as f:
            json.dump(config, f)

    return path


@pytest.fixture
async def server():
    """Server fixture with proper cleanup."""
    servers = []

    async def create_server(config):
        server = AutoMCPServer(name="test", config=config)
        servers.append(server)
        return server

    yield create_server

    # Cleanup all servers
    for server in servers:
        for group in server.groups.values():
            if hasattr(group, "cleanup") and callable(group.cleanup):
                await group.cleanup()


@pytest.mark.asyncio
async def test_server_initialization(tmp_path, server):
    """Test server initialization with service config."""
    config_path = create_test_config(tmp_path, "service")
    with open(config_path) as f:
        config = ServiceConfig(**yaml.safe_load(f))

    srv = await server(config)
    assert "test-group" in srv.groups
    assert isinstance(srv.groups["test-group"], TestOperation)


@pytest.mark.asyncio
async def test_single_group_initialization(tmp_path, server):
    """Test server initialization with group config."""
    config_path = create_test_config(tmp_path, "group")
    with open(config_path) as f:
        config = GroupConfig(**json.load(f))

    srv = await server(config)
    assert "test-group" in srv.groups
    assert isinstance(srv.groups["test-group"], ServiceGroup)


@pytest.mark.asyncio
async def test_service_request_handling(server, test_group_config):
    """Test handling of service requests."""
    srv = await server(test_group_config)
    srv.groups["test-group"] = TestOperation()

    request = ServiceRequest(requests=[ExecutionRequest(operation="test")])

    response = await srv._handle_service_request("test-group", request)
    assert not response.errors
    assert "Test successful" in response.content.text


@pytest.mark.asyncio
async def test_unknown_group_handling(server, test_group_config):
    """Test handling of requests for unknown groups."""
    srv = await server(test_group_config)

    request = ServiceRequest(requests=[ExecutionRequest(operation="test")])

    response = await srv._handle_service_request("unknown-group", request)
    assert response.errors
    assert "Group not found" in response.errors[0]


@pytest.mark.asyncio
async def test_operation_timeout(server, test_group_config):
    """Test operation timeout handling."""

    class SlowOperation(ServiceGroup):
        @operation()
        async def slow(self) -> ExecutionResponse:
            try:
                await asyncio.sleep(2)  # Longer than timeout
                return ExecutionResponse(
                    content=types.TextContent(type="text", text="Done")
                )
            except asyncio.CancelledError:
                # Clean cancellation
                raise
            finally:
                # Ensure cleanup
                await self.cleanup()

    srv = await server(test_group_config)
    srv.timeout = 0.1
    srv.groups["test-group"] = SlowOperation()

    request = ServiceRequest(requests=[ExecutionRequest(operation="slow")])

    response = await srv._handle_service_request("test-group", request)
    assert response.errors
    assert "timeout" in response.errors[0].lower()


@pytest.mark.asyncio
async def test_concurrent_requests(server, test_group_config):
    """Test handling of concurrent requests."""

    class MultiOperation(ServiceGroup):
        def __init__(self):
            super().__init__()
            self._lock = asyncio.Lock()

        @operation()
        async def op1(self) -> ExecutionResponse:
            async with self._lock:
                return ExecutionResponse(
                    content=types.TextContent(type="text", text="First")
                )

        @operation()
        async def op2(self) -> ExecutionResponse:
            async with self._lock:
                return ExecutionResponse(
                    content=types.TextContent(type="text", text="Second")
                )

        async def cleanup(self):
            """Clean up resources."""
            await super().cleanup()

    srv = await server(test_group_config)
    srv.groups["test-group"] = MultiOperation()

    request = ServiceRequest(
        requests=[ExecutionRequest(operation="op1"), ExecutionRequest(operation="op2")]
    )

    response = await srv._handle_service_request("test-group", request)
    assert not response.errors
    assert "First" in response.content.text
    assert "Second" in response.content.text


@pytest.mark.asyncio
async def test_tool_listing(server, test_group_config):
    """Test tool listing functionality."""
    srv = await server(test_group_config)

    tools = await srv.server.list_tools()
    assert len(tools) > 0
    for tool in tools:
        assert isinstance(tool, types.Tool)
        assert tool.name.startswith("test-group.")
