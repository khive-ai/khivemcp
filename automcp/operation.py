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
                validated_input = schema(**kwargs)
                return await func(self, validated_input)
            return await func(self, *args, **kwargs)

        wrapper.is_operation = True
        wrapper.op_name = name or func.__name__
        wrapper.schema = schema
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        return wrapper

    return decorator
