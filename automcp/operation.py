"""Core service group and manager implementation."""

from functools import wraps

from pydantic import BaseModel


def operation(
    schema: type[BaseModel] | None = None,
    name: str | None = None,
    policy: str | None = None,
):
    """Decorator for service operations."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if schema:
                # Extract schema parameters from kwargs
                schema_params = {}
                other_args = []
                other_kwargs = {}
                
                # Handle direct MCP tool invocation case
                if len(args) == 1 and not kwargs and isinstance(args[0], dict):
                    # Direct call with a dictionary argument
                    return await func(schema(**args[0]), **other_kwargs)
                
                # Handle case where kwargs contain all schema fields
                # This happens when called through ServiceGroup.execute
                schema_field_names = set(schema.__annotations__.keys())
                if set(kwargs.keys()).issuperset(schema_field_names):
                    # Create a dictionary of just the schema parameters
                    input_dict = {}
                    for key in schema_field_names:
                        if key in kwargs:
                            input_dict[key] = kwargs.pop(key)
                    
                    # Create validated schema object
                    validated_input = schema(**input_dict)
                    return await func(self, validated_input, *args, **kwargs)
                
                # Normal case - extract parameters from kwargs
                for key, value in kwargs.items():
                    if key in schema.__annotations__:
                        schema_params[key] = value
                    else:
                        other_kwargs[key] = value
                
                validated_input = schema(**schema_params)
                return await func(
                    validated_input, *args, *other_args, **other_kwargs
                )
            return await func(*args, **kwargs)

        wrapper.is_operation = True
        wrapper.op_name = name or func.__name__
        wrapper.schema = schema
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        return wrapper

    return decorator
