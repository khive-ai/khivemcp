import asyncio
import time

from mcp.types import TextContent as Context

from automcp.group import ServiceGroup
from automcp.operation import operation


class TimeoutGroup(ServiceGroup):
    """Group with operations for testing timeout functionality."""

    @operation()
    async def sleep(self, seconds: float) -> str:
        """Sleep for the specified number of seconds.

        This operation simply waits for the specified duration and returns.
        Useful for basic timeout testing.
        """
        await asyncio.sleep(seconds)
        return f"Slept for {seconds} seconds"

    @operation()
    async def slow_counter(
        self, limit: int, delay: float, ctx: Context
    ) -> str:
        """Count up to a limit with delay between each number and progress reporting.

        Args:
            limit: The number to count up to
            delay: Seconds to wait between counts
            ctx: MCP context for progress reporting

        Returns:
            A string with the counting results and timing information
        """
        result = []
        start_time = time.time()

        for i in range(1, limit + 1):
            await ctx.report_progress(i, limit)
            ctx.info(f"Counter: {i}/{limit}")
            result.append(str(i))
            await asyncio.sleep(delay)

        total_time = time.time() - start_time
        return f"Counted to {limit} in {total_time:.2f} seconds: {', '.join(result)}"

    @operation()
    async def cpu_intensive(self, iterations: int, ctx: Context) -> str:
        """Perform a CPU-intensive operation for testing timeout.

        This operation does meaningless but CPU-intensive work to test
        how the timeout handling works with CPU-bound operations.

        Args:
            iterations: Number of calculation iterations to perform
            ctx: MCP context for progress reporting

        Returns:
            A string with timing information and result
        """
        ctx.info(
            f"Starting CPU-intensive operation with {iterations} iterations"
        )
        start_time = time.time()

        result = 0
        chunk_size = 100  # Process in smaller chunks to allow timeout checks

        for i in range(iterations):
            if i % (iterations // 10) == 0 or i % chunk_size == 0:
                # Yield control to event loop more frequently to allow timeout checks
                progress = (i / iterations) * 100
                await ctx.report_progress(i, iterations)
                ctx.info(f"Progress: {progress:.1f}%")
                # Explicitly yield control to the event loop
                await asyncio.sleep(0)

            # CPU-intensive work - reduced workload for faster tests
            result += sum(j * j for j in range(1000))

            # Yield control every chunk_size iterations
            if i % chunk_size == chunk_size - 1:
                await asyncio.sleep(
                    0
                )  # Yield to event loop without actual delay

        total_time = time.time() - start_time
        return f"Completed {iterations} iterations in {total_time:.2f} seconds with result: {result}"
