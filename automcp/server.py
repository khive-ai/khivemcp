"""
AutoMCP server implementation.

This module provides the core server implementation for AutoMCP, handling
MCP protocol integration, request routing, and operation execution.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.models import InitializationOptions

from .exceptions import OperationTimeoutError
from .group import ServiceGroup
from .types import (
    ExecutionRequest,
    ExecutionResponse,
    GroupConfig,
    ServiceConfig,
    ServiceRequest,
    ServiceResponse,
)


class AutoMCPServer:
    """MCP server implementation supporting both service and group configurations.

    This class provides a unified interface for creating and running MCP servers
    based on either a single ServiceGroup configuration or a multi-group service
    configuration. It handles the MCP protocol, request routing, concurrent execution,
    and timeout management.
    """

    def __init__(
        self,
        name: str,
        config: Union[ServiceConfig, GroupConfig],
        timeout: float = 30.0,
    ):
        """Initialize MCP server.

        Args:
            name: Server name used for MCP protocol identification
            config: Service or group configuration that defines the available operations
            timeout: Operation timeout in seconds for all operations

        Raises:
            TypeError: If config is not a ServiceConfig or GroupConfig
        """
        self.name = name
        self.raw_config = config  # Store raw config for potential reference
        self.timeout = timeout

        # Initialize FastMCP server with appropriate parameters
        instructions = (
            config.description
            if hasattr(config, "description") and config.description
            else ""
        )
        dependencies = []
        if hasattr(config, "packages"):
            dependencies = config.packages

        self.server = FastMCP(
            name=name,
            instructions=instructions,
            dependencies=dependencies,
            lifespan=None,
        )

        self.groups: Dict[str, ServiceGroup] = {}

        # Initialize groups based on config type
        if isinstance(config, ServiceConfig):
            self._init_service_groups(config)
        elif isinstance(config, GroupConfig):
            self._init_single_group(config)
        else:
            raise TypeError(
                "Configuration must be ServiceConfig or GroupConfig"
            )

        self._setup_handlers()

    def _init_service_groups(self, service_config: ServiceConfig) -> None:
        """Initialize multiple service groups from a service configuration.

        This method dynamically imports and instantiates ServiceGroup classes
        based on the class paths specified in the service configuration.

        Args:
            service_config: The service configuration containing group definitions

        Raises:
            RuntimeError: If a group fails to initialize
        """
        for class_path, group_config in service_config.groups.items():
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
                raise RuntimeError(
                    f"Failed to initialize group {class_path}: {e}"
                )

    def _init_single_group(self, group_config: GroupConfig) -> None:
        """Initialize a single service group from a group configuration.

        This method creates a basic ServiceGroup instance and configures it
        with the provided group configuration.

        Args:
            group_config: The configuration for the single group
        """
        group = ServiceGroup()
        group.config = group_config
        self.groups[group_config.name] = group

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers.

        This method registers all operations from all groups as tools with the FastMCP server.
        """
        # Register all operations from all groups as tools
        for group_name, group in self.groups.items():
            for op_name, operation in group.registry.items():
                tool_name = f"{group_name}.{op_name}"

                # Extract schema if available
                input_schema = {}
                if operation.schema:
                    try:
                        schema_dict = operation.schema.model_json_schema()
                        if isinstance(schema_dict, dict):
                            input_schema = schema_dict
                    except Exception as e:
                        logging.error(
                            f"Failed to extract schema for {tool_name}: {e}"
                        )

                # Register the tool with FastMCP
                # Create the handler function first
                handler = self._create_tool_handler(group_name, op_name)

                # Pass the handler as the first argument (fn) and other parameters as kwargs
                self.server.add_tool(
                    handler,
                    name=tool_name,
                    description=operation.doc
                    or f"Operation {op_name} in group {group_name}",
                )

    def _create_tool_handler(self, group_name: str, op_name: str):
        """Create a handler function for a specific tool.

        Args:
            group_name: The name of the group containing the operation
            op_name: The name of the operation

        Returns:
            A handler function that can be registered with FastMCP
        """

        async def handler(arguments: dict | None = None) -> types.TextContent:
            try:
                # Create execution request
                request = ServiceRequest(
                    requests=[
                        ExecutionRequest(
                            operation=op_name, arguments=arguments
                        )
                    ]
                )

                # Execute request
                response = await self._handle_service_request(
                    group_name, request
                )
                return response.content

            except Exception as e:
                error_msg = f"Error executing {group_name}.{op_name}: {str(e)}"
                logging.exception(error_msg)
                return types.TextContent(type="text", text=error_msg)

        return handler

    async def _handle_service_request(
        self, group_name: str, request: ServiceRequest
    ) -> ServiceResponse:
        """Handle service request for specific group.

        This method processes a service request by executing all contained
        operation requests concurrently with timeout handling.

        Args:
            group_name: The name of the group to execute operations on
            request: The service request containing operation requests

        Returns:
            A ServiceResponse containing the results or error information
        """
        group = self.groups.get(group_name)
        if not group:
            error_msg = f"Group not found: {group_name}"
            return ServiceResponse(
                content=types.TextContent(type="text", text=error_msg),
                errors=[error_msg],
            )

        try:
            # Execute all requests concurrently with timeout
            tasks = [group.execute(req) for req in request.requests]

            try:
                responses = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                # Use the custom OperationTimeoutError
                operations = [req.operation for req in request.requests]
                error_msg = f"Operations {', '.join(operations)} in group {group_name} timed out after {self.timeout} seconds"
                logging.error(error_msg)
                raise OperationTimeoutError(error_msg)

            # Process responses
            errors = []
            results = []

            for resp in responses:
                if isinstance(resp, Exception):
                    error_msg = f"Operation error: {str(resp)}"
                    errors.append(error_msg)
                    logging.error(f"Operation execution failed: {error_msg}")
                elif resp.error:
                    errors.append(resp.error)
                    results.append(resp.content.text)
                else:
                    results.append(resp.content.text)

            return ServiceResponse(
                content=types.TextContent(
                    type="text", text="\n".join(results)
                ),
                errors=errors if errors else None,
            )

        except OperationTimeoutError as e:
            return ServiceResponse(
                content=types.TextContent(
                    type="text", text=f"Operation timeout: {str(e)}"
                ),
                errors=[f"Execution timeout: {str(e)}"],
            )
        except Exception as e:
            error_msg = f"Error processing service request: {str(e)}"
            logging.exception(error_msg)
            return ServiceResponse(
                content=types.TextContent(type="text", text=error_msg),
                errors=[error_msg],
            )

    async def start(self) -> None:
        """Start the MCP server using stdio transport.

        This method initializes the MCP protocol over stdio and begins
        processing requests. It blocks until the server is stopped.
        """
        # Run the FastMCP server with stdio transport
        await self.server.run("stdio")

    async def __aenter__(self):
        """Async context manager entry.

        Returns:
            The server instance
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.

        Ensures the server is properly stopped when exiting a context manager block.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        await self.stop()

    async def stop(self):
        """Stop the server and clean up resources.

        This method handles graceful shutdown of the server and any associated
        resources. Currently a placeholder for future cleanup logic.
        """
        # Cleanup resources if needed
        logging.info(f"Stopping AutoMCPServer: {self.name}")
        pass

    def get_capabilities(
        self,
        notification_options: NotificationOptions,
        experimental_capabilities: dict = None,
    ):
        """Get server capabilities.

        This method provides access to the underlying server's capabilities.
        It's needed for compatibility with the MCP protocol.

        Args:
            notification_options: Options for notifications
            experimental_capabilities: Optional experimental capabilities

        Returns:
            Server capabilities
        """
        if experimental_capabilities is None:
            experimental_capabilities = {}

        # Access the underlying server's _mcp_server attribute which has the get_capabilities method
        return self.server._mcp_server.get_capabilities(
            notification_options=notification_options,
            experimental_capabilities=experimental_capabilities,
        )
