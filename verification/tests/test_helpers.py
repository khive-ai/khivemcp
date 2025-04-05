"""Helper functions for testing AutoMCP servers."""

import asyncio
import contextlib
from datetime import timedelta
from typing import Any, AsyncGenerator, Optional, Tuple

import anyio
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)
from mcp.client.session import ClientSession
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import JSONRPCMessage

from automcp.server import AutoMCPServer

# Define a type for message streams
MessageStream = Tuple[
    MemoryObjectReceiveStream[JSONRPCMessage | Exception],
    MemoryObjectSendStream[JSONRPCMessage],
]


@contextlib.asynccontextmanager
async def create_client_server_memory_streams() -> (
    AsyncGenerator[Tuple[MessageStream, MessageStream], None]
):
    """
    Creates a pair of bidirectional memory streams for client-server communication.

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


@contextlib.asynccontextmanager
async def create_connected_automcp_server_and_client_session(
    server: AutoMCPServer,
    read_timeout_seconds: Optional[timedelta] = None,
) -> AsyncGenerator[Tuple[AutoMCPServer, ClientSession], None]:
    """
    Creates a ClientSession that is connected to a running AutoMCP server.

    Args:
        server: The AutoMCPServer instance to connect to
        read_timeout_seconds: Optional timeout for read operations

    Returns:
        A tuple of (server, client_session)
    """
    async with create_client_server_memory_streams() as (
        client_streams,
        server_streams,
    ):
        client_read, client_write = client_streams
        server_read, server_write = server_streams

        # Create a cancel scope for the server task
        async with anyio.create_task_group() as tg:
            # Start the server's internal MCP server
            # The FastMCP.run method only takes 1 or 2 arguments (transport type or transport object)
            # We need to use a different approach to run the server with the memory streams

            # Create a task to run the server
            async def run_server():
                # Use the _mcp_server attribute which has the run method that accepts the streams
                await server.server._mcp_server.run(
                    server_read,
                    server_write,
                    InitializationOptions(
                        server_name=server.name,
                        server_version="1.0.0",
                        capabilities=server.get_capabilities(
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
                    yield server, client_session
            finally:
                tg.cancel_scope.cancel()
