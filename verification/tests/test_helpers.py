"""Helper functions for testing AutoMCP servers.

This module has been refactored to use the new testing infrastructure components.
Most of the previous functionality has been moved to automcp/testing/server.py.
This file now serves primarily as a compatibility layer for existing tests.

For new tests, please use the following components directly:
1. automcp.testing.server.TestServer - For simplified server testing
2. automcp.testing.transforms - For standardized parameter handling
3. automcp.schemas.registry.SchemaRegistry - For centralized schema management
"""

import contextlib
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Tuple

from mcp.client.session import ClientSession

from automcp.server import AutoMCPServer
from automcp.testing.server import TestServer, create_memory_streams

# Re-export memory streams for backward compatibility
create_client_server_memory_streams = create_memory_streams


@contextlib.asynccontextmanager
async def create_connected_automcp_server_and_client_session(
    server: AutoMCPServer,
    read_timeout_seconds: timedelta | None = None,
) -> AsyncGenerator[tuple[AutoMCPServer, ClientSession], None]:
    """Creates a ClientSession that is connected to a running AutoMCP server.

    DEPRECATED: Use automcp.testing.server.create_connected_server_and_client_session instead.

    This function maintains backward compatibility with existing tests.

    Args:
        server: The AutoMCPServer instance to connect to
        read_timeout_seconds: Optional timeout for read operations

    Returns:
        A tuple of (server, client_session)
    """
    # Create a TestServer
    test_server = TestServer(server)

    # Use the TestServer to create a client session
    async with test_server.create_client_session(
        read_timeout_seconds
    ) as client_session:
        yield server, client_session
