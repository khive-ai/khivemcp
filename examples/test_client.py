"""Test client for math service."""

import asyncio
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    """Run test client."""
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "automcp", "examples/math-service.yaml"]
    )

    async with stdio_client(server) as (read_stream, write_stream):
        client = ClientSession(read_stream, write_stream)

        # List available tools
        tools = await client.list_tools()
        print("\nAvailable tools:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        # Test add operation
        print("\nTesting add operation...")
        result = await client.call_tool("math-ops.add", {"x": 2, "y": 3})
        print(f"2 + 3 = {result[0].text}")

        # Test subtract operation
        print("\nTesting subtract operation...")
        result = await client.call_tool("math-ops.subtract", {"x": 5, "y": 3})
        print(f"5 - 3 = {result[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
