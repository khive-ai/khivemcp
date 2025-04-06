#!/usr/bin/env python3
"""
Simplified test for DataProcessorGroup functionality.
This first tests direct invocation, then through the MCP protocol.
"""

import asyncio
import json
from pprint import pprint

from mcp.types import TextContent
from automcp.server import AutoMCPServer
from automcp.types import GroupConfig
from verification.tests.test_helpers import create_connected_automcp_server_and_client_session

from verification.groups.data_processor_group import (
    DataItem,
    DataProcessorGroup,
    ProcessingParameters,
    SchemaDefinition,
)


async def test_direct_operations():
    """Test DataProcessorGroup operations by direct invocation."""
    print("\n=== Testing direct group operations ===")
    
    # Create the group
    group = DataProcessorGroup()
    
    # Create mock context
    ctx = TextContent(type="text", text="")
    logs = []
    progress = []
    
    async def report_progress(current, total):
        progress.append((current, total))
    
    def info(message):
        logs.append(message)
        print(f"Log: {message}")
    
    ctx.report_progress = report_progress
    ctx.info = info
    
    # Create test data
    test_data = [
        DataItem(
            id="item1",
            value="Sample Text",
            metadata={"category": "text", "priority": "high"}
        ),
        DataItem(
            id="item2",
            value=42,
            metadata={"category": "number", "priority": "medium"}
        ),
        DataItem(
            id="item3",
            value=78.5,
            metadata={"category": "number", "priority": "low"}
        )
    ]
    
    # Test process_data
    print("\nTesting process_data directly...")
    params = ProcessingParameters(
        transform_case="upper",
        aggregate=True,
        sort_by="id",
        sort_order="asc"
    )
    
    result = await group.process_data(data=test_data, parameters=params, ctx=ctx)
    print(f"Process data result: {result}")
    
    # Test generate_report
    print("\nTesting generate_report directly...")
    report = await group.generate_report(
        processed_data=result,
        format={"title": "Direct Test Report", "format_type": "markdown"},
        ctx=ctx
    )
    print(f"Report preview: {report[:200]}...")
    
    # Test validate_schema
    print("\nTesting validate_schema directly...")
    schema_def = SchemaDefinition(
        type="object",
        properties={
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0, "maximum": 120}
        },
        required=["name"]
    )
    
    valid_data = {"name": "John Doe", "age": 30}
    validation_result = await group.validate_schema(data=valid_data, schema=schema_def)
    print(f"Validation result: {validation_result}")
    
    return "Direct testing completed successfully!"


async def test_mcp_operations():
    """Test DataProcessorGroup operations through MCP protocol."""
    print("\n=== Testing MCP protocol operations ===")
    
    # Create server configuration
    config = GroupConfig(
        name="data-processor",
        description="Group for data processing operations",
        config={
            "default_processing": {
                "filter_fields": None,
                "transform_case": None,
                "aggregate": False,
                "sort_by": None,
                "sort_order": "asc"
            },
            "default_report_format": {
                "title": "Data Processing Report",
                "include_summary": True,
                "include_timestamp": True,
                "format_type": "text"
            }
        }
    )
    
    # Create the server with our configuration
    server = AutoMCPServer("test-server", config)
    
    # Create and register the data processor group
    data_processor_group = DataProcessorGroup()
    server.groups["data-processor"] = data_processor_group
    
    try:
        # Connect server and client
        print("Creating in-memory server and client connection...")
        async with create_connected_automcp_server_and_client_session(server) as (_, client):
            print("Connected successfully!")
            
            # List available tools
            tools_result = await client.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            print(f"Available tools: {tool_names}")
            
            # Test process_data operation
            print("\nTesting process_data via MCP...")
            process_data_input = {
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
            
            response = await client.call_tool("data-processor.process_data", process_data_input)
            response_text = response.content[0].text if response.content else ""
            print(f"Process data response: {response_text[:200]}...")
            
            # Try to parse the response for further operations
            try:
                # First try to parse as JSON
                try:
                    processed_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # If not valid JSON, try to eval as Python dict
                    processed_data = eval(response_text)
                print("Successfully parsed response")
            except Exception as e:
                print(f"Failed to parse response: {e}")
                # Create a simple structure for testing the next operation
                processed_data = {
                    "processed_items": [
                        {"id": "item1", "value": "SAMPLE TEXT"},
                        {"id": "item2", "value": 42}
                    ]
                }
            
            # Test generate_report operation
            print("\nTesting generate_report via MCP...")
            report_request = {
                "processed_data": processed_data,
                "format": {
                    "title": "MCP Test Report",
                    "format_type": "markdown"
                }
            }
            
            response = await client.call_tool("data-processor.generate_report", report_request)
            response_text = response.content[0].text if response.content else ""
            print(f"Report preview: {response_text[:200]}...")
            
            # Test validate_schema operation
            print("\nTesting validate_schema via MCP...")
            schema_request = {
                "data": {"name": "Test User", "age": 30},
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer", "minimum": 0, "maximum": 120}
                    },
                    "required": ["name"]
                }
            }
            
            response = await client.call_tool("data-processor.validate_schema", schema_request)
            response_text = response.content[0].text if response.content else ""
            print(f"Schema validation response: {response_text}")
            
            return "MCP protocol testing completed successfully!"
    except Exception as e:
        print(f"Error during MCP testing: {e}")
        return f"MCP protocol testing failed: {e}"


if __name__ == "__main__":
    # Run both tests
    direct_result = asyncio.run(test_direct_operations())
    print(f"\nDirect test result: {direct_result}")
    
    # Only run MCP test if direct test succeeded
    if "successfully" in direct_result:
        mcp_result = asyncio.run(test_mcp_operations())
        print(f"\nMCP test result: {mcp_result}")
    else:
        print("\nSkipping MCP test due to direct test failure")