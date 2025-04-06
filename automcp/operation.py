"""Operation decorator for service groups."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from pydantic import BaseModel, ValidationError

# Define a type variable for the schema
SchemaType = TypeVar("SchemaType", bound=BaseModel)

# Try to import Context type, fallback to Any if not available
try:
    import mcp.types as types

    Context = types.TextContent
except (ImportError, AttributeError):
    from typing import Any

    Context = Any


def operation(
    schema: type[BaseModel] | None = None,
    name: str | None = None,
    policy: str | None = None,
) -> Callable:
    """Decorator for service operations.

    This decorator marks a method as an operation that can be executed by
    the ServiceGroup. It handles schema validation, context injection,
    and attaches metadata to the wrapped function.

    Args:
        schema: Optional Pydantic model class for input validation.
        name: Optional custom name for the operation. Defaults to the function name.
        policy: Optional policy string for access control.

    Returns:
        A decorator function that wraps the original operation method.

    Notes:
        Context Handling:
        - If a parameter is named 'ctx' or has a type annotation ending with 'Context',
          it will be detected as a context parameter.
        - Context can be provided either as a positional argument or as a keyword argument.
        - If context is not provided, a default None value will be injected.
        - The decorator intelligently detects if context is already provided positionally
          to prevent "multiple values for argument" errors.

    Example:
        ```python
        class MyServiceGroup(ServiceGroup):
            @operation(schema=MyInputSchema)
            async def my_operation(self, data: MyInputSchema, ctx: Context = None):
                # Operation implementation
                return result
        ```
    """

    def decorator(func: Callable) -> Callable:
        # Get the operation name (use provided name or function name)
        op_name = name or func.__name__

        # Analyze the function signature
        sig = inspect.signature(func)

        # Check if the function requires a context parameter
        requires_context = False
        ctx_param_name = None

        for param_name, param in sig.parameters.items():
            if param_name == "ctx" or str(param.annotation).endswith(
                "Context"
            ):
                requires_context = True
                ctx_param_name = param_name
                break

        # Find the schema parameter if schema is provided
        schema_param_name = None
        if schema:
            for param_name, param in sig.parameters.items():
                if param_name != "self" and param.annotation == schema:
                    schema_param_name = param_name
                    break

            if not schema_param_name:
                raise TypeError(
                    f"Operation '{op_name}' decorated with schema {schema.__name__} "
                    f"but no matching parameter annotation found."
                )

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get the number of positional arguments expected by the function (excluding self)
            func_params = list(sig.parameters.values())
            positional_params = [
                p
                for p in func_params
                if p.name != "self"
                and p.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            ]

            # Handle context parameter if required
            if requires_context:
                # Check if context is already provided as a positional argument
                has_positional_ctx = False

                # Check if we have enough positional args to include the context parameter
                ctx_param_index = None
                for i, param in enumerate(positional_params):
                    if param.name == ctx_param_name:
                        ctx_param_index = i
                        break

                # Only consider ctx as positionally provided if it's at the *exact* position
                if (
                    ctx_param_index is not None
                    and len(args) == ctx_param_index + 1
                ):
                    has_positional_ctx = True

                # Only add context to kwargs if it's not already provided in kwargs
                if ctx_param_name not in kwargs:
                    # If we have more positional args than expected but ctx is not explicitly
                    # at the right position, we should not inject a context
                    if not (
                        ctx_param_index is not None
                        and len(args) > ctx_param_index
                    ):
                        # Provide a default context if not provided
                        try:
                            # Try to import MockContext for testing
                            from .testing.context import MockContext

                            mock_ctx = MockContext()
                            kwargs[ctx_param_name] = mock_ctx
                        except ImportError:
                            # Fallback to None if MockContext is not available
                            kwargs[ctx_param_name] = None

            # Handle schema validation if provided
            if schema and schema_param_name:
                # Check if schema is already provided as a positional argument
                has_positional_schema = False
                schema_param_index = None

                for i, param in enumerate(positional_params):
                    if param.name == schema_param_name:
                        schema_param_index = i
                        break

                if (
                    schema_param_index is not None
                    and len(args) > schema_param_index
                ):
                    # Schema is provided as a positional argument
                    has_positional_schema = True
                    # Verify it's an instance of the schema class
                    if not isinstance(args[schema_param_index], schema):
                        raise TypeError(
                            f"Positional argument for '{schema_param_name}' must be an instance of {schema.__name__}"
                        )

                if not has_positional_schema:
                    # Extract schema parameters from kwargs
                    schema_kwargs = {}
                    other_kwargs = {}

                    # Get the schema fields
                    schema_fields = (
                        schema.model_fields.keys()
                        if hasattr(schema, "model_fields")
                        else schema.__annotations__.keys()
                    )

                    # Separate schema parameters from other kwargs
                    for key, value in kwargs.items():
                        if key in schema_fields:
                            schema_kwargs[key] = value
                        else:
                            other_kwargs[key] = value

                    try:
                        # Validate the input using the schema
                        validated_input = schema(**schema_kwargs)

                        # Replace the original kwargs with the validated input and other kwargs
                        kwargs = other_kwargs
                        kwargs[schema_param_name] = validated_input

                    except ValidationError as e:
                        # Re-raise validation errors to be caught by ServiceGroup.execute
                        raise e

            # Call the original function with the processed arguments
            return await func(self, *args, **kwargs)

        # Attach metadata to the wrapper
        wrapper.is_operation = True
        wrapper.op_name = op_name
        wrapper.schema = schema
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        wrapper.requires_context = requires_context

        return wrapper

    return decorator
