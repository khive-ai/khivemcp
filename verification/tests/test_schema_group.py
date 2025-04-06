"""Tests for the SchemaGroup service group using the new testing infrastructure."""

import pytest

from automcp.schemas import ListProcessingSchema, MessageSchema, PersonSchema
from automcp.schemas.registry import SchemaRegistry
from automcp.server import AutoMCPServer
from automcp.testing.context import MockContext
from automcp.testing.server import TestServer
from automcp.testing.transforms import SchemaParameterTransformer
from automcp.types import GroupConfig
from verification.groups.schema_group import SchemaGroup


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
    # Use MockContext from the new testing infrastructure
    ctx = MockContext()

    # Pass schema parameters as keyword arguments and ctx as a separate argument
    result = await group.repeat_message(text="Hello", repeat=3, ctx=ctx)
    assert result == "Hello Hello Hello"

    # Verify that progress was reported
    assert len(ctx.progress_reports) == 3
    assert ctx.progress_reports[-1] == (
        3,
        3,
    )  # Last report should be (current=3, total=3)


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


@pytest.mark.asyncio
async def test_schema_group_via_testserver():
    """Test SchemaGroup operations via TestServer using schema registry."""
    # Create a schema registry
    registry = SchemaRegistry()
    registry.register(PersonSchema)
    registry.register(MessageSchema)
    registry.register(ListProcessingSchema)

    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)
    server.groups["schema"] = SchemaGroup()

    # Create parameter transformers for each schema
    parameter_transformers = {
        "schema.greet_person": registry.create_transformer(
            "PersonSchema", "person"
        ),
        "schema.repeat_message": registry.create_transformer(
            "MessageSchema", "message"
        ),
        "schema.process_list": registry.create_transformer(
            "ListProcessingSchema", "data"
        ),
    }

    # Create a test server
    test_server = TestServer(server, parameter_transformers)

    # Test via client
    async with test_server.create_client_session() as client:
        # Test greet_person
        result = await client.execute_tool(
            "schema.greet_person",
            {"name": "John Doe", "age": 30, "email": "john@example.com"},
        )
        assert "Hello, John Doe!" in result.text
        assert "30 years old" in result.text
        assert "john@example.com" in result.text

        # Test repeat_message
        result = await client.execute_tool(
            "schema.repeat_message", {"text": "World", "repeat": 2}
        )
        assert "World World" in result.text

        # Test process_list
        result = await client.execute_tool(
            "schema.process_list",
            {
                "items": ["apple", "banana"],
                "prefix": "Fruit:",
                "uppercase": True,
            },
        )
        assert "Fruit: APPLE" in result.text
        assert "Fruit: BANANA" in result.text


@pytest.mark.asyncio
async def test_schema_validation_errors():
    """Test schema validation error handling with TestServer."""
    # Create a schema registry
    registry = SchemaRegistry()
    registry.register(PersonSchema)

    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)
    server.groups["schema"] = SchemaGroup()

    # Create parameter transformers
    parameter_transformers = {
        "schema.greet_person": registry.create_transformer(
            "PersonSchema", "person"
        ),
    }

    # Create a test server
    test_server = TestServer(server, parameter_transformers)

    # Test via client
    async with test_server.create_client_session() as client:
        # Test with missing required field
        result = await client.execute_tool(
            "schema.greet_person", {"name": "John Doe"}  # Missing age
        )
        assert "error" in result.text.lower()

        # Test with invalid field type
        result = await client.execute_tool(
            "schema.greet_person",
            {"name": "John Doe", "age": "thirty"},  # Should be an integer
        )
        assert "error" in result.text.lower()
