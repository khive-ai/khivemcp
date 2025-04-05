"""Tests for the SchemaGroup service group."""

import pytest
from mcp.types import TextContent

from verification.groups.schema_group import SchemaGroup
from verification.schemas import (
    ListProcessingSchema,
    MessageSchema,
    PersonSchema,
)


@pytest.mark.asyncio
async def test_greet_person_direct():
    """Test greet_person operation directly."""
    group = SchemaGroup()
    # Pass schema parameters as keyword arguments
    result = await group.greet_person(
        name="John", age=30, email="john@example.com"
    )
    assert "Hello, John!" in result
    assert "30 years old" in result
    assert "john@example.com" in result

    # Test without optional email
    result = await group.greet_person(name="Alice", age=25)
    assert "Hello, Alice!" in result
    assert "25 years old" in result
    assert "email" not in result


@pytest.mark.asyncio
async def test_repeat_message_direct():
    """Test repeat_message operation directly."""
    group = SchemaGroup()
    # Create a TextContent object to use as Context
    ctx = TextContent(type="text", text="")

    # Add the required methods for testing
    async def report_progress(current, total):
        pass

    def info(message):
        pass

    ctx.report_progress = report_progress
    ctx.info = info

    # Pass schema parameters as keyword arguments and ctx as a separate argument
    result = await group.repeat_message(text="Hello", repeat=3, ctx=ctx)
    assert result == "Hello Hello Hello"


@pytest.mark.asyncio
async def test_process_list_direct():
    """Test process_list operation directly."""
    group = SchemaGroup()

    # Test with default settings
    result = await group.process_list(items=["one", "two"])
    assert result == ["Item: one", "Item: two"]

    # Test with custom prefix and uppercase
    result = await group.process_list(
        items=["one", "two"], prefix=">>", uppercase=True
    )
    assert result == [">> ONE", ">> TWO"]


# Skip MCP client tests for now - we'll implement these once we have the proper MCP client setup
@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_schema_group_via_mcp():
    """Test SchemaGroup operations via MCP client."""
    # This test will be implemented with proper MCP client setup
    assert True


@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_schema_validation_errors():
    """Test schema validation error handling."""
    # This test will be implemented with proper MCP client setup
    assert True
