"""Tests for statistics operations group."""

import numpy as np
import pytest

from automcp.schemas.base import ExecutionResponse, TextContent
from examples.stats import DistributionInput, StatsGroup, StatsInput


@pytest.fixture
async def stats_group():
    """Create stats group instance."""
    return StatsGroup()


@pytest.mark.asyncio
async def test_mean(stats_group):
    """Test mean operation."""
    input = StatsInput(values=[1, 2, 3, 4, 5])
    response = await stats_group.mean(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "3.0"
    assert not response.error

    # Test with precision
    input = StatsInput(values=[1.234, 2.345, 3.456], precision=2)
    response = await stats_group.mean(input)
    assert response.content.text == "2.35"


@pytest.mark.asyncio
async def test_median(stats_group):
    """Test median operation."""
    # Odd number of values
    input = StatsInput(values=[1, 2, 3, 4, 5])
    response = await stats_group.median(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert response.content.text == "3.0"
    assert not response.error

    # Even number of values
    input = StatsInput(values=[1, 2, 3, 4])
    response = await stats_group.median(input)
    assert response.content.text == "2.5"

    # Test with precision
    input = StatsInput(values=[1.234, 2.345, 3.456], precision=2)
    response = await stats_group.median(input)
    assert response.content.text == "2.35"


@pytest.mark.asyncio
async def test_std(stats_group):
    """Test standard deviation operation."""
    input = StatsInput(values=[1, 2, 3, 4, 5])
    response = await stats_group.std(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert float(response.content.text) == pytest.approx(1.4142, rel=1e-4)
    assert not response.error

    # Test with precision
    input = StatsInput(values=[1.234, 2.345, 3.456], precision=3)
    response = await stats_group.std(input)
    assert float(response.content.text) == pytest.approx(1.111, rel=1e-3)


@pytest.mark.asyncio
async def test_variance(stats_group):
    """Test variance operation."""
    input = StatsInput(values=[1, 2, 3, 4, 5])
    response = await stats_group.variance(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert float(response.content.text) == pytest.approx(2.0, rel=1e-4)
    assert not response.error

    # Test with precision
    input = StatsInput(values=[1.234, 2.345, 3.456], precision=3)
    response = await stats_group.variance(input)
    assert float(response.content.text) == pytest.approx(1.234, rel=1e-3)


@pytest.mark.asyncio
async def test_normal_sample(stats_group):
    """Test normal distribution sampling."""
    input = DistributionInput(mean=0, std=1, size=1000)
    response = await stats_group.normal_sample(input)
    assert isinstance(response, ExecutionResponse)
    assert response.content.type == "text"
    assert not response.error

    # Convert result back to list and verify statistics
    samples = eval(response.content.text)  # Safe since we know it's a list of numbers
    assert len(samples) == 1000
    assert abs(np.mean(samples)) < 0.1  # Should be close to 0
    assert abs(np.std(samples) - 1) < 0.1  # Should be close to 1

    # Test with precision
    input = DistributionInput(mean=0, std=1, size=10, precision=2)
    response = await stats_group.normal_sample(input)
    samples = eval(response.content.text)
    assert all(isinstance(x, float) for x in samples)
    assert all(str(x).split(".")[-1] if "." in str(x) else "0" <= "00" for x in samples)

    # Test error case
    input = DistributionInput(mean=0, std=-1, size=10)  # Negative std
    response = await stats_group.normal_sample(input)
    assert response.error is not None
