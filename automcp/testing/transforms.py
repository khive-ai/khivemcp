"""Parameter transformation utilities for testing.

This module provides utilities for transforming parameters between different formats
when testing AutoMCP operations. It helps standardize parameter handling and eliminates
the need for special case handlers in test code.
"""

import json
from typing import Any, Dict, Protocol, Type, TypeVar, cast

import mcp.types as types
from pydantic import BaseModel

# Define a type variable for the schema
SchemaType = TypeVar("SchemaType", bound=BaseModel)


class ParameterTransformer(Protocol):
    """Protocol for parameter transformers.

    Parameter transformers are responsible for converting raw arguments from
    client calls into the structured format expected by operations. This allows
    for standardized parameter handling without special case handlers.
    """

    async def transform(
        self,
        operation_name: str,
        arguments: Dict[str, Any],
        context: types.TextContent | None = None,
    ) -> Dict[str, Any]:
        """Transform parameters for an operation.

        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context

        Returns:
            Transformed arguments
        """
        ...


class FlatParameterTransformer:
    """Parameter transformer for flat parameters.

    This transformer passes through parameters as-is, assuming they are already
    in the correct format for the operation (flat key-value pairs).

    Example:
        Input: {"name": "John", "age": 30}
        Output: {"name": "John", "age": 30}
    """

    async def transform(
        self,
        operation_name: str,
        arguments: Dict[str, Any],
        context: types.TextContent | None = None,
    ) -> Dict[str, Any]:
        """Transform parameters using flat pass-through.

        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context

        Returns:
            The original arguments unchanged
        """
        return arguments


class NestedParameterTransformer:
    """Parameter transformer for nested parameters.

    This transformer extracts parameters from a nested structure where the
    operation name is used as the key for the nested parameters.

    Example:
        Input: {"operation_name": {"param1": "value1", "param2": "value2"}}
        Output: {"param1": "value1", "param2": "value2"}
    """

    async def transform(
        self,
        operation_name: str,
        arguments: Dict[str, Any],
        context: types.TextContent | None = None,
    ) -> Dict[str, Any]:
        """Transform parameters by extracting from nested structure.

        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context

        Returns:
            Extracted arguments from the nested structure
        """
        # Check if arguments contain a key matching the operation name
        if operation_name in arguments and isinstance(
            arguments[operation_name], dict
        ):
            return arguments[operation_name]

        # If no nested structure is found, return the original arguments
        return arguments


class SchemaParameterTransformer:
    """Parameter transformer for schema-based operations.

    This transformer validates and transforms parameters using a Pydantic schema.
    It can handle both flat and nested parameter structures.

    Example with flat parameters:
        Input: {"name": "John", "age": 30}
        Output: {"person": Person(name="John", age=30)}

    Example with nested parameters:
        Input: {"person": {"name": "John", "age": 30}}
        Output: {"person": Person(name="John", age=30)}
    """

    def __init__(self, schema_class: Type[BaseModel], param_name: str = None):
        """Initialize the transformer.

        Args:
            schema_class: The Pydantic schema class
            param_name: Optional parameter name, defaults to the schema class name in lowercase
        """
        self.schema_class = schema_class
        self.param_name = param_name or schema_class.__name__.lower()

    async def transform(
        self,
        operation_name: str,
        arguments: Dict[str, Any],
        context: types.TextContent | None = None,
    ) -> Dict[str, Any]:
        """Transform parameters using the schema.

        This method handles both flat arguments and nested arguments.

        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context

        Returns:
            Transformed arguments with validated schema instance
        """
        # Get the schema fields
        schema_fields = (
            self.schema_class.model_fields.keys()
            if hasattr(self.schema_class, "model_fields")
            else self.schema_class.__annotations__.keys()
        )

        # Check if we have a nested structure with the param_name
        if self.param_name in arguments and isinstance(
            arguments[self.param_name], dict
        ):
            # Extract the nested parameters
            schema_kwargs = arguments[self.param_name]

            # Create a new arguments dict without the nested structure
            new_args = {
                k: v for k, v in arguments.items() if k != self.param_name
            }

            # Validate and add the schema instance
            new_args[self.param_name] = self.schema_class(**schema_kwargs)

            return new_args

        # Check if we have flat parameters matching the schema fields
        schema_kwargs = {}
        other_kwargs = {}

        # Separate schema parameters from other kwargs
        for key, value in arguments.items():
            if key in schema_fields:
                schema_kwargs[key] = value
            else:
                other_kwargs[key] = value

        # If we have schema parameters, validate and create the schema instance
        if schema_kwargs:
            validated_input = self.schema_class(**schema_kwargs)

            # Replace the original kwargs with the validated input and other kwargs
            other_kwargs[self.param_name] = validated_input

            return other_kwargs

        # If no schema parameters are found, return the original arguments
        return arguments


class CompositeParameterTransformer:
    """Parameter transformer that combines multiple transformers.

    This transformer tries each transformer in sequence until one successfully
    transforms the parameters.

    Example:
        A composite transformer with SchemaParameterTransformer and NestedParameterTransformer
        will first try to validate using the schema, and if that fails, it will try
        to extract from a nested structure.
    """

    def __init__(self, transformers: list[ParameterTransformer]):
        """Initialize the transformer.

        Args:
            transformers: List of transformers to try in sequence
        """
        self.transformers = transformers

    async def transform(
        self,
        operation_name: str,
        arguments: Dict[str, Any],
        context: types.TextContent | None = None,
    ) -> Dict[str, Any]:
        """Transform parameters by trying each transformer in sequence.

        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context

        Returns:
            Transformed arguments from the first successful transformer
        """
        # Try each transformer in sequence
        for transformer in self.transformers:
            try:
                transformed = await transformer.transform(
                    operation_name, arguments, context
                )
                # If the transformer changed the arguments, return the result
                if transformed != arguments:
                    return transformed
            except Exception:
                # If the transformer raised an exception, try the next one
                continue

        # If all transformers failed, return the original arguments
        return arguments
