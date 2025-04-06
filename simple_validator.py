#!/usr/bin/env python3
"""
Simple validator to interact with MCP tools
"""

from mcp.server.fastmcp import FastMCP, Context
from verification.groups.data_processor_group import (
    DataItem,
    DataProcessingSchema,
    ProcessingParameters,
    ReportFormat,
    ReportGenerationSchema,
    SchemaDefinition,
    SchemaValidationRequestSchema,
    ValidationError,
    ValidationResult,
    DataProcessorGroup
)

# Create a FastMCP server
server = FastMCP("Validator", instructions="A simple validation server")

# Create a data processor group to use its methods
processor = DataProcessorGroup()

@server.tool(name="validate_schema")
def validate_schema(data: any, schema: dict) -> dict:
    """Validate input data against a specified schema.
    
    Args:
        data: The data to validate
        schema: The schema to validate against
        
    Returns:
        dict: The validation result
    """
    # Convert the schema to a SchemaDefinition
    schema_obj = SchemaDefinition(**schema)
    
    # Create error list
    errors = []
    
    # Validate the data against the schema
    try:
        processor._validate_data_against_schema(data, schema_obj, "", errors)
        valid = len(errors) == 0
    except Exception as e:
        errors.append({
            "path": "",
            "message": f"Validation error: {str(e)}"
        })
        valid = False
        
    # Return the result as a dictionary (which MCP can handle)
    return {
        "valid": valid,
        "errors": [{"path": e.path, "message": e.message} for e in errors] if errors else None
    }

@server.tool(name="process_data")
def process_data(data: list, parameters: dict = None) -> dict:
    """Process data items according to specified parameters."""
    # Convert input to proper objects
    data_items = []
    for item_data in data:
        data_items.append(DataItem(**item_data))
        
    params = ProcessingParameters(**(parameters or {}))
    
    # Process the data
    processed_items = []
    
    for item in data_items:
        processed_item = processor._process_item(item, params)
        processed_items.append(processed_item)
        
    # Perform aggregation if requested
    result = {"processed_items": processed_items}
    if params.aggregate:
        result["aggregated"] = processor._aggregate_data(processed_items)
        
    return result

if __name__ == "__main__":
    print("Starting simple validator server...")
    server.run("stdio")