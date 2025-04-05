"""Tests for context parameter handling with positional arguments."""

import pytest
from mcp.server.fastmcp import Context

from automcp.operation import operation
from automcp.testing.context import MockContext


class TestContextService:
    """Test service class for context parameter handling tests."""

    @operation()
    async def positional_context_operation(
        self, value: str, ctx: Context
    ) -> str:
        """Operation with context as the second parameter."""
        return f"Value: {value}, Context: {ctx.request_id}"

    @operation()
    async def multiple_args_with_context(
        self, arg1: int, arg2: float, ctx: Context
    ) -> str:
        """Operation with multiple arguments and context."""
        return f"Arg1: {arg1}, Arg2: {arg2}, Context: {ctx.request_id}"


@pytest.fixture
def service():
    """Create test service instance."""
    return TestContextService()


@pytest.fixture
def context():
    """Create test context."""
    ctx = MockContext()
    ctx.request_id = "test-123"
    return ctx


async def test_positional_context(service, context):
    """Test operation with context as a positional argument."""
    # Test with context as a positional argument
    result = await service.positional_context_operation("test", context)
    assert result == "Value: test, Context: test-123"

    # Test with context as a keyword argument
    result = await service.positional_context_operation("test", ctx=context)
    assert result == "Value: test, Context: test-123"

    # Test with mixed positional and keyword arguments
    # This should not cause "multiple values for argument 'ctx'" error
    result = await service.positional_context_operation(
        value="test", ctx=context
    )
    assert result == "Value: test, Context: test-123"


async def test_multiple_args_with_context(service, context):
    """Test operation with multiple arguments and context."""
    # Test with all positional arguments
    result = await service.multiple_args_with_context(1, 2.5, context)
    assert result == "Arg1: 1, Arg2: 2.5, Context: test-123"

    # Test with mixed positional and keyword arguments
    result = await service.multiple_args_with_context(1, arg2=2.5, ctx=context)
    assert result == "Arg1: 1, Arg2: 2.5, Context: test-123"

    # Test with all keyword arguments
    result = await service.multiple_args_with_context(
        arg1=1, arg2=2.5, ctx=context
    )
    assert result == "Arg1: 1, Arg2: 2.5, Context: test-123"
