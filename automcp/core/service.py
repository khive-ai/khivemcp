"""Core service implementation."""

import asyncio
from functools import wraps
from typing import Any, ClassVar, Dict, Optional, Type

from pydantic import BaseModel, create_model

from automcp.core.errors import OperationError, ValidationError
from automcp.schemas.base import ExecutionResponse, TextContent


def operation(
    schema: Optional[Type[BaseModel]] = None,
    name: Optional[str] = None,
    policy: Optional[str] = None,
):
    """Decorator for service operations."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                if schema:
                    # Validate input
                    validated_input = schema(**kwargs)
                    result = await func(self, validated_input)
                else:
                    result = await func(self, *args, **kwargs)

                # Ensure result is ExecutionResponse
                if not isinstance(result, ExecutionResponse):
                    result = ExecutionResponse(
                        content=TextContent(type="text", text=str(result))
                    )
                return result
            except Exception as e:
                raise OperationError(
                    str(e),
                    {
                        "operation": func.__name__,
                        "args": args,
                        "kwargs": kwargs,
                        "schema": schema.__name__ if schema else None,
                    },
                )

        # Attach metadata
        wrapper.is_operation = True
        wrapper.op_name = name or func.__name__
        wrapper.schema = schema
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        return wrapper

    return decorator


class ServiceGroup:
    """Base class for all service groups."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize service group."""
        self.config = config or {}
        self._operations = {}
        self._lock = asyncio.Lock()
        self._contexts = set()
        self._init_operations()

    def _init_operations(self) -> None:
        """Initialize operations from class methods."""
        for name in dir(self):
            if name.startswith("_"):
                continue

            attr = getattr(self, name)
            if hasattr(attr, "is_operation"):
                self._operations[attr.op_name] = attr

    async def execute(
        self,
        operation: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResponse:
        """Execute an operation."""
        if operation not in self._operations:
            raise OperationError(f"Unknown operation: {operation}")

        try:
            async with self._lock:
                return await self._operations[operation](self, **(arguments or {}))
        except Exception as e:
            if isinstance(e, OperationError):
                raise
            raise OperationError(
                str(e), {"operation": operation, "arguments": arguments}
            )

    async def _execute_with_context(
        self,
        operation: str,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResponse:
        """Execute operation with context."""
        context = context or {}
        try:
            async with self._operation_context(operation, context) as ctx:
                return await self.execute(operation, arguments)
        except Exception as e:
            if isinstance(e, OperationError):
                raise
            raise OperationError(
                str(e),
                {"operation": operation, "arguments": arguments, "context": context},
            )

    async def _operation_context(self, operation: str, context: Dict[str, Any]):
        """Context manager for operation execution."""

        class OperationContext:
            def __init__(self, group: "ServiceGroup", op: str, ctx: Dict[str, Any]):
                self.group = group
                self.operation = op
                self.context = ctx
                self.start_time = None
                self._task = None

            async def __aenter__(self):
                self.start_time = asyncio.get_event_loop().time()
                self._task = asyncio.current_task()
                self.group._contexts.add(self)
                return self

            async def __aexit__(self, exc_type, exc, tb):
                try:
                    duration = asyncio.get_event_loop().time() - self.start_time
                    self.context["duration"] = duration
                finally:
                    self.group._contexts.remove(self)
                    self._task = None

        return OperationContext(self, operation, context)

    async def cleanup(self):
        """Clean up group resources."""
        # Cancel any running operations
        for ctx in list(self._contexts):
            if ctx._task and not ctx._task.done():
                ctx._task.cancel()
                try:
                    await ctx._task
                except asyncio.CancelledError:
                    pass

        # Clear contexts
        self._contexts.clear()
