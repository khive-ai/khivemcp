"""Tests for the ExampleGroup service group."""

import pytest

from verification.groups.example_group import ExampleGroup


@pytest.mark.asyncio
async def test_hello_world_direct():
    """Test hello_world operation directly."""
    group = ExampleGroup()
    result = await group.hello_world()
    assert result == "Hello, World!"


@pytest.mark.asyncio
async def test_echo_direct():
    """Test echo operation directly."""
    group = ExampleGroup()
    result = await group.echo("test message")
    assert result == "Echo: test message"


@pytest.mark.asyncio
async def test_count_to_direct():
    """Test count_to operation directly."""
    group = ExampleGroup()
    result = await group.count_to(3)
    assert result == "1, 2, 3"


# Skip MCP client tests for now - we'll implement these once we have the proper MCP client setup
@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_example_group_via_mcp():
    """Test ExampleGroup operations via MCP client."""
    # This test will be implemented with proper MCP client setup
    assert True


@pytest.mark.skip(reason="MCP client tests require proper MCP client setup")
@pytest.mark.asyncio
async def test_example_group_invalid_input():
    """Test ExampleGroup operations with invalid inputs."""
    # This test will be implemented with proper MCP client setup
    assert True
