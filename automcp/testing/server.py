"""Test server for AutoMCP operations.

This module provides a standardized way to create and test AutoMCP servers
with automatic parameter handling and schema validation.
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncGenerator, Callable
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple, cast

import anyio
import mcp.types as types
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)
from mcp.client.session import ClientSession
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import JSONRPCMessage
from pydantic import BaseModel

from automcp.server import AutoMCPServer
from automcp.testing.transforms import ParameterTransformer

# Define a type for message streams
MessageStream = tuple[
    MemoryObjectReceiveStream[JSONRPCMessage | Exception],
    MemoryObjectSendStream[JSONRPCMessage],
]


@contextlib.asynccontextmanager
async def create_memory_streams() -> (
    AsyncGenerator[tuple[MessageStream, MessageStream], None]
):
    """Create a pair of bidirectional memory streams for client-server communication.

    Returns:
        A tuple of (client_streams, server_streams) where each is a tuple of
        (read_stream, write_stream)
    """
    # Create streams for both directions
    server_to_client_send, server_to_client_receive = (
        anyio.create_memory_object_stream[JSONRPCMessage | Exception](1)
    )
    client_to_server_send, client_to_server_receive = (
        anyio.create_memory_object_stream[JSONRPCMessage | Exception](1)
    )

    client_streams = (server_to_client_receive, client_to_server_send)
    server_streams = (client_to_server_receive, server_to_client_send)

    async with (
        server_to_client_receive,
        client_to_server_send,
        client_to_server_receive,
        server_to_client_send,
    ):
        yield client_streams, server_streams


class TestServer:
    """Test server for AutoMCP operations.

    This class provides a standardized way to create and test AutoMCP servers
    with automatic parameter handling and schema validation.
    """

    def __init__(
        self,
        server: AutoMCPServer,
        parameter_transformers: Dict[str, ParameterTransformer] = None,
    ):
        """Initialize the test server.

        Args:
            server: The AutoMCPServer instance to test
            parameter_transformers: Optional dictionary mapping operation names to
                parameter transformers for custom parameter handling
        """
        self.server = server
        self.parameter_transformers = parameter_transformers or {}

    def create_operation_handler(
        self,
        group_name: str,
        operation_name: str,
    ) -> Callable:
        """Create a handler function for an operation.

        Args:
            group_name: The name of the group containing the operation
            operation_name: The name of the operation

        Returns:
            A handler function that can be registered with FastMCP
        """
        # Get the group and operation
        group = self.server.groups.get(group_name)
        if not group:
            raise ValueError(f"Unknown group: {group_name}")

        operation = group.registry.get(operation_name)
        if not operation:
            raise ValueError(f"Unknown operation: {operation_name}")

        # Get the full operation name (group.operation)
        full_operation_name = f"{group_name}.{operation_name}"

        # Get the parameter transformer for this operation if available
        parameter_transformer = self.parameter_transformers.get(
            full_operation_name
        )

        async def handler(
            arguments: Dict[str, Any] | None = None,
            ctx: types.TextContent = None,
        ) -> types.TextContent:
            try:
                # Create a copy of the arguments to avoid modifying the original
                args = arguments.copy() if arguments else {}

                # Add context if needed
                if (
                    hasattr(operation, "requires_context")
                    and operation.requires_context
                ):
                    args["ctx"] = ctx

                # Execute the operation
                result = await operation(**args)

                # Convert result to TextContent
                response_text = ""
                if isinstance(result, BaseModel):
                    response_text = result.model_dump_json()
                elif isinstance(result, (dict, list)):
                    response_text = json.dumps(result)
                elif result is not None:
                    response_text = str(result)

                return types.TextContent(type="text", text=response_text)

            except Exception as e:
                error_msg = (
                    f"Error during '{operation_name}' execution: {str(e)}"
                )
                logging.exception(error_msg)
                return types.TextContent(type="text", text=error_msg)

        return handler

    def register_operations(self) -> None:
        """Register all operations from all groups as tools with the FastMCP server.

        This method ensures that all operations are properly registered with
        the appropriate parameter transformers.
        """
        for group_name, group in self.server.groups.items():
            for op_name, operation in group.registry.items():
                tool_name = f"{group_name}.{op_name}"

                # Create the handler function
                handler = self.create_operation_handler(group_name, op_name)

                # Register the tool with FastMCP
                description = (
                    operation.doc
                    or f"Operation {op_name} in group {group_name}"
                )

                try:
                    self.server.server.add_tool(
                        handler,
                        name=tool_name,
                        description=description,
                    )
                except Exception as e:
                    logging.warning(f"Error registering tool {tool_name}: {e}")

    @contextlib.asynccontextmanager
    async def create_client_session(
        self,
        read_timeout_seconds: timedelta | None = None,
    ) -> AsyncGenerator[ClientSession, None]:
        """Create a client session connected to this server.

        Args:
            read_timeout_seconds: Optional timeout for read operations

        Returns:
            A connected ClientSession
        """
        async with create_memory_streams() as (client_streams, server_streams):
            client_read, client_write = client_streams
            server_read, server_write = server_streams

            # Create a cancel scope for the server task
            async with anyio.create_task_group() as tg:
                # Register all operations with appropriate parameter transformers
                self.register_operations()

                # Start the server's internal MCP server
                async def run_server():
                    await self.server.server._mcp_server.run(
                        server_read,
                        server_write,
                        InitializationOptions(
                            server_name=self.server.name,
                            server_version="1.0.0",
                            capabilities=self.server.get_capabilities(
                                notification_options=NotificationOptions(),
                                experimental_capabilities={},
                            ),
                        ),
                    )

                tg.start_soon(run_server)

                try:
                    # Create and initialize the client session
                    async with ClientSession(
                        read_stream=client_read,
                        write_stream=client_write,
                        read_timeout_seconds=read_timeout_seconds,
                    ) as client_session:
                        await client_session.initialize()
                        yield client_session
                finally:
                    tg.cancel_scope.cancel()


@contextlib.asynccontextmanager
async def create_connected_server_and_client_session(
    server: AutoMCPServer,
    parameter_transformers: Dict[str, ParameterTransformer] = None,
    read_timeout_seconds: timedelta | None = None,
) -> AsyncGenerator[Tuple[TestServer, ClientSession], None]:
    """Create a TestServer and connected ClientSession.

    This function simplifies the process of creating a test server and
    connecting a client session to it for testing purposes.

    Args:
        server: The AutoMCPServer instance to test
        parameter_transformers: Optional dictionary mapping operation names to
            parameter transformers for custom parameter handling
        read_timeout_seconds: Optional timeout for read operations

    Returns:
        A tuple of (test_server, client_session)
    """
    test_server = TestServer(server, parameter_transformers)

    async with test_server.create_client_session(
        read_timeout_seconds
    ) as client_session:
        yield test_server, client_session
