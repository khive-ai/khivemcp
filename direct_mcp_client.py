#!/usr/bin/env python3
"""
A direct MCP client to test interacting with the data processor server.
This bypasses the use_mcp_tool and interacts directly with the server.
"""

import asyncio
import json
import subprocess
import sys
from pprint import pprint

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    """Run the direct MCP client."""
    print("\n=== Direct MCP Client for Data Processor ===")
    
    # Kill any existing servers
    try:
        subprocess.run(["pkill", "-f", "automcp.cli run verification/config/data_processor_group.json"])
        await asyncio.sleep(1)  # Give the server time to shut down
    except Exception:
        pass
    
    # Start a new server process
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "automcp.cli", "run", "verification/config/data_processor_group.json", "--mode", "stdio"],
    )
    
    try:
        # Connect to the server
        print("Starting and connecting to server...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize the connection
                await client.initialize()
                print("Connected to server successfully")
                
                # List available tools
                tools_result = await client.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                print(f"Available tools: {tool_names}")
                
                # Try validate_schema operation
                print("\nTesting validate_schema operation...")
                schema_request = {
                    "data": "test string",
                    "schema": {
                        "type": "string"
                    }
                }
                
                try:
                    response = await client.call_tool("data-processor.validate_schema", schema_request)
                    response_text = response.content[0].text if response.content else ""
                    print(f"Response: {response_text}")
                except Exception as e:
                    print(f"Error calling validate_schema: {e}")
                    traceback.print_exc()
                
                # Try process_data operation
                print("\nTesting process_data operation...")
                process_data = {
                    "data": [
                        {
                            "id": "item1",
                            "value": "Sample Text",
                            "metadata": {"category": "text", "priority": "high"}
                        },
                        {
                            "id": "item2",
                            "value": 42,
                            "metadata": {"category": "number", "priority": "medium"}
                        }
                    ],
                    "parameters": {
                        "transform_case": "upper",
                        "aggregate": True
                    }
                }
                
                try:
                    response = await client.call_tool("data-processor.process_data", process_data)
                    response_text = response.content[0].text if response.content else ""
                    print(f"Response: {response_text}")
                except Exception as e:
                    print(f"Error calling process_data: {e}")
                    import traceback
                    traceback.print_exc()
                    
                print("\nDirect client test complete")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())