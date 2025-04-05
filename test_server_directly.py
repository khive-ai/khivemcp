#!/usr/bin/env python3
"""
Simple script to test connecting to an AutoMCP server directly.
"""

import asyncio
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    """Connect to an AutoMCP server and test basic operations."""
    if len(sys.argv) < 2:
        print("Usage: python test_server_directly.py <config_file>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    print(f"Testing server with config: {config_path}")

    # Create server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "verification.run_server", str(config_path)],
    )
    print(f"Starting server with parameters: {server_params}")

    try:
        # Connect to the server using stdio
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize the connection
                await client.initialize()
                print("Client initialized successfully")

                # Get the list of available tools
                tools = await client.list_tools()
                tool_names = [tool.name for tool in tools]
                print(f"Available tools: {tool_names}")

                # Test hello_world operation
                if "example.hello_world" in tool_names:
                    print("Testing example.hello_world operation...")
                    response = await client.call_tool("example.hello_world", {})
                    response_text = response.content[0].text if response.content else ""
                    print(f"Response: {response_text}")
                else:
                    print("example.hello_world operation not found")

                # Test echo operation
                if "example.echo" in tool_names:
                    print("Testing example.echo operation...")
                    response = await client.call_tool(
                        "example.echo", {"text": "Testing AutoMCP"}
                    )
                    response_text = response.content[0].text if response.content else ""
                    print(f"Response: {response_text}")
                else:
                    print("example.echo operation not found")

                # Test count_to operation
                if "example.count_to" in tool_names:
                    print("Testing example.count_to operation...")
                    response = await client.call_tool("example.count_to", {"number": 5})
                    response_text = response.content[0].text if response.content else ""
                    print(f"Response: {response_text}")
                else:
                    print("example.count_to operation not found")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
