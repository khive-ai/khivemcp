"""Core service group and manager implementation."""

from typing import Any, ClassVar

import mcp.types as types

from .types import ExecutionRequest, ExecutionResponse


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
