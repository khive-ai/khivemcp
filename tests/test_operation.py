"""Tests for the operation decorator."""

import pytest
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from automcp.operation import operation


class TestInput(BaseModel):
    """Test input schema."""

    value: str


class TestService:
    """Test service class for operation decorator tests."""

    @operation()
    async def basic_operation(self, value: str):
        """Basic operation without schema or context."""
        return f"Result: {value}"

    @operation(schema=TestInput)
    async def schema_operation(self, data: TestInput):
        """Operation with schema validation."""
        return f"Validated: {data.value}"

    @operation()
    async def context_operation(self, value: str, ctx: Context):
        """Operation that requires context."""
        return f"Context: {ctx.request_id}, Value: {value}"

    @operation(schema=TestInput)
    async def schema_context_operation(self, data: TestInput, ctx: Context):
        """Operation with both schema and context."""
        return f"Context: {ctx.request_id}, Validated: {data.value}"

    @operation(name="custom_name", policy="test_policy")
    async def named_operation(self, value: str):
        """Operation with custom name and policy."""
        return f"Named: {value}"


@pytest.fixture
def service():
    """Create test service instance."""
    return TestService()


@pytest.fixture
def context():
    """Create test context."""
    return Context(request_id="test-123")


async def test_basic_operation(service):
    """Test basic operation without schema or context."""
    result = await service.basic_operation("test")
    assert result == "Result: test"


async def test_schema_operation(service):
    """Test operation with schema validation."""
    result = await service.schema_operation(value="test")
    assert result == "Validated: test"

    with pytest.raises(ValueError):
        await service.schema_operation(invalid="test")


async def test_context_operation(service, context):
    """Test operation that requires context."""
    result = await service.context_operation("test", ctx=context)
    assert result == "Context: test-123, Value: test"


async def test_schema_context_operation(service, context):
    """Test operation with both schema and context."""
    result = await service.schema_context_operation(value="test", ctx=context)
    assert result == "Context: test-123, Validated: test"


async def test_operation_metadata(service):
    """Test operation metadata attributes."""
    assert service.basic_operation.is_operation
    assert service.basic_operation.op_name == "basic_operation"
    assert service.basic_operation.schema is None
    assert service.basic_operation.policy is None

    assert service.named_operation.op_name == "custom_name"
    assert service.named_operation.policy == "test_policy"


async def test_context_detection(service):
    """Test automatic context requirement detection."""
    assert not service.basic_operation.requires_context
    assert not service.schema_operation.requires_context
    assert service.context_operation.requires_context
    assert service.schema_context_operation.requires_context


async def test_backward_compatibility(service):
    """Test backward compatibility with existing operations."""
    # Operations without context should work without ctx parameter
    result = await service.basic_operation("test")
    assert result == "Result: test"

    # Operations with schema should work as before
    result = await service.schema_operation(value="test")
    assert result == "Validated: test"

    # Context operations should work with or without context
    result = await service.context_operation("test")  # No context
    assert result == "Context: None, Value: test"

    result = await service.context_operation("test", ctx=context)  # With context
    assert result == "Context: test-123, Value: test"
