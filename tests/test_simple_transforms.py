"""Simple tests for parameter transformers."""

import pytest
from pydantic import BaseModel

from automcp.testing import (
    CompositeParameterTransformer,
    FlatParameterTransformer,
    NestedParameterTransformer,
    SchemaParameterTransformer,
)


class Person(BaseModel):
    """Test schema for a person."""

    name: str
    age: int


class TestSimpleTransformers:
    """Simple tests for parameter transformers."""

    @pytest.mark.asyncio
    async def test_flat_transformer(self):
        """Test FlatParameterTransformer."""
        # Arrange
        transformer = FlatParameterTransformer()
        arguments = {"name": "John", "age": 30}

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert
        assert result == arguments
        assert result["name"] == "John"
        assert result["age"] == 30

    @pytest.mark.asyncio
    async def test_nested_transformer(self):
        """Test NestedParameterTransformer."""
        # Arrange
        transformer = NestedParameterTransformer()
        operation_name = "greet_person"
        arguments = {
            "greet_person": {"name": "John", "age": 30},
            "other_param": "value",
        }

        # Act
        result = await transformer.transform(operation_name, arguments)

        # Assert
        assert result == {"name": "John", "age": 30}

    @pytest.mark.asyncio
    async def test_schema_transformer_flat(self):
        """Test SchemaParameterTransformer with flat parameters."""
        # Arrange
        transformer = SchemaParameterTransformer(Person)
        arguments = {"name": "John", "age": 30}

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert
        assert "person" in result
        assert isinstance(result["person"], Person)
        assert result["person"].name == "John"
        assert result["person"].age == 30

    @pytest.mark.asyncio
    async def test_schema_transformer_nested(self):
        """Test SchemaParameterTransformer with nested parameters."""
        # Arrange
        transformer = SchemaParameterTransformer(Person)
        arguments = {
            "person": {"name": "John", "age": 30},
            "other_param": "value",
        }

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert
        assert "person" in result
        assert isinstance(result["person"], Person)
        assert result["person"].name == "John"
        assert result["person"].age == 30
        assert "other_param" in result
        assert result["other_param"] == "value"

    @pytest.mark.asyncio
    async def test_composite_transformer(self):
        """Test CompositeParameterTransformer."""
        # Arrange
        schema_transformer = SchemaParameterTransformer(Person)
        nested_transformer = NestedParameterTransformer()

        transformer = CompositeParameterTransformer(
            [
                nested_transformer,
                schema_transformer,
            ]
        )

        operation_name = "greet_person"
        arguments = {"greet_person": {"name": "John", "age": 30}}

        # Act
        result = await transformer.transform(operation_name, arguments)

        # Assert - should use the nested transformer first
        assert result == {"name": "John", "age": 30}
