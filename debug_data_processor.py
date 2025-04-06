#!/usr/bin/env python3
"""
Debug script for testing DataProcessorGroup directly and through the execution mechanism.
"""

import asyncio
import json
from pprint import pprint

from mcp.types import TextContent as Context
from automcp.types import ExecutionRequest, ExecutionResponse
from verification.groups.data_processor_group import (
    DataItem,
    DataProcessingSchema,
    DataProcessorGroup,
    ProcessingParameters,
)


async def test_direct_call():
    """Test calling process_data directly on the group instance."""
    print("\n=== Testing Direct Call ===")

    # Create the DataProcessorGroup
    group = DataProcessorGroup()
    
    # Create a context
    ctx = Context(type="text", text="")
    ctx.info = lambda msg: print(f"Log: {msg}")
    ctx.report_progress = lambda current, total: None
    
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
        )
    ]
    
    # Create parameters
    params = ProcessingParameters(
        transform_case="upper",
        aggregate=True
    )
    
    # Create the schema object that would normally be created by the decorator
    data_schema = DataProcessingSchema(data=test_data, parameters=params)
    
    # Call the method directly
    try:
        result = await group.process_data(data=data_schema, ctx=ctx)
        print("Direct call succeeded!")
        pprint(result)
        return result
    except Exception as e:
        print(f"Direct call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_execute_method():
    """Test calling process_data through the execute method."""
    print("\n=== Testing Execute Method ===")

    # Create the DataProcessorGroup
    group = DataProcessorGroup()
    
    # Create test data in the format expected by the execute method
    test_data = [
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
    ]
    
    # Create the arguments dictionary
    args = {
        "data": test_data,
        "parameters": {
            "transform_case": "upper",
            "aggregate": True
        }
    }
    
    # Create the execution request
    request = ExecutionRequest(operation="process_data", arguments=args)
    
    # Call execute
    try:
        response = await group.execute(request)
        print("Execute method call succeeded!")
        print(f"Response: {response.content.text}")
        return response
    except Exception as e:
        print(f"Execute method call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_with_various_parameter_formats():
    """Test with different parameter formats to diagnose the issue."""
    print("\n=== Testing Different Parameter Formats ===")
    
    group = DataProcessorGroup()
    
    # Test 1: Try with a single argument containing both data and parameters
    print("\nTest 1: Single combined argument")
    request1 = ExecutionRequest(
        operation="process_data",
        arguments={
            "data_schema": {
                "data": [{"id": "item1", "value": "Test"}],
                "parameters": {"transform_case": "upper"}
            }
        }
    )
    
    try:
        response1 = await group.execute(request1)
        print(f"Test 1 Result: {response1.content.text}")
    except Exception as e:
        print(f"Test 1 Failed: {e}")
    
    # Test 2: Try with data as a positional argument
    print("\nTest 2: Positional argument")
    request2 = ExecutionRequest(
        operation="process_data",
        arguments=[{
            "data": [{"id": "item1", "value": "Test"}],
            "parameters": {"transform_case": "upper"}
        }]
    )
    
    try:
        response2 = await group.execute(request2)
        print(f"Test 2 Result: {response2.content.text}")
    except Exception as e:
        print(f"Test 2 Failed: {e}")
    
    # Test 3: Try with a completely flattened structure
    print("\nTest 3: Flattened structure")
    request3 = ExecutionRequest(
        operation="process_data",
        arguments={
            "data": [{"id": "item1", "value": "Test"}],
            "parameters": {"transform_case": "upper"}
        }
    )
    
    try:
        response3 = await group.execute(request3)
        print(f"Test 3 Result: {response3.content.text}")
    except Exception as e:
        print(f"Test 3 Failed: {e}")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_direct_call())
    asyncio.run(test_execute_method())
    asyncio.run(test_with_various_parameter_formats())