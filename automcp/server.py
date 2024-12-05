"""AutoMCP server implementation."""

import asyncio

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .group import ServiceGroup
from .types import (
    ExecutionRequest,
    GroupConfig,
    ServiceConfig,
    ServiceRequest,
    ServiceResponse,
)


class AutoMCPServer:
    """MCP server implementation supporting both service and group configurations."""

    def __init__(
        self,
        name: str,
        config: ServiceConfig | GroupConfig,
        timeout: float = 30.0,
    ):
        """Initialize MCP server.

        Args:
            name: Server name
            config: Service or group configuration
            timeout: Operation timeout in seconds
        """
        self.name = name
        self.config = config
        self.timeout = timeout
        self.server = Server(name)
        self.groups: dict[str, ServiceGroup] = {}

        # Initialize groups based on config type
        if isinstance(config, ServiceConfig):
            self._init_service_groups()
        else:
            self._init_single_group()

        self._setup_handlers()

    def _init_service_groups(self) -> None:
        """Initialize groups from service config."""
        assert isinstance(self.config, ServiceConfig)

        for class_path, group_config in self.config.groups.items():
            try:
                # Import group class from path (module:class)
                module_path, class_name = class_path.split(":")
                module = __import__(module_path, fromlist=[class_name])
                group_cls = getattr(module, class_name)

                # Initialize group with merged config
                group = group_cls()
                group.config = group_config

                self.groups[group_config.name] = group

            except Exception as e:
                raise RuntimeError(f"Failed to initialize group {class_path}: {e}")

    def _init_single_group(self) -> None:
        """Initialize single group from group config."""
        assert isinstance(self.config, GroupConfig)
        group = ServiceGroup()
        group.config = self.config
        self.groups[self.config.name] = group

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List all available tools across groups."""
            tools = []
            for group in self.groups.values():
                for op_name, operation in group.registry.items():
                    tools.append(
                        types.Tool(
                            name=f"{group.config.name}.{op_name}",
                            description=operation.doc,
                            inputSchema=(
                                operation.schema.model_json_schema()
                                if operation.schema
                                else None
                            ),
                        )
                    )
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None = None
        ) -> list[types.TextContent]:
            """Handle tool execution."""
            try:
                # Parse group and operation from tool name
                group_name, op_name = name.split(".", 1)

                # Create execution request
                request = ServiceRequest(
                    requests=[ExecutionRequest(operation=op_name, arguments=arguments)]
                )

                # Execute request
                response = await self._handle_service_request(group_name, request)
                return [response.content]

            except Exception as e:
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_service_request(
        self, group_name: str, request: ServiceRequest
    ) -> ServiceResponse:
        """Handle service request for specific group."""
        group = self.groups.get(group_name)
        if not group:
            return ServiceResponse(
                content=types.TextContent(
                    type="text", text=f"Group not found: {group_name}"
                ),
                errors=[f"Group not found: {group_name}"],
            )

        try:
            # Execute all requests concurrently with timeout
            tasks = [group.execute(req) for req in request.requests]

            responses = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=self.timeout
            )

            # Process responses
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
        except Exception as e:
            return ServiceResponse(
                content=types.TextContent(type="text", text=str(e)), errors=[str(e)]
            )

    async def start(self) -> None:
        """Start the MCP server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.name,
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
        # Cleanup if needed
        pass
