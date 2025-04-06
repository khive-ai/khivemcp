#!/usr/bin/env python3
"""
MCP Format Test Client

This script demonstrates the exact format that an MCP client would use to call the tools.
"""

import asyncio
import json
from verification.groups.mcp_data_processor_group import (
    MCPDataProcessorGroup,
    SchemaDefinition, 
    ValidationResult
)
from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.types import ExecutionRequest, ExecutionResponse, ServiceRequest, ServiceResponse

async def main():
    print("\n=== MCP Format Test ===")
    
    # Create processor instance
    processor = MCPDataProcessorGroup()
    
    # Test data
    test_data = "test string"
    test_schema = {"type": "string"}
    
    # Mimicking exactly how AutoMCP would call the operation
    print("\nSimulating an MCP request...")
    
    # This is how the automcp.group.ServiceGroup._execute method constructs the arguments
    args = {"data": test_data, "schema": test_schema}
    
    try:
        # Directly call the method with proper kwargs as MCP would
        result = await processor.validate_schema(**args)
        print(f"Direct kwargs call result: {result}")
    except Exception as e:
        print(f"Error calling with kwargs: {e}")
        import traceback
        traceback.print_exc()
    
    # Now simulate exactly the flow in automcp.group.py
    print("\nSimulating full AutoMCP flow...")
    try:
        # Create the execution request like in automcp.server.py
        request = ExecutionRequest(operation="validate_schema", arguments=args)
        
        # Extract arguments exactly as done in automcp.group._execute
        operation_args = request.arguments or {}
        
        # Get the operation from the registry 
        operation = processor.validate_schema
        
        # Call it as done in _execute
        print(f"Calling with operation_args={operation_args}")
        result = await operation(**operation_args)
        print(f"Full simulation result: {result}")
    except Exception as e:
        print(f"Error in full simulation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())