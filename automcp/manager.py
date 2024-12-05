"""Core service group and manager implementation."""

import asyncio
import inspect

import mcp.types as types

from .group import ServiceGroup
from .types import ServiceRequest, ServiceResponse

DEFAULT_TIMEOUT = 60  # seconds


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
