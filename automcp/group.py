"""Core service group and manager implementation."""

import mcp.types as types

from .types import ExecutionRequest, ExecutionResponse


class ServiceGroup:
    """Service group containing operations."""

    def __init__(self):
        """Initialize the service group and register operations."""
        self.registry = {}

        # Register operations
        for name in dir(self):
            method = getattr(self, name)
            if hasattr(method, "is_operation") and method.is_operation:
                self.registry[method.op_name] = method

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
            # Call the operation directly with the arguments
            result = await operation(**(request.arguments or {}))
            return ExecutionResponse(
                content=types.TextContent(type="text", text=str(result)), error=None
            )
        except Exception as e:
            return ExecutionResponse(
                content=types.TextContent(type="text", text=str(e)), error=str(e)
            )

    # Add public execute method that the server can call
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Public method to execute an operation."""
        return await self._execute(request)
