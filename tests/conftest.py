"""Test configuration and fixtures."""

import asyncio
from typing import Any, AsyncGenerator, Callable, Dict

import pytest

from automcp import AutoMCPServer, ServiceGroup
from automcp.schemas.base import GroupConfig, ServiceConfig


@pytest.fixture
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean up any pending tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
    loop.close()


@pytest.fixture
async def service_group() -> AsyncGenerator[ServiceGroup, None]:
    """Create a service group with cleanup."""
    group = ServiceGroup()
    yield group
    await group.cleanup()


@pytest.fixture
async def server() -> (
    AsyncGenerator[Callable[[ServiceConfig | GroupConfig], AutoMCPServer], None]
):
    """Create a server factory with cleanup."""
    servers = []

    async def create_server(config: ServiceConfig | GroupConfig) -> AutoMCPServer:
        server = AutoMCPServer(name="test", config=config)
        servers.append(server)
        return server

    yield create_server

    # Cleanup all servers
    for server in servers:
        for group in server.groups.values():
            if hasattr(group, "cleanup") and callable(group.cleanup):
                await group.cleanup()


@pytest.fixture
async def test_config() -> ServiceConfig:
    """Create a test service configuration."""
    return ServiceConfig(
        name="test-service",
        description="Test service",
        groups={
            "tests.test_server:TestOperation": GroupConfig(
                name="test-group", description="Test group"
            )
        },
    )


@pytest.fixture
async def test_group_config() -> GroupConfig:
    """Create a test group configuration."""
    return GroupConfig(name="test-group", description="Test group")


@pytest.fixture(autouse=True)
async def cleanup_tasks():
    """Cleanup any remaining tasks after each test."""
    yield
    # Cancel any pending tasks
    loop = asyncio.get_event_loop()
    pending = asyncio.all_tasks(loop)
    for task in pending:
        if not task.done() and task != asyncio.current_task():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
