"""Tests for parameter transformation utilities."""

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


class TestFlatParameterTransformer:
    """Tests for FlatParameterTransformer."""

    @pytest.mark.asyncio
    async def test_transform_flat_parameters(self):
        """Test transforming flat parameters."""
        # Arrange
        transformer = FlatParameterTransformer()
        arguments = {"name": "John", "age": 30}

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert
        assert result == arguments
        assert result["name"] == "John"
        assert result["age"] == 30


class TestNestedParameterTransformer:
    """Tests for NestedParameterTransformer."""

    @pytest.mark.asyncio
    async def test_transform_nested_parameters(self):
        """Test transforming nested parameters."""
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
    async def test_transform_flat_parameters(self):
        """Test transforming flat parameters when no nested structure exists."""
        # Arrange
        transformer = NestedParameterTransformer()
        operation_name = "greet_person"
        arguments = {"name": "John", "age": 30}

        # Act
        result = await transformer.transform(operation_name, arguments)

        # Assert
        assert result == arguments


class TestSchemaParameterTransformer:
    """Tests for SchemaParameterTransformer."""

    @pytest.mark.asyncio
    async def test_transform_flat_parameters(self):
        """Test transforming flat parameters into a schema instance."""
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
    async def test_transform_nested_parameters(self):
        """Test transforming nested parameters into a schema instance."""
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
    async def test_transform_with_custom_param_name(self):
        """Test transforming parameters with a custom parameter name."""
        # Arrange
        transformer = SchemaParameterTransformer(Person, param_name="user")
        arguments = {"name": "John", "age": 30}

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert
        assert "user" in result
        assert isinstance(result["user"], Person)
        assert result["user"].name == "John"
        assert result["user"].age == 30

    @pytest.mark.asyncio
    async def test_transform_unrelated_parameters(self):
        """Test transforming parameters that don't match the schema."""
        # Arrange
        transformer = SchemaParameterTransformer(Person)
        arguments = {"unrelated": "value"}

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert
        assert result == arguments


class TestCompositeParameterTransformer:
    """Tests for CompositeParameterTransformer."""

    @pytest.mark.asyncio
    async def test_transform_with_multiple_transformers(self):
        """Test transforming parameters with multiple transformers."""
        # Arrange
        schema_transformer = SchemaParameterTransformer(Person)
        nested_transformer = NestedParameterTransformer()
        flat_transformer = FlatParameterTransformer()

        transformer = CompositeParameterTransformer(
            [schema_transformer, nested_transformer, flat_transformer]
        )

        operation_name = "greet_person"
        arguments = {"greet_person": {"name": "John", "age": 30}}

        # Act
        result = await transformer.transform(operation_name, arguments)

        # Assert - should use the nested transformer
        assert result == {"name": "John", "age": 30}

    @pytest.mark.asyncio
    async def test_transform_with_schema_transformer(self):
        """Test transforming parameters that match a schema."""
        # Arrange
        schema_transformer = SchemaParameterTransformer(Person)
        nested_transformer = NestedParameterTransformer()

        transformer = CompositeParameterTransformer(
            [schema_transformer, nested_transformer]
        )

        arguments = {"name": "John", "age": 30}

        # Act
        result = await transformer.transform("test_operation", arguments)

        # Assert - should use the schema transformer
        assert "person" in result
        assert isinstance(result["person"], Person)
        assert result["person"].name == "John"
        assert result["person"].age == 30
