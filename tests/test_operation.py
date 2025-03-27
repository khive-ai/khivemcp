"""Tests for operation decorator and execution."""

import pytest
from pydantic import BaseModel

from automcp import ServiceGroup, operation
from automcp.types import ExecutionRequest, ExecutionResponse


class TestInput(BaseModel):
    """Test input schema."""

    value: str


class TestGroup(ServiceGroup):
    """Test service group."""

    @operation(schema=TestInput)
    async def test_operation(self, input: TestInput) -> ExecutionResponse:
        """Test operation with schema."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text=f"Received: {input.value}")
        )

    @operation()
    async def simple_operation(self) -> ExecutionResponse:
        """Test operation without schema."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text="Simple operation")
        )

    @operation(name="custom_name")
    async def internal_name(self) -> ExecutionResponse:
        """Test operation with custom name."""
        return ExecutionResponse(
            content=types.TextContent(type="text", text="Custom named operation")
        )


@pytest.mark.asyncio
async def test_operation_with_schema():
    """Test operation with input schema."""
    group = TestGroup()
    request = ExecutionRequest(operation="test_operation", arguments={"value": "test"})

    response = await group._execute(request)
    assert not response.error
    assert response.content.text == "Received: test"


@pytest.mark.asyncio
async def test_operation_schema_validation():
    """Test operation input validation."""
    group = TestGroup()
    request = ExecutionRequest(
        operation="test_operation",
        arguments={"invalid": "test"},  # Missing required 'value' field
    )

    response = await group._execute(request)
    assert response.error
    assert "value" in response.content.text.lower()


@pytest.mark.asyncio
async def test_simple_operation():
    """Test operation without schema."""
    group = TestGroup()
    request = ExecutionRequest(operation="simple_operation")

    response = await group._execute(request)
    assert not response.error
    assert response.content.text == "Simple operation"


@pytest.mark.asyncio
async def test_custom_named_operation():
    """Test operation with custom name."""
    group = TestGroup()
    request = ExecutionRequest(operation="custom_name")

    response = await group._execute(request)
    assert not response.error
    assert response.content.text == "Custom named operation"


@pytest.mark.asyncio
async def test_unknown_operation():
    """Test handling of unknown operation."""
    group = TestGroup()
    request = ExecutionRequest(operation="unknown_operation")

    response = await group._execute(request)
    assert response.error
    assert "unknown operation" in response.content.text.lower()


@pytest.mark.asyncio
async def test_operation_error_handling():
    """Test operation error handling."""

    class ErrorGroup(ServiceGroup):
        @operation()
        async def error_operation(self) -> ExecutionResponse:
            raise ValueError("Test error")

    group = ErrorGroup()
    request = ExecutionRequest(operation="error_operation")

    response = await group._execute(request)
    assert response.error
    assert "test error" in response.content.text.lower()
