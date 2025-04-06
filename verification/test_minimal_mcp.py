#!/usr/bin/env python3
"""
Minimal test for DataProcessorGroup through MCP protocol.
Only tests setting up the server and listing available tools.
"""

import asyncio
import traceback

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig
from verification.groups.data_processor_group import DataProcessorGroup
from verification.tests.test_helpers import create_connected_automcp_server_and_client_session


async def test_minimal_mcp():
    """Test minimal MCP setup for DataProcessorGroup."""
    print("\n=== Testing Minimal MCP Setup ===")
    
    try:
        # Create server configuration
        print("Creating server configuration...")
        config = GroupConfig(
            name="data-processor",
            description="Group for data processing operations"
        )
        
        # Create and register the server
        print("Creating server...")
        server = AutoMCPServer("test-server", config)
        
        # Create and register the data processor group
        print("Registering data processor group...")
        data_processor_group = DataProcessorGroup()
        data_processor_group.config = config.config
        server.groups["data-processor"] = data_processor_group
        
        # Connect server and client
        print("Creating in-memory server and client connection...")
        async with create_connected_automcp_server_and_client_session(server) as (_, client):
            print("Connected successfully!")
            
            # Only list available tools
            print("Listing available tools...")
            try:
                tools_result = await client.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                print(f"Available tools: {tool_names}")
                return "Minimal MCP test successful!"
            except Exception as e:
                print(f"Error listing tools: {e}")
                traceback.print_exc()
                return f"Error listing tools: {e}"
    
    except Exception as e:
        print(f"Error in test: {e}")
        traceback.print_exc()
        return f"Test failed: {e}"


if __name__ == "__main__":
    result = asyncio.run(test_minimal_mcp())
    print(f"\nTest result: {result}")