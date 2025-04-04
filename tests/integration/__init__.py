"""Integration tests package."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional

import anyio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams
from mcp.types import JSONRPCMessage

from automcp.group import ServiceGroup
from automcp.server import AutoMCPServer


@asynccontextmanager
async def create_connected_server_and_client_session(
    server_factory: Callable[[], AutoMCPServer],
    server_groups: Dict[str, ServiceGroup],
    read_timeout_seconds: Optional[float] = None,
    raise_exceptions: bool = False,
):
    """
    Creates a connected AutoMCPServer and ClientSession for testing.

    Args:
        server_factory: A factory function that creates an AutoMCPServer instance
        server_groups: Dictionary mapping group names to ServiceGroup instances
        read_timeout_seconds: Optional timeout for client read operations
        raise_exceptions: Whether to raise exceptions in the server

    Yields:
        A tuple of (server, client_session)
    """
    # Create the server instance
    server = server_factory()

    # Register all service groups
    for group_name, group_instance in server_groups.items():
        server.register_service_group(group_name, group_instance)

    # Create memory streams for client-server communication
    async with create_client_server_memory_streams() as (
        client_streams,
        server_streams,
    ):
        client_read, client_write = client_streams
        server_read, server_write = server_streams

        # Create a task group for the server
        async with anyio.create_task_group() as tg:
            # Start the server
            tg.start_soon(
                lambda: server.run_with_streams(
                    server_read, server_write, raise_exceptions=raise_exceptions
                )
            )

            # Create and initialize the client session
            timeout = (
                None
                if read_timeout_seconds is None
                else anyio.to_timedelta(read_timeout_seconds)
            )
            client_session = ClientSession(
                read_stream=client_read,
                write_stream=client_write,
                read_timeout_seconds=timeout,
            )

            async with client_session:
                await client_session.initialize()
                try:
                    # Yield both the server and client session
                    yield server, client_session
                finally:
                    # Cancel the server task when we're done
                    tg.cancel_scope.cancel()
