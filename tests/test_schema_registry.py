"""Tests for the SchemaRegistry class."""

import pytest
from pydantic import BaseModel, Field

from automcp.schemas.common import (
    ListProcessingSchema,
    MessageSchema,
    PersonSchema,
)
from automcp.schemas.registry import SchemaRegistry
from automcp.testing.transforms import SchemaParameterTransformer


class TestSchema(BaseModel):
    """Test schema for registry tests."""

    name: str = Field(..., description="Test name")
    value: int = Field(..., description="Test value")


def test_schema_registry_init():
    """Test SchemaRegistry initialization."""
    registry = SchemaRegistry()
    assert registry.schemas == {}


def test_schema_registry_register():
    """Test registering a schema."""
    registry = SchemaRegistry()
    registry.register(TestSchema)

    assert "TestSchema" in registry.schemas
    assert registry.schemas["TestSchema"] == TestSchema


def test_schema_registry_register_with_name():
    """Test registering a schema with a custom name."""
    registry = SchemaRegistry()
    registry.register(TestSchema, name="CustomName")

    assert "CustomName" in registry.schemas
    assert registry.schemas["CustomName"] == TestSchema


def test_schema_registry_register_invalid():
    """Test registering an invalid schema."""
    registry = SchemaRegistry()

    with pytest.raises(TypeError):
        registry.register(str)  # Not a BaseModel subclass


def test_schema_registry_get():
    """Test getting a schema by name."""
    registry = SchemaRegistry()
    registry.register(TestSchema)

    schema = registry.get("TestSchema")
    assert schema == TestSchema

    # Test getting a non-existent schema
    assert registry.get("NonExistentSchema") is None


def test_schema_registry_register_all_from_module():
    """Test registering all schemas from a module."""
    registry = SchemaRegistry()

    # Import the module containing schemas
    import automcp.schemas.common as common_module

    # Register all schemas from the module
    registered = registry.register_all_from_module(common_module)

    # Check that all expected schemas were registered
    assert "PersonSchema" in registered
    assert "MessageSchema" in registered
    assert "ListProcessingSchema" in registered

    # Check that the schemas are in the registry
    assert registry.get("PersonSchema") == PersonSchema
    assert registry.get("MessageSchema") == MessageSchema
    assert registry.get("ListProcessingSchema") == ListProcessingSchema


def test_schema_registry_create_transformer():
    """Test creating a parameter transformer for a registered schema."""
    registry = SchemaRegistry()
    registry.register(TestSchema)

    # Create a transformer
    transformer = registry.create_transformer("TestSchema")

    # Check that the transformer is of the correct type
    assert isinstance(transformer, SchemaParameterTransformer)
    assert transformer.schema_class == TestSchema
    assert transformer.param_name == "testschema"

    # Test creating a transformer with a custom param name
    transformer = registry.create_transformer(
        "TestSchema", param_name="custom"
    )
    assert transformer.param_name == "custom"

    # Test creating a transformer for a non-existent schema
    with pytest.raises(ValueError):
        registry.create_transformer("NonExistentSchema")


def test_schema_registry_list_schemas():
    """Test listing all registered schema names."""
    registry = SchemaRegistry()
    registry.register(TestSchema)
    registry.register(PersonSchema)

    schemas = registry.list_schemas()
    assert "TestSchema" in schemas
    assert "PersonSchema" in schemas
    assert len(schemas) == 2


def test_schema_registry_get_schema_fields():
    """Test getting the fields of a registered schema."""
    registry = SchemaRegistry()
    registry.register(TestSchema)

    fields = registry.get_schema_fields("TestSchema")
    assert "name" in fields
    assert "value" in fields

    # Test getting fields of a non-existent schema
    with pytest.raises(ValueError):
        registry.get_schema_fields("NonExistentSchema")
