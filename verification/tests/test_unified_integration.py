"""Unified integration test demonstrating Parameter Transformers, TestServer, and Schema Registry.

This test demonstrates how all three components of the new testing infrastructure work together:
1. Parameter Transformers for standardized parameter handling
2. TestServer for simplified server testing
3. Schema Registry for centralized schema management
"""

from typing import Any, Dict, List

import pytest

from automcp.schemas.registry import SchemaRegistry
from automcp.server import AutoMCPServer
from automcp.testing.context import MockContext
from automcp.testing.server import TestServer
from automcp.testing.transforms import (
    CompositeParameterTransformer,
    FlatParameterTransformer,
    NestedParameterTransformer,
    SchemaParameterTransformer,
)
from automcp.types import GroupConfig
from verification.groups.example_group import ExampleGroup


@pytest.mark.asyncio
async def test_unified_integration():
    """Test integrating Parameter Transformers, TestServer, and Schema Registry."""
    # 1. Create a Schema Registry and register schemas
    registry = SchemaRegistry()

    # Register schemas from the automcp.schemas module
    from automcp.schemas import common

    registry.register_all_from_module(common)

    # List registered schemas for demonstration
    schema_names = registry.list_schemas()
    assert "PersonSchema" in schema_names
    assert "MessageSchema" in schema_names
    assert "ListProcessingSchema" in schema_names

    # 2. Create an AutoMCPServer with a simple example group
    server = AutoMCPServer(
        "unified-test-server",
        GroupConfig(name="test", description="Test server"),
    )

    # Add example group
    server.groups["example"] = ExampleGroup()

    # 3. Create Parameter Transformers for example group operations
    parameter_transformers = {
        "example.hello_world": FlatParameterTransformer(),
    }

    # 4. Create a TestServer with the parameter transformers
    test_server = TestServer(server, parameter_transformers)

    # 5. Test with the client
    async with test_server.create_client_session() as client:
        # Test hello_world operation
        response = await client.call_tool("example.hello_world", {})
        response_text = response.content[0].text if response.content else ""
        assert "Hello, World!" in response_text


@pytest.mark.asyncio
async def test_schema_registry_discovery():
    """Test schema registry discovery and field information."""
    # Create a schema registry and register schemas
    registry = SchemaRegistry()

    # Register schemas from the automcp.schemas module
    from automcp.schemas import common

    registry.register_all_from_module(common)

    # Verify that the schemas are registered
    person_schema = registry.get("PersonSchema")
    assert person_schema is not None

    # Get schema fields
    fields = registry.get_schema_fields("PersonSchema")
    assert "name" in fields
    assert "age" in fields
    assert "email" in fields

    # Use the schema to create a transformer
    person_transformer = SchemaParameterTransformer(person_schema, "person")

    # Test the transformer with flat parameters
    transformed = await person_transformer.transform(
        "greet_person", {"name": "John Doe", "age": 30}
    )

    # Verify the transformer created a PersonSchema instance
    assert "person" in transformed
    assert transformed["person"].name == "John Doe"
    assert transformed["person"].age == 30

    # Test the transformer with nested parameters
    transformed = await person_transformer.transform(
        "greet_person", {"person": {"name": "Jane Smith", "age": 25}}
    )

    # Verify the transformer handled the nested structure
    assert "person" in transformed
    assert transformed["person"].name == "Jane Smith"
    assert transformed["person"].age == 25


@pytest.mark.asyncio
async def test_test_server_error_handling():
    """Test the TestServer's error handling capabilities."""
    # Create an AutoMCPServer with a simple example group
    server = AutoMCPServer(
        "error-test-server",
        GroupConfig(name="example", description="Example group"),
    )
    server.groups["example"] = ExampleGroup()

    # Create parameter transformers
    parameter_transformers = {
        "example.hello_world": FlatParameterTransformer(),
    }

    # Create a TestServer
    test_server = TestServer(server, parameter_transformers)

    # Test with invalid parameters and operations
    async with test_server.create_client_session() as client:
        # Test with invalid operation name
        response = await client.call_tool("example.nonexistent_operation", {})
        response_text = response.content[0].text if response.content else ""
        assert (
            "unknown tool" in response_text.lower()
            or "error" in response_text.lower()
        )


@pytest.mark.asyncio
async def test_mock_context_usage():
    """Test using MockContext with operations."""
    # Test with a direct call to demonstrate how MockContext simplifies testing
    ctx = MockContext()

    # Report some progress
    await ctx.report_progress(1, 10)
    await ctx.report_progress(5, 10)
    await ctx.report_progress(10, 10)

    # Log some info
    ctx.info("Starting operation")
    ctx.info("Processing data")
    ctx.info("Operation complete")

    # Verify captured information
    assert len(ctx.progress_updates) == 3
    assert ctx.progress_updates[0] == (1, 10)
    assert ctx.progress_updates[1] == (5, 10)
    assert ctx.progress_updates[2] == (10, 10)

    assert len(ctx.info_messages) == 3
    assert ctx.info_messages[0] == "Starting operation"
    assert ctx.info_messages[1] == "Processing data"
    assert ctx.info_messages[2] == "Operation complete"

    # Example of using MockContext directly with an operation that doesn't require ctx
    example_group = ExampleGroup()
    result = await example_group.count_to(number=3)
    assert result == "1, 2, 3"
