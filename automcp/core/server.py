"""MCP server implementation."""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ResourcesCapability,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolsCapability,
)

from automcp.core.errors import ConfigurationError, OperationError
from automcp.core.service import ServiceGroup
from automcp.schemas.base import (
    ExecutionResponse,
    GroupConfig,
    ServiceConfig,
    ServiceRequest,
    ServiceResponse,
)


class AutoMCPServer:
    """AutoMCP server implementation."""

    def __init__(
        self,
        name: str,
        config: ServiceConfig | GroupConfig,
        timeout: float = 30.0,
    ):
        """Initialize server."""
        self.name = name
        self.config = config
        self.timeout = timeout
        self.server = Server(name)
        self.groups: Dict[str, ServiceGroup] = {}
        self._init_groups()

    def _init_groups(self) -> None:
        """Initialize service groups."""
        if isinstance(self.config, ServiceConfig):
            # Initialize multiple service groups
            for class_path, group_config in self.config.groups.items():
                try:
                    module_path, class_name = class_path.split(":")
                    module = __import__(module_path, fromlist=[class_name])
                    group_cls = getattr(module, class_name)
                    group = group_cls()
                    group.config = group_config.config
                    self.groups[group_config.name] = group
                except Exception as e:
                    raise ConfigurationError(
                        f"Failed to initialize group {class_path}: {str(e)}"
                    )
        else:
            # Initialize single group
            group = ServiceGroup()
            group.config = self.config.config
            self.groups[self.config.name] = group

    async def _handle_service_request(
        self,
        group_name: str,
        request: ServiceRequest,
    ) -> ServiceResponse:
        """Handle service request."""
        group = self.groups.get(group_name)
        if not group:
            return ServiceResponse(
                content=TextContent(type="text", text=f"Group not found: {group_name}"),
                errors=[f"Group not found: {group_name}"],
            )

        try:
            tasks = [
                group.execute(req.operation, req.arguments) for req in request.requests
            ]
            responses = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=self.timeout
            )

            # Process responses
            errors = []
            results = []
            for resp in responses:
                if isinstance(resp, Exception):
                    errors.append(str(resp))
                else:
                    results.append(resp)

            if errors:
                return ServiceResponse(
                    content=TextContent(type="text", text="\n".join(errors)),
                    errors=errors,
                )

            # Combine successful responses
            combined_text = "\n".join(r.content.text for r in results)
            return ServiceResponse(content=TextContent(type="text", text=combined_text))

        except asyncio.TimeoutError:
            return ServiceResponse(
                content=TextContent(
                    type="text", text=f"Operation timeout after {self.timeout}s"
                ),
                errors=[f"Operation timeout after {self.timeout}s"],
            )
        except Exception as e:
            return ServiceResponse(
                content=TextContent(type="text", text=str(e)), errors=[str(e)]
            )

    async def start(self) -> None:
        """Start the server."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            tools = []
            for group_name, group in self.groups.items():
                for op_name, operation in group._operations.items():
                    schema = (
                        operation.schema.model_json_schema()
                        if operation.schema
                        else None
                    )
                    tools.append(
                        Tool(
                            name=f"{group_name}.{op_name}",
                            description=operation.doc,
                            inputSchema=schema,
                        )
                    )
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any] | None = None
        ) -> List[TextContent]:
            """Handle tool call request."""
            try:
                group_name, op_name = name.split(".", 1)
                group = self.groups.get(group_name)
                if not group:
                    raise OperationError(f"Group not found: {group_name}")

                response = await group.execute(op_name, arguments)
                return [response.content]

            except Exception as e:
                if isinstance(e, OperationError):
                    raise
                raise OperationError(str(e), {"tool": name, "arguments": arguments})

        # Create initialization options
        options = self.server.create_initialization_options()

        # Run server with stdio
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream, options, raise_exceptions=True
                )
        except KeyboardInterrupt:
            print("\nServer stopped", file=sys.stderr)
        except Exception as e:
            print(f"Server error: {str(e)}", file=sys.stderr)
            raise
        finally:
            # Cleanup resources
            for group in self.groups.values():
                if hasattr(group, "cleanup") and callable(group.cleanup):
                    await group.cleanup()


async def serve(config: ServiceConfig | GroupConfig, timeout: float = 30.0) -> None:
    """Run the AutoMCP server."""
    # Initialize server
    server = Server("automcp")

    # Initialize groups
    groups: Dict[str, ServiceGroup] = {}
    if isinstance(config, ServiceConfig):
        # Initialize multiple service groups
        for class_path, group_config in config.groups.items():
            try:
                module_path, class_name = class_path.split(":")
                module = __import__(module_path, fromlist=[class_name])
                group_cls = getattr(module, class_name)
                group = group_cls()
                group.config = group_config.config
                groups[group_config.name] = group
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to initialize group {class_path}: {str(e)}"
                )
    else:
        # Initialize single group
        group = ServiceGroup()
        group.config = config.config
        groups[config.name] = group

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        """List available tools."""
        tools = []
        for group_name, group in groups.items():
            for op_name, operation in group._operations.items():
                schema = (
                    operation.schema.model_json_schema() if operation.schema else None
                )
                tools.append(
                    Tool(
                        name=f"{group_name}.{op_name}",
                        description=operation.doc,
                        inputSchema=schema,
                    )
                )
        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None = None
    ) -> List[TextContent]:
        """Handle tool call request."""
        try:
            group_name, op_name = name.split(".", 1)
            group = groups.get(group_name)
            if not group:
                raise OperationError(f"Group not found: {group_name}")

            response = await group.execute(op_name, arguments)
            return [response.content]

        except Exception as e:
            if isinstance(e, OperationError):
                raise
            raise OperationError(str(e), {"tool": name, "arguments": arguments})

    # Create initialization options
    options = server.create_initialization_options()

    # Run server with stdio
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {str(e)}", file=sys.stderr)
        raise
    finally:
        # Cleanup resources
        for group in groups.values():
            if hasattr(group, "cleanup") and callable(group.cleanup):
                await group.cleanup()
