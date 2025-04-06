"""Integration tests for SchemaRegistry with parameter transformers."""

import pytest
from pydantic import BaseModel, Field

from automcp.schemas.registry import SchemaRegistry
from automcp.testing.transforms import SchemaParameterTransformer


class TestSchema(BaseModel):
    """Test schema for integration tests."""

    name: str = Field(..., description="Test name")
    value: int = Field(..., description="Test value")
    optional: str | None = Field(None, description="Optional field")


@pytest.mark.asyncio
async def test_schema_registry_with_transformer():
    """Test integration between SchemaRegistry and SchemaParameterTransformer."""
    # Create a registry and register a schema
    registry = SchemaRegistry()
    registry.register(TestSchema)

    # Create a transformer using the registry
    transformer = registry.create_transformer("TestSchema")

    # Test flat parameters
    arguments = {"name": "test", "value": 42, "other": "other"}
    transformed = await transformer.transform("test_operation", arguments)

    assert "testschema" in transformed
    assert isinstance(transformed["testschema"], TestSchema)
    assert transformed["testschema"].name == "test"
    assert transformed["testschema"].value == 42
    assert transformed["testschema"].optional is None
    assert transformed["other"] == "other"

    # Test nested parameters
    arguments = {"testschema": {"name": "test", "value": 42}, "other": "other"}
    transformed = await transformer.transform("test_operation", arguments)

    assert "testschema" in transformed
    assert isinstance(transformed["testschema"], TestSchema)
    assert transformed["testschema"].name == "test"
    assert transformed["testschema"].value == 42
    assert transformed["testschema"].optional is None
    assert transformed["other"] == "other"


@pytest.mark.asyncio
async def test_schema_registry_with_custom_param_name():
    """Test integration with custom parameter name."""
    # Create a registry and register a schema
    registry = SchemaRegistry()
    registry.register(TestSchema)

    # Create a transformer with a custom parameter name
    transformer = registry.create_transformer(
        "TestSchema", param_name="custom"
    )

    # Test flat parameters
    arguments = {"name": "test", "value": 42, "other": "other"}
    transformed = await transformer.transform("test_operation", arguments)

    assert "custom" in transformed
    assert isinstance(transformed["custom"], TestSchema)
    assert transformed["custom"].name == "test"
    assert transformed["custom"].value == 42
    assert transformed["custom"].optional is None
    assert transformed["other"] == "other"

    # Test nested parameters
    arguments = {"custom": {"name": "test", "value": 42}, "other": "other"}
    transformed = await transformer.transform("test_operation", arguments)

    assert "custom" in transformed
    assert isinstance(transformed["custom"], TestSchema)
    assert transformed["custom"].name == "test"
    assert transformed["custom"].value == 42
    assert transformed["custom"].optional is None
    assert transformed["other"] == "other"


@pytest.mark.asyncio
async def test_multiple_transformers_from_registry():
    """Test creating and using multiple transformers from the registry."""
    # Create a registry and register multiple schemas
    registry = SchemaRegistry()
    registry.register(TestSchema)

    # Create a second test schema
    class AnotherSchema(BaseModel):
        """Another test schema."""

        id: str = Field(..., description="ID")
        count: int = Field(..., description="Count")

    registry.register(AnotherSchema)

    # Create transformers for both schemas
    test_transformer = registry.create_transformer("TestSchema")
    another_transformer = registry.create_transformer("AnotherSchema")

    # Test the first transformer
    arguments = {"name": "test", "value": 42}
    transformed = await test_transformer.transform("test_operation", arguments)

    assert "testschema" in transformed
    assert isinstance(transformed["testschema"], TestSchema)

    # Test the second transformer
    arguments = {"id": "123", "count": 5}
    transformed = await another_transformer.transform(
        "another_operation", arguments
    )

    assert "anotherschema" in transformed
    assert isinstance(transformed["anotherschema"], AnotherSchema)
    assert transformed["anotherschema"].id == "123"
    assert transformed["anotherschema"].count == 5
