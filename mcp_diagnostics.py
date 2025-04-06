#!/usr/bin/env python3
"""
Diagnostic tool to help troubleshoot MCP server issues.
"""

import sys
import traceback
from functools import wraps
import inspect
import asyncio
import json
from pprint import pprint

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_data_processor():
    """Test the data processor server in diagnostic mode."""
    print("\n=== Running MCP Diagnostics ===")
    
    # Connection parameters for the server
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "automcp.cli", "run", "verification/config/data_processor_group.json", "--mode", "stdio"],
    )
    
    try:
        print("Starting diagnostic MCP client session...")
        
        # Patch the ClientSession.call_tool method to trace all calls
        original_call_tool = ClientSession.call_tool
        
        @wraps(original_call_tool)
        async def diagnostic_call_tool(self, name, arguments=None):
            print(f"\nDIAGNOSTIC: Calling tool {name} with arguments:")
            pprint(arguments)
            
            try:
                print("DIAGNOSTIC: Calling original method...")
                result = await original_call_tool(self, name, arguments)
                print("DIAGNOSTIC: Tool call successful!")
                print(f"DIAGNOSTIC: Result: {result}")
                return result
            except Exception as e:
                print(f"DIAGNOSTIC: Error calling tool: {e}")
                print("DIAGNOSTIC: Stack trace:")
                traceback.print_exc()
                raise
        
        # Apply the patch
        ClientSession.call_tool = diagnostic_call_tool
        
        # Also patch the send_request method to see what's happening at a lower level
        original_send_request = ClientSession.send_request
        
        @wraps(original_send_request)
        async def diagnostic_send_request(self, *args, **kwargs):
            print("\nDIAGNOSTIC: send_request called with:")
            print(f"DIAGNOSTIC: - args: {args}")
            print(f"DIAGNOSTIC: - kwargs: {kwargs}")
            
            try:
                print("DIAGNOSTIC: Calling original send_request...")
                result = await original_send_request(self, *args, **kwargs)
                print("DIAGNOSTIC: send_request successful!")
                return result
            except Exception as e:
                print(f"DIAGNOSTIC: Error in send_request: {e}")
                print("DIAGNOSTIC: Stack trace:")
                traceback.print_exc()
                raise
        
        # Apply the second patch
        ClientSession.send_request = diagnostic_send_request
        
        # Connect to the server and run the diagnostic
        print("Connecting to server...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize the connection
                await client.initialize()
                print("Connected to server successfully")
                
                # Try to call a simple operation
                print("\nTrying simple operation...")
                try:
                    result = await client.call_tool("data-processor.validate_schema", {
                        "data": "test string",
                        "schema": {
                            "type": "string"
                        }
                    })
                    print(f"Operation result: {result}")
                except Exception as e:
                    print(f"Operation failed: {e}")
                
                print("\nDiagnostic complete!")
                
    except Exception as e:
        print(f"Diagnostic session error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_data_processor())