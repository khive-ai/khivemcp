#!/usr/bin/env python3
"""
Direct validation test for the MCP Data Processor

This script bypasses all the MCP layers and calls the validation method directly
to isolate where the error is occurring.
"""

import asyncio
import json
from verification.groups.mcp_data_processor_group import (
    MCPDataProcessorGroup,
    SchemaDefinition
)

async def main():
    print("\n=== Direct Validation Test ===")
    
    # Create processor instance
    processor = MCPDataProcessorGroup()
    
    # Create test data and schema
    test_data = "test string"
    test_schema = SchemaDefinition(type="string")
    
    # Test direct method call
    print("\nCalling validation directly with appropriate objects...")
    try:
        # Call the _validate_data_against_schema method directly
        errors = []
        processor._validate_data_against_schema(test_data, test_schema, "", errors)
        if errors:
            print(f"Validation failed with errors: {errors}")
        else:
            print("Validation succeeded!")
    except Exception as e:
        print(f"Error during direct validation: {e}")
        import traceback
        traceback.print_exc()

    # Now try it through the operation method
    print("\nCalling through operation method...")
    try:
        result = await processor.validate_schema(data=test_data, schema=test_schema)
        print(f"Operation result: {result}")
    except Exception as e:
        print(f"Error during operation call: {e}")
        import traceback
        traceback.print_exc()
    
if __name__ == "__main__":
    asyncio.run(main())