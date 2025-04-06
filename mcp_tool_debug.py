#!/usr/bin/env python3
"""
Debug script that mimics how the MCP tool works with DataProcessorGroup.
This helps diagnose the "not enough values to unpack" error.
"""

import asyncio
import json
import sys
from pprint import pprint

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig, ExecutionRequest
from verification.groups.data_processor_group import DataProcessorGroup


async def main():
    """Main debug function."""
    print("=== MCP Tool Debug ===")
    
    # Create configuration similar to the data_processor_group.json
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
    
    # Create the server
    server = AutoMCPServer("test-server", config)
    
    # Create and register the DataProcessorGroup
    group = DataProcessorGroup()
    group.config = config.config
    server.groups["data-processor"] = group
    
    # Test data for process_data
    test_data = {
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
    
    # Direct execution on the group (as the MCP server would do)
    print("\n--- Direct group.execute() ---")
    request = ExecutionRequest(operation="process_data", arguments=test_data)
    try:
        response = await group.execute(request)
        print("Success! Response:")
        print(response.content.text)
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Simulate server handle_request (what happens internally when MCP tool is used)
    print("\n--- Server handle_request() ---")
    try:
        # This is how the server processes MCP tool requests
        group_name = "data-processor"
        operation_name = "process_data"
        
        # Get the group
        target_group = server.groups.get(group_name)
        if not target_group:
            print(f"Group not found: {group_name}")
            return
        
        # Create execution request
        full_op_name = f"{group_name}.{operation_name}"
        execution_request = ExecutionRequest(
            operation=operation_name,
            arguments=test_data
        )
        
        # Execute the request
        response = await target_group.execute(execution_request)
        print("Server execution successful!")
        print(f"Response: {response.content.text}")
    except Exception as e:
        print(f"Server execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to directly call the DataProcessorGroup operation correctly
    print("\n--- Correct Direct Operation Call ---")
    try:
        from verification.groups.data_processor_group import (
            DataItem, 
            DataProcessingSchema,
            ProcessingParameters
        )
        from mcp.types import TextContent
        
        # Create context
        ctx = TextContent(type="text", text="")
        ctx.info = lambda msg: print(f"Log: {msg}")
        ctx.report_progress = lambda current, total: None
        
        # Create data items
        items = [
            DataItem(
                id="item1",
                value="Sample Text",
                metadata={"category": "text", "priority": "high"}
            ),
            DataItem(
                id="item2",
                value=42,
                metadata={"category": "number", "priority": "medium"}
            )
        ]
        
        # Create parameters
        params = ProcessingParameters(
            transform_case="upper",
            aggregate=True
        )
        
        # Create schema instance
        schema = DataProcessingSchema(data=items, parameters=params)
        
        # Call the operation correctly
        result = await group.process_data(schema, ctx)
        print("Direct operation call succeeded!")
        pprint(result)
    except Exception as e:
        print(f"Direct operation call failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())