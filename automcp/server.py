"""MCP server implementation."""

import asyncio
from typing import Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .operation import ServiceGroup, ServiceManager
from .types import ExecutionRequest, ServiceRequest, ServiceResponse


class AutoMCPServer:
    """MCP server with unified operation handling."""

    def __init__(self, name: str, service_group: ServiceGroup, timeout: float = 30):
        """Initialize MCP server.

        Args:
            name: Server name
            service_group: Service group containing operations
            timeout: Operation timeout in seconds
        """
        self.server = Server(name)
        self.manager = ServiceManager(service_group, timeout)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name=op.op_name,
                    description=op.doc,
                    inputSchema=op.schema.model_json_schema() if op.schema else None,
                )
                for op in self.manager.group.registry.values()
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None = None
        ) -> list[types.TextContent]:
            """Handle tool execution."""
            request = ServiceRequest(
                requests=[ExecutionRequest(operation=name, arguments=arguments)]
            )

            response = await self.manager.execute(request)
            return [response.content]

    async def start(self) -> None:
        """Start the MCP server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.server.name,
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Any cleanup needed
        pass


'''
# Define operations
class MyServiceGroup(ServiceGroup):
    @operation(schema=EditSchema)
    async def edit_text(self, input: EditSchema) -> ExecutionResponse:
        """Edit text content."""
        # Implementation
        pass

# Create and run server
async def main():
    group = MyServiceGroup()
    async with AutoMCPServer("my-server", group) as server:
        await server.start()

if __name__ == "__main__":
    asyncio.run(main())
'''
