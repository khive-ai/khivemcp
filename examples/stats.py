"""Example statistics operations group."""

from typing import List, Optional

import numpy as np
from pydantic import BaseModel, Field

from automcp import ServiceGroup, operation
from automcp.schemas.base import ExecutionResponse, TextContent


class StatsInput(BaseModel):
    """Input for statistics operations."""

    values: List[float] = Field(..., description="List of numbers")
    precision: Optional[int] = Field(None, description="Decimal precision")


class DistributionInput(BaseModel):
    """Input for distribution operations."""

    mean: float = Field(..., description="Mean of the distribution")
    std: float = Field(..., description="Standard deviation")
    size: int = Field(..., description="Number of samples")
    precision: Optional[int] = Field(None, description="Decimal precision")


class StatsGroup(ServiceGroup):
    """Statistics operations group."""

    @operation(schema=StatsInput)
    async def mean(self, input: StatsInput) -> ExecutionResponse:
        """Calculate mean of numbers."""
        result = np.mean(input.values)
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=StatsInput)
    async def median(self, input: StatsInput) -> ExecutionResponse:
        """Calculate median of numbers."""
        result = np.median(input.values)
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=StatsInput)
    async def std(self, input: StatsInput) -> ExecutionResponse:
        """Calculate standard deviation of numbers."""
        result = np.std(input.values)
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=StatsInput)
    async def variance(self, input: StatsInput) -> ExecutionResponse:
        """Calculate variance of numbers."""
        result = np.var(input.values)
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=DistributionInput)
    async def normal_sample(self, input: DistributionInput) -> ExecutionResponse:
        """Generate samples from normal distribution."""
        try:
            samples = np.random.normal(loc=input.mean, scale=input.std, size=input.size)
            if input.precision is not None:
                samples = np.round(samples, input.precision)
            return ExecutionResponse(
                content=TextContent(type="text", text=str(samples.tolist()))
            )
        except Exception as e:
            return ExecutionResponse(
                content=TextContent(type="text", text=f"Error: {str(e)}"), error=str(e)
            )
