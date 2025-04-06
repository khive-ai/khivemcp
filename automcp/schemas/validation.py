"""Schema validation utilities for AutoMCP.

This module provides utilities for validating data against Pydantic schemas
and extracting parameters from various data structures.
"""

from typing import Any, Dict, Optional, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

# Define a type variable for the schema
SchemaType = TypeVar("SchemaType", bound=BaseModel)


def validate_schema(
    schema: Type[SchemaType],
    data: Dict[str, Any],
    partial: bool = False,
) -> SchemaType:
    """Validate data against a schema.

    Args:
        schema: The Pydantic schema class
        data: The data to validate
        partial: Whether to allow partial validation (missing fields)

    Returns:
        A validated schema instance

    Raises:
        ValidationError: If validation fails
    """
    if not issubclass(schema, BaseModel):
        raise TypeError(
            f"Schema must be a subclass of BaseModel, got {type(schema)}"
        )

    # If partial validation is requested, check required fields manually
    if partial:
        # Get the required fields from the schema
        required_fields = {
            field_name
            for field_name, field in schema.model_fields.items()
            if field.is_required()
        }

        # Check if all required fields are present
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            # Instead of trying to create a ValidationError directly,
            # let Pydantic handle it by attempting to create the model
            # This will raise the appropriate ValidationError
            try:
                return schema(**data)
            except ValidationError:
                # Re-raise the validation error
                raise

        # Create the schema instance with the provided fields
        return schema(**data)

    # Otherwise, perform full validation
    return schema(**data)


def extract_schema_parameters(
    schema: Type[BaseModel],
    data: Dict[str, Any],
    nested_key: str = None,
) -> Dict[str, Any]:
    """Extract parameters for a schema from data.

    This function handles both flat and nested parameters.

    Args:
        schema: The Pydantic schema class
        data: The data to extract parameters from
        nested_key: Optional key for nested parameters

    Returns:
        Extracted parameters
    """
    if not issubclass(schema, BaseModel):
        raise TypeError(
            f"Schema must be a subclass of BaseModel, got {type(schema)}"
        )

    # Get the schema fields
    schema_fields = (
        schema.model_fields.keys()
        if hasattr(schema, "model_fields")
        else schema.__annotations__.keys()
    )

    # Check if we have a nested structure with the nested_key
    if (
        nested_key
        and nested_key in data
        and isinstance(data[nested_key], dict)
    ):
        # Extract the nested parameters
        nested_data = data[nested_key]

        # Create a new arguments dict without the nested structure
        new_args = {k: v for k, v in data.items() if k != nested_key}

        # Validate and add the schema instance
        new_args[nested_key] = schema(**nested_data)

        return new_args

    # Check if we have flat parameters matching the schema fields
    schema_kwargs = {}
    other_kwargs = {}

    # Separate schema parameters from other kwargs
    for key, value in data.items():
        if key in schema_fields:
            schema_kwargs[key] = value
        else:
            other_kwargs[key] = value

    # If we have schema parameters, validate and create the schema instance
    if schema_kwargs:
        validated_input = schema(**schema_kwargs)

        # If nested_key is provided, use it as the key for the validated input
        if nested_key:
            other_kwargs[nested_key] = validated_input
            return other_kwargs
        else:
            # Otherwise, return the validated input directly
            return validated_input

    # If no schema parameters are found, return the original data
    return data


def create_schema_instance(
    schema: Type[SchemaType],
    data: Dict[str, Any],
    param_name: str = None,
) -> Dict[str, SchemaType]:
    """Create a schema instance from data and return it with the parameter name.

    Args:
        schema: The Pydantic schema class
        data: The data to create the schema instance from
        param_name: Optional parameter name, defaults to the schema class name in lowercase

    Returns:
        A dictionary with the parameter name as the key and the schema instance as the value
    """
    if not issubclass(schema, BaseModel):
        raise TypeError(
            f"Schema must be a subclass of BaseModel, got {type(schema)}"
        )

    # Determine the parameter name
    param_name = param_name or schema.__name__.lower()

    # Create the schema instance
    instance = validate_schema(schema, data)

    # Return the instance with the parameter name
    return {param_name: instance}
