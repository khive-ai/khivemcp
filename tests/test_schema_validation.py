"""Tests for schema validation utilities."""

import pytest
from pydantic import BaseModel, Field, ValidationError

from automcp.schemas.validation import (
    create_schema_instance,
    extract_schema_parameters,
    validate_schema,
)


class TestSchema(BaseModel):
    """Test schema for validation tests."""

    name: str = Field(..., description="Test name")
    value: int = Field(..., description="Test value")
    optional: str | None = Field(None, description="Optional field")


def test_validate_schema():
    """Test validating data against a schema."""
    # Test valid data
    data = {"name": "test", "value": 42, "optional": "optional"}
    result = validate_schema(TestSchema, data)

    assert isinstance(result, TestSchema)
    assert result.name == "test"
    assert result.value == 42
    assert result.optional == "optional"

    # Test valid data with missing optional field
    data = {"name": "test", "value": 42}
    result = validate_schema(TestSchema, data)

    assert isinstance(result, TestSchema)
    assert result.name == "test"
    assert result.value == 42
    assert result.optional is None

    # Test invalid data (missing required field)
    data = {"name": "test"}
    with pytest.raises(ValidationError):
        validate_schema(TestSchema, data)

    # Test invalid data (wrong type)
    data = {"name": "test", "value": "not an int"}
    with pytest.raises(ValidationError):
        validate_schema(TestSchema, data)

    # Test invalid schema type
    with pytest.raises(TypeError):
        validate_schema(str, data)  # Not a BaseModel subclass


def test_validate_schema_partial():
    """Test partial validation of data against a schema."""
    # Test partial validation with missing optional field
    data = {"name": "test", "value": 42}
    result = validate_schema(TestSchema, data, partial=True)

    assert isinstance(result, TestSchema)
    assert result.name == "test"
    assert result.value == 42
    assert result.optional is None

    # Test partial validation with missing required field
    data = {"name": "test"}
    with pytest.raises(ValidationError):
        validate_schema(TestSchema, data, partial=True)


def test_extract_schema_parameters():
    """Test extracting parameters for a schema from data."""
    # Test flat parameters
    data = {"name": "test", "value": 42, "other": "other"}
    result = extract_schema_parameters(TestSchema, data)

    assert isinstance(result, TestSchema)
    assert result.name == "test"
    assert result.value == 42
    assert result.optional is None

    # Test nested parameters with nested_key
    data = {"test_schema": {"name": "test", "value": 42}, "other": "other"}
    result = extract_schema_parameters(
        TestSchema, data, nested_key="test_schema"
    )

    assert isinstance(result, dict)
    assert "test_schema" in result
    assert isinstance(result["test_schema"], TestSchema)
    assert result["test_schema"].name == "test"
    assert result["test_schema"].value == 42
    assert result["test_schema"].optional is None
    assert result["other"] == "other"

    # Test with no matching parameters
    data = {"other": "other"}
    result = extract_schema_parameters(TestSchema, data)

    assert result == data

    # Test invalid schema type
    with pytest.raises(TypeError):
        extract_schema_parameters(str, data)  # Not a BaseModel subclass


def test_create_schema_instance():
    """Test creating a schema instance from data."""
    # Test with default parameter name
    data = {"name": "test", "value": 42}
    result = create_schema_instance(TestSchema, data)

    assert isinstance(result, dict)
    assert "testschema" in result
    assert isinstance(result["testschema"], TestSchema)
    assert result["testschema"].name == "test"
    assert result["testschema"].value == 42
    assert result["testschema"].optional is None

    # Test with custom parameter name
    data = {"name": "test", "value": 42}
    result = create_schema_instance(TestSchema, data, param_name="custom")

    assert isinstance(result, dict)
    assert "custom" in result
    assert isinstance(result["custom"], TestSchema)
    assert result["custom"].name == "test"
    assert result["custom"].value == 42
    assert result["custom"].optional is None

    # Test with invalid data
    data = {"name": "test"}  # Missing required field
    with pytest.raises(ValidationError):
        create_schema_instance(TestSchema, data)

    # Test invalid schema type
    with pytest.raises(TypeError):
        create_schema_instance(str, data)  # Not a BaseModel subclass
