"""Example math operations group."""

from typing import Optional

import numpy as np
from pydantic import BaseModel, Field

from automcp import ServiceGroup, operation
from automcp.schemas.base import ExecutionResponse, TextContent


class ArithmeticInput(BaseModel):
    """Input for arithmetic operations."""

    x: float = Field(..., description="First number")
    y: float = Field(..., description="Second number")
    precision: Optional[int] = Field(None, description="Decimal precision")


class MathGroup(ServiceGroup):
    """Math operations group."""

    @operation(schema=ArithmeticInput)
    async def add(self, input: ArithmeticInput) -> ExecutionResponse:
        """Add two numbers."""
        result = input.x + input.y
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=ArithmeticInput)
    async def subtract(self, input: ArithmeticInput) -> ExecutionResponse:
        """Subtract two numbers."""
        result = input.x - input.y
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=ArithmeticInput)
    async def multiply(self, input: ArithmeticInput) -> ExecutionResponse:
        """Multiply two numbers."""
        result = input.x * input.y
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=ArithmeticInput)
    async def divide(self, input: ArithmeticInput) -> ExecutionResponse:
        """Divide two numbers."""
        if input.y == 0:
            return ExecutionResponse(
                content=TextContent(type="text", text="Error: Division by zero"),
                error="Division by zero",
            )

        result = input.x / input.y
        if input.precision is not None:
            result = round(result, input.precision)
        return ExecutionResponse(content=TextContent(type="text", text=str(result)))

    @operation(schema=ArithmeticInput)
    async def power(self, input: ArithmeticInput) -> ExecutionResponse:
        """Raise x to the power of y."""
        try:
            result = np.power(input.x, input.y)
            if input.precision is not None:
                result = round(result, input.precision)
            return ExecutionResponse(content=TextContent(type="text", text=str(result)))
        except Exception as e:
            return ExecutionResponse(
                content=TextContent(type="text", text=f"Error: {str(e)}"), error=str(e)
            )
