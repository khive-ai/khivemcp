"""Test configuration and fixtures for verification package."""

import contextlib
from typing import Any, AsyncGenerator, Callable, Tuple

import pytest

from automcp.server import AutoMCPServer
from automcp.testing.context import MockContext


class MockClient:
    """Mock MCP client for testing."""

    def __init__(self, server: AutoMCPServer):
        """Initialize the mock client with a server reference."""
        self.server = server
        self.timeout = 5.0
        self._progress_callback = None

    async def call(self, operation: str, *args, **kwargs) -> Any:
        """Call an operation on the server."""
        # Parse group and operation
        group_name, op_name = operation.split(".", 1)

        # Get the group
        group = self.server.groups.get(group_name)
        if not group:
            raise AttributeError(f"Group not found: {group_name}")

        # Get the operation
        op = getattr(group, op_name, None)
        if not op:
            raise AttributeError(f"Operation not found: {op_name}")

        # Call the operation
        if args and kwargs:
            return await op(*args, **kwargs)
        elif args:
            return await op(*args)
        else:
            return await op(**kwargs)

    def set_progress_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        """Set the progress callback."""
        self._progress_callback = callback


@contextlib.asynccontextmanager
async def create_connected_server_and_client_session() -> (
    AsyncGenerator[Tuple[AutoMCPServer, MockClient], None]
):
    """Create a connected server and client session for testing."""
    server = AutoMCPServer("test-server", None)
    client = MockClient(server)
    try:
        yield server, client
    finally:
        pass  # No cleanup needed for mock implementation


@pytest.fixture
def mock_context():
    """Provide a mock context for testing."""
    return MockContext()
