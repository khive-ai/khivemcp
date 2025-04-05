"""Tests for the TimeoutGroup service group."""

import asyncio

import pytest
from mcp.types import TextContent

from verification.groups.timeout_group import TimeoutGroup


@pytest.mark.asyncio
async def test_sleep_direct():
    """Test sleep operation directly."""
    group = TimeoutGroup()
    start_time = asyncio.get_event_loop().time()
    result = await group.sleep(0.1)  # Short sleep for testing
    elapsed = asyncio.get_event_loop().time() - start_time

    assert "Slept for 0.1 seconds" in result
    assert 0.1 <= elapsed <= 0.2  # Allow small timing variance


@pytest.mark.asyncio
async def test_slow_counter_direct():
    """Test slow_counter operation directly."""
    group = TimeoutGroup()

    # Create a TextContent object to use as Context
    ctx = TextContent(type="text", text="")

    # Add the required methods for testing
    async def report_progress(current, total):
        pass

    def info(message):
        pass

    ctx.report_progress = report_progress
    ctx.info = info

    result = await group.slow_counter(3, 0.1, ctx)
    assert "Counted to 3" in result
    assert "1, 2, 3" in result


@pytest.mark.asyncio
async def test_cpu_intensive_direct():
    """Test cpu_intensive operation directly."""
    group = TimeoutGroup()

    # Create a TextContent object to use as Context
    ctx = TextContent(type="text", text="")

    # Add the required methods for testing
    async def report_progress(current, total):
        pass

    def info(message):
        pass

    ctx.report_progress = report_progress
    ctx.info = info

    result = await group.cpu_intensive(
        1000, ctx
    )  # Small iteration count for testing
    assert "Completed 1000 iterations" in result
    assert "result:" in result


# Skip MCP client tests for now - we'll implement these once we have the proper MCP client setup
@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_timeout_group_via_mcp():
    """Test TimeoutGroup operations via MCP client."""
    # This test will be implemented with proper MCP client setup
    assert True


@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_timeout_handling():
    """Test operation timeout handling."""
    # This test will be implemented with proper MCP client setup
    assert True


@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_progress_reporting():
    """Test progress reporting in timeout operations."""
    # This test will be implemented with proper MCP client setup
    assert True
