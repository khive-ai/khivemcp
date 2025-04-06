"""Core service group and manager implementation."""

import mcp.types as types

from .types import ExecutionRequest, ExecutionResponse


class MockContext(types.TextContent):
    """Mock context for testing operations with progress reporting."""

    def __init__(self):
        super().__init__(type="text", text="")
        self.progress_updates = []
        self.info_messages = []

    def info(self, message):
        """Record an info message."""
        self.info_messages.append(message)

    async def report_progress(self, current, total):
        """Record a progress update."""
        self.progress_updates.append((current, total))


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
            # Create a context for progress reporting and logging
            ctx = MockContext()

            # Call the operation directly with the arguments and context
            args = request.arguments or {}

            # Check if the operation expects a ctx parameter
            import inspect

            sig = inspect.signature(operation)
            if "ctx" in sig.parameters:
                args["ctx"] = ctx

            # Add debug print statements to trace execution
            print(f"DEBUG: Calling operation {request.operation} with args: {args}")
            try:
                result = await operation(**args)
                print(f"DEBUG: Operation {request.operation} succeeded with result: {result}")
                return ExecutionResponse(
                    content=types.TextContent(type="text", text=str(result)), error=None
                )
            except Exception as e:
                print(f"DEBUG: Operation {request.operation} failed with error: {e}")
                import traceback
                traceback.print_exc()
                raise
        except Exception as e:
            return ExecutionResponse(
                content=types.TextContent(type="text", text=str(e)), error=str(e)
            )

    # Add public execute method that the server can call
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Public method to execute an operation."""
        return await self._execute(request)
