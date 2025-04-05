"""Tests for the ServiceGroup class."""

import json

import pytest
from pydantic import BaseModel

from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.testing.context import MockContext
from automcp.types import ExecutionRequest, ExecutionResponse


class TestInput(BaseModel):
    """Test input schema."""

    value: str


class TestOutput(BaseModel):
    """Test output schema."""

    result: str
    status: str = "success"


class TestServiceGroup(ServiceGroup):
    """Test service group for testing ServiceGroup functionality."""

    @operation()
    async def basic_operation(self, value: str):
        """Basic operation without schema."""
        return f"Result: {value}"

    @operation(schema=TestInput)
    async def schema_operation(self, data: TestInput):
        """Operation with schema validation."""
        return f"Validated: {data.value}"

    @operation()
    async def context_operation(self, value: str, ctx: MockContext):
        """Operation that requires context."""
        ctx.info(f"Processing value: {value}")
        await ctx.report_progress(50, 100)
        return f"Context used, Value: {value}"

    @operation()
    async def error_operation(self, value: str):
        """Operation that raises an error."""
        raise ValueError(f"Test error: {value}")

    @operation(schema=TestInput)
    async def complex_return_operation(self, data: TestInput):
        """Operation that returns a complex Pydantic model."""
        return TestOutput(result=f"Processed: {data.value}")


@pytest.fixture
def service_group():
    """Create test service group instance."""
    return TestServiceGroup()


async def test_service_group_initialization(service_group):
    """Test ServiceGroup initialization and operation registration."""
    # Check that operations are registered correctly
    assert "basic_operation" in service_group.registry
    assert "schema_operation" in service_group.registry
    assert "context_operation" in service_group.registry
    assert "error_operation" in service_group.registry
    assert "complex_return_operation" in service_group.registry

    # Check that the registry is not empty
    assert not service_group._is_empty


async def test_execute_basic_operation(service_group):
    """Test executing a basic operation through the ServiceGroup.execute method."""
    request = ExecutionRequest(
        operation="basic_operation", arguments={"value": "test"}
    )
    response = await service_group.execute(request)

    assert response.error is None
    assert response.content.text == "Result: test"


async def test_execute_schema_operation(service_group):
    """Test executing an operation with schema validation."""
    # Valid input
    request = ExecutionRequest(
        operation="schema_operation", arguments={"value": "test"}
    )
    response = await service_group.execute(request)

    assert response.error is None
    assert response.content.text == "Validated: test"

    # Invalid input (missing required field)
    request = ExecutionRequest(
        operation="schema_operation", arguments={"invalid": "test"}
    )
    response = await service_group.execute(request)

    assert response.error is not None
    assert "Input validation failed" in response.error
    assert "Input validation failed" in response.content.text


async def test_execute_context_operation(service_group):
    """Test executing an operation that requires context."""
    # Create a context
    ctx = MockContext()

    request = ExecutionRequest(
        operation="context_operation", arguments={"value": "test", "ctx": ctx}
    )
    response = await service_group.execute(request)

    assert response.error is None
    assert response.content.text == "Context used, Value: test"

    # Check that the context was used correctly
    assert len(ctx.info_messages) == 1
    assert "Processing value: test" in ctx.info_messages[0]
    assert len(ctx.progress_updates) == 1
    assert ctx.progress_updates[0] == (50, 100)


async def test_execute_error_operation(service_group):
    """Test executing an operation that raises an error."""
    request = ExecutionRequest(
        operation="error_operation", arguments={"value": "test"}
    )
    response = await service_group.execute(request)

    assert response.error is not None
    assert "Error during 'error_operation' execution" in response.error
    assert "Test error: test" in response.error
    assert "Test error: test" in response.content.text


async def test_execute_unknown_operation(service_group):
    """Test executing an unknown operation."""
    request = ExecutionRequest(operation="unknown_operation", arguments={})
    response = await service_group.execute(request)

    assert response.error is not None
    assert "Unknown operation: unknown_operation" in response.error
    assert "Unknown operation: unknown_operation" in response.content.text


async def test_execute_complex_return_operation(service_group):
    """Test executing an operation that returns a complex Pydantic model."""
    request = ExecutionRequest(
        operation="complex_return_operation", arguments={"value": "test"}
    )
    response = await service_group.execute(request)

    assert response.error is None

    # Parse the JSON response
    result = json.loads(response.content.text)
    assert result["result"] == "Processed: test"
    assert result["status"] == "success"
