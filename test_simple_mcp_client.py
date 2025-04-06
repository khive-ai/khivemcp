#!/usr/bin/env python3
"""
Simple MCP test client to directly invoke our data processor.

This script bypasses most of the MCP-AutoMCP integration layers to help us debug 
the exact issue.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from verification.groups.mcp_data_processor_group import MCPDataProcessorGroup

async def main():
    print("\n=== Simple MCP Test Client ===")
    
    # Create a standalone instance of our data processor
    data_processor = MCPDataProcessorGroup()
    
    # Test 1: Direct method call
    print("\nTesting direct method call...")
    result = await data_processor.validate_schema(
        data="test string",
        schema={"type": "string"}
    )
    print(f"Direct call result: {result}")
    
    # Test 2: Through stdio protocol
    print("\nStarting MCP stdio server...")
    server_cmd = "uv run python -m automcp.cli run verification/config/mcp_wrapper_config.json --mode stdio"
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "automcp.cli", "run", 
              "verification/config/mcp_wrapper_config.json", "--mode", "stdio"],
    )
    
    try:
        print("Connecting to MCP server...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize
                await client.initialize()
                print("Connected successfully!")
                
                # List available tools
                tools_result = await client.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                print(f"Available tools: {tool_names}")
                
                # Try validate_schema
                print("\nTesting validate_schema via MCP...")
                try:
                    response = await client.call_tool(
                        "data-processor.validate_schema", 
                        arguments={"data": "test string", "schema": {"type": "string"}}
                    )
                    print(f"Response: {response.content[0].text if response.content else 'No content'}")
                except Exception as e:
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()
                
    except Exception as e:
        print(f"Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())