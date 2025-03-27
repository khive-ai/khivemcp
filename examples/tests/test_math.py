"""Tests for math operations group."""

import asyncio

import pytest

from automcp.schemas.base import ExecutionResponse, TextContent
from examples.math_service import ArithmeticInput, MathGroup


@pytest.fixture
async def math_group():
    """Create math group instance with cleanup."""
    group = MathGroup()
    yield group
    await group.cleanup()


@pytest.fixture
async def concurrent_group():
    """Create math group for concurrent testing."""
    group = MathGroup(config={"timeout": 0.5})
    yield group
    await group.cleanup()


@pytest.mark.asyncio
async def test_add(math_group):
    """Test add operation."""
    input = ArithmeticInput(x=2, y=3)
    response = await math_group.add(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "5"
    assert not response.error

    # Test with precision
    input = ArithmeticInput(x=2.123, y=3.456, precision=2)
    response = await math_group.add(input)
    assert response.content.text == "5.58"


@pytest.mark.asyncio
async def test_subtract(math_group):
    """Test subtract operation."""
    input = ArithmeticInput(x=5, y=3)
    response = await math_group.subtract(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "2"
    assert not response.error

    # Test with precision
    input = ArithmeticInput(x=5.678, y=3.456, precision=2)
    response = await math_group.subtract(input)
    assert response.content.text == "2.22"


@pytest.mark.asyncio
async def test_multiply(math_group):
    """Test multiply operation."""
    input = ArithmeticInput(x=4, y=3)
    response = await math_group.multiply(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "12"
    assert not response.error

    # Test with precision
    input = ArithmeticInput(x=4.123, y=3.456, precision=2)
    response = await math_group.multiply(input)
    assert response.content.text == "14.25"


@pytest.mark.asyncio
async def test_divide(math_group):
    """Test divide operation."""
    input = ArithmeticInput(x=6, y=2)
    response = await math_group.divide(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "3.0"
    assert not response.error

    # Test division by zero
    input = ArithmeticInput(x=6, y=0)
    response = await math_group.divide(input)
    assert response.error == "Division by zero"

    # Test with precision
    input = ArithmeticInput(x=5.678, y=2.5, precision=2)
    response = await math_group.divide(input)
    assert response.content.text == "2.27"


@pytest.mark.asyncio
async def test_power(math_group):
    """Test power operation."""
    input = ArithmeticInput(x=2, y=3)
    response = await math_group.power(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "8.0"
    assert not response.error

    # Test with precision
    input = ArithmeticInput(x=2.5, y=2, precision=2)
    response = await math_group.power(input)
    assert response.content.text == "6.25"

    # Test error case
    input = ArithmeticInput(x=-1, y=0.5)
    response = await math_group.power(input)
    assert response.error is not None


@pytest.mark.asyncio
async def test_concurrent_operations(concurrent_group):
    """Test concurrent operation execution."""
    inputs = [ArithmeticInput(x=i, y=i + 1) for i in range(5)]

    async def run_add(input):
        return await concurrent_group.add(input)

    # Run operations concurrently
    tasks = [run_add(input) for input in inputs]
    responses = await asyncio.gather(*tasks)

    # Verify results
    for i, response in enumerate(responses):
        assert not response.error
        assert float(response.content.text) == i + (i + 1)


@pytest.mark.asyncio
async def test_operation_timeout(concurrent_group):
    """Test operation timeout handling."""

    async def slow_power():
        input = ArithmeticInput(x=2, y=1000000)  # Large computation
        try:
            await concurrent_group.power(input)
        except asyncio.TimeoutError:
            return True
        return False

    # Should timeout
    assert await asyncio.wait_for(slow_power(), timeout=1.0)


@pytest.mark.asyncio
async def test_cleanup(math_group):
    """Test resource cleanup."""
    # Create some operations
    inputs = [ArithmeticInput(x=i, y=i) for i in range(3)]

    # Start operations
    tasks = []
    for input in inputs:
        task = asyncio.create_task(math_group.add(input))
        tasks.append(task)

    # Let operations start
    await asyncio.sleep(0.1)

    # Cancel tasks
    for task in tasks:
        if not task.done():
            task.cancel()

    # Cleanup should handle cancellation
    await math_group.cleanup()

    # Verify cleanup
    assert len(math_group._contexts) == 0
