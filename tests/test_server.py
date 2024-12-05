"""AutoMCP server tests."""

import asyncio

import mcp.types as types
import pytest
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
    async def test_op(self, input: TestSchema) -> ExecutionResponse:
        """Test operation."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text=f"Result: {input.value}")
        )


@pytest.fixture
def group_config():
    return GroupConfig(
        name="test-group", description="Test group", config={"test": True}
    )


@pytest.fixture
def service_config():
    return ServiceConfig(
        name="test-service",
        groups={
            "test_server:TestGroup": GroupConfig(
                name="test-group", description="Test group", config={"test": True}
            )
        },
    )


@pytest.mark.asyncio
async def test_group_server(group_config):
    """Test server with single group."""
    server = AutoMCPServer("test", group_config)

    request = ServiceRequest(
        requests=[ExecutionRequest(operation="test_op", arguments={"value": 42})]
    )

    response = await server._handle_service_request("test-group", request)
    assert response.content.text == "Result: 42"
    assert not response.errors


@pytest.mark.asyncio
async def test_service_server(service_config):
    """Test server with service config."""
    server = AutoMCPServer("test", service_config)

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
