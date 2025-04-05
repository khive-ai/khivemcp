"""Tests for timeout handling in AutoMCP operations."""

import asyncio
import time

import pytest
from mcp.types import TextContent

from automcp.server import AutoMCPServer
from automcp.types import ExecutionRequest, GroupConfig, ServiceRequest
from verification.groups.timeout_group import TimeoutGroup


class MockContext(TextContent):
    """Mock context for testing operations with progress reporting."""

    def __init__(self):
        super().__init__(type="text", text="")
        self.progress_updates = []
        self.info_messages = []

    def info(self, message):
        """Record an info message."""
        self.info_messages.append(message)

    async def report_progress(self, current, total):
        """Record a progress update."""
        self.progress_updates.append((current, total))


@pytest.mark.asyncio
async def test_operation_completes_before_timeout():
    """Test that operations complete successfully when they finish before the timeout."""
    # Create a server with a 1-second timeout
    config = GroupConfig(name="timeout", description="Timeout group")
    server = AutoMCPServer("test-server", config, timeout=1.0)
    server.groups["timeout"] = TimeoutGroup()

    # Test sleep operation with duration less than timeout
    request = ServiceRequest(
        requests=[ExecutionRequest(operation="sleep", arguments={"seconds": 0.2})]
    )

    start_time = time.time()
    result = await server._handle_service_request("timeout", request)
    elapsed = time.time() - start_time

    assert "Slept for 0.2 seconds" in result.content.text
    assert 0.2 <= elapsed < 1.0  # Should complete in less than the timeout


@pytest.mark.asyncio
async def test_operation_exceeds_timeout():
    """Test that operations are interrupted when they exceed the timeout."""
    # Create a server with a very short timeout
    config = GroupConfig(name="timeout", description="Timeout group")
    server = AutoMCPServer("test-server", config, timeout=0.2)
    server.groups["timeout"] = TimeoutGroup()

    # Test sleep operation with duration greater than timeout
    request = ServiceRequest(
        requests=[ExecutionRequest(operation="sleep", arguments={"seconds": 1.0})]
    )

    start_time = time.time()
    result = await server._handle_service_request("timeout", request)
    elapsed = time.time() - start_time

    # The operation should be interrupted by the timeout
    assert elapsed < 0.5  # Should return much faster than the requested sleep time
    # Check for timeout in errors list
    assert result.errors and "timeout" in str(result.errors).lower()


@pytest.mark.asyncio
async def test_progress_reporting_with_timeout():
    """Test progress reporting in operations with timeout."""
    # Create a server with a timeout that allows the operation to complete
    config = GroupConfig(name="timeout", description="Timeout group")
    server = AutoMCPServer("test-server", config, timeout=1.0)
    server.groups["timeout"] = TimeoutGroup()

    # Create a mock context to capture progress updates
    ctx = MockContext()

    # Call the slow_counter operation directly
    timeout_group = server.groups["timeout"]
    result = await timeout_group.slow_counter(3, 0.1, ctx)

    # Verify progress was reported
    assert len(ctx.progress_updates) == 3
    assert ctx.progress_updates[0] == (1, 3)
    assert ctx.progress_updates[1] == (2, 3)
    assert ctx.progress_updates[2] == (3, 3)

    # Verify info messages were logged
    assert len(ctx.info_messages) == 3
    assert "Counter: 1/3" in ctx.info_messages[0]
    assert "Counter: 2/3" in ctx.info_messages[1]
    assert "Counter: 3/3" in ctx.info_messages[2]


@pytest.mark.asyncio
async def test_cpu_intensive_operation_timeout():
    """Test timeout handling for CPU-intensive operations."""
    # Create a server with a very short timeout
    config = GroupConfig(name="timeout", description="Timeout group")
    server = AutoMCPServer("test-server", config, timeout=0.1)
    server.groups["timeout"] = TimeoutGroup()

    # Test cpu_intensive operation with a large iteration count
    request = ServiceRequest(
        requests=[
            ExecutionRequest(
                operation="cpu_intensive", arguments={"iterations": 100000}
            )
        ]
    )

    start_time = time.time()
    result = await server._handle_service_request("timeout", request)
    elapsed = time.time() - start_time

    # The operation should be interrupted by the timeout
    # Note: CPU-intensive operations may not respond to timeouts immediately
    # since they don't yield control to the event loop frequently
    assert elapsed < 5.0  # Should still be faster than the full computation
    # Check for timeout in errors list
    assert result.errors and "timeout" in str(result.errors).lower()


@pytest.mark.asyncio
async def test_concurrent_operations_with_timeout():
    """Test handling of concurrent operations with timeout."""
    # Create a server with a moderate timeout
    config = GroupConfig(name="timeout", description="Timeout group")
    server = AutoMCPServer("test-server", config, timeout=0.5)
    server.groups["timeout"] = TimeoutGroup()

    # Create multiple requests to run concurrently
    requests = [
        ServiceRequest(
            requests=[ExecutionRequest(operation="sleep", arguments={"seconds": 0.1})]
        ),
        ServiceRequest(
            requests=[ExecutionRequest(operation="sleep", arguments={"seconds": 0.2})]
        ),
        ServiceRequest(
            requests=[ExecutionRequest(operation="sleep", arguments={"seconds": 0.3})]
        ),
    ]

    # Run all requests concurrently
    start_time = time.time()
    results = await asyncio.gather(
        *[server._handle_service_request("timeout", request) for request in requests]
    )
    elapsed = time.time() - start_time

    # All operations should complete successfully
    assert "Slept for 0.1 seconds" in results[0].content.text
    assert "Slept for 0.2 seconds" in results[1].content.text
    assert "Slept for 0.3 seconds" in results[2].content.text

    # The total time should be close to the longest operation (0.3s)
    # rather than the sum of all operations (0.6s)
    assert 0.3 <= elapsed < 0.5
