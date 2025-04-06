#!/usr/bin/env python3
"""
Script to properly test the running data processor MCP server.
This connects to the server as a client should, not by directly calling operations.
"""

import asyncio
import json
import sys
from pprint import pprint

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_data_processor_server():
    """Test the data processor server properly using MCP client."""
    print("\n=== Testing Data Processor MCP Server ===")
    
    # Connection parameters for a new server instance
    # Note: To test the already running server, we would need to connect to its stdio
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "automcp.cli", "run", "verification/config/data_processor_group.json", "--mode", "stdio"],
    )
    
    try:
        print("Connecting to server...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize connection
                await client.initialize()
                print("Connected to server successfully")
                
                # List available tools
                tools_result = await client.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                print(f"Available tools: {tool_names}")
                
                # Test process_data operation
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
                
                response = await client.call_tool("data-processor.process_data", process_data)
                response_text = response.content[0].text if response.content else ""
                print(f"Process data response: {response_text}")
                
                # Parse the response for further operations
                try:
                    # First try to parse as JSON
                    try:
                        processed_data = json.loads(response_text)
                        print("Parsed as JSON")
                    except json.JSONDecodeError:
                        # If not valid JSON, try to parse as Python dict
                        processed_data = eval(response_text)
                        print("Parsed with eval")
                        
                    # Test generate_report operation
                    print("\nTesting generate_report operation...")
                    report_request = {
                        "processed_data": processed_data,
                        "format": {
                            "title": "Test Report",
                            "format_type": "markdown",
                            "include_summary": True,
                            "include_timestamp": True
                        }
                    }
                    
                    response = await client.call_tool("data-processor.generate_report", report_request)
                    response_text = response.content[0].text if response.content else ""
                    print(f"Report response preview: {response_text[:150]}...")
                    
                    # Test validate_schema operation
                    print("\nTesting validate_schema operation...")
                    schema_request = {
                        "data": {"name": "Test User", "email": "test@example.com"},
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string", "format": "email"}
                            },
                            "required": ["name", "email"]
                        }
                    }
                    
                    response = await client.call_tool("data-processor.validate_schema", schema_request)
                    response_text = response.content[0].text if response.content else ""
                    print(f"Schema validation response: {response_text}")
                    
                    print("\nAll tests completed successfully!")
                    
                except Exception as e:
                    print(f"Error in tests: {e}")
                    import traceback
                    traceback.print_exc()
                
    except Exception as e:
        print(f"Error connecting to server: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_data_processor_server())