"""Core service group and manager implementation."""

import asyncio
import inspect
from functools import wraps
from typing import Any, ClassVar, Dict, Optional, Type

import mcp.types as types
from pydantic import BaseModel

from .types import ExecutionRequest, ExecutionResponse, ServiceRequest, ServiceResponse

DEFAULT_TIMEOUT = 60  # seconds


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


class ServiceGroup:
    """Service group containing operations."""

    registry: ClassVar[dict[str, Any]] = {}

    @property
    def _is_empty(self) -> bool:
        """Check if group has any registered operations."""
        return not bool(self.registry)

    async def _execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute an operation."""
        operation = self.registry.get(request.operation)
        if not operation:
            return ExecutionResponse(
                content=types.TextContent(
                    type="text", text=f"Unknown operation: {request.operation}"
                ),
                error=f"Unknown operation: {request.operation}",
            )

        try:
            return await operation(self, **(request.arguments or {}))
        except Exception as e:
            return ExecutionResponse(
                content=types.TextContent(type="text", text=str(e)), error=str(e)
            )


class ServiceManager:
    """Manager for service operations."""

    def __init__(self, group: ServiceGroup, timeout: float = DEFAULT_TIMEOUT):
        """Initialize service manager."""
        self.group = group
        self.timeout = timeout
        self._init_group()

    def _init_group(self) -> None:
        """Initialize group registry."""
        self.group.registry.clear()

        for name, method in inspect.getmembers(self.group):
            if (
                inspect.ismethod(method)
                and hasattr(method, "is_operation")
                and not name.startswith("_")
            ):
                self.group.registry[method.op_name] = method

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute service request with timeout."""
        try:
            responses = await asyncio.gather(
                *[self.group._execute(req) for req in request.requests],
                return_exceptions=True,
            )

            errors = []
            results = []

            for resp in responses:
                if isinstance(resp, Exception):
                    errors.append(str(resp))
                elif resp.error:
                    errors.append(resp.error)
                    results.append(resp.content.text)
                else:
                    results.append(resp.content.text)

            return ServiceResponse(
                content=types.TextContent(type="text", text="\n".join(results)),
                errors=errors if errors else None,
            )

        except asyncio.TimeoutError:
            return ServiceResponse(
                content=types.TextContent(type="text", text="Operation timed out"),
                errors=["Execution timeout"],
            )
