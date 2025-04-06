#!/usr/bin/env python3
"""
MCP Data Processor Wrapper

This script creates a proper MCP server that wraps the existing data processor functionality.
It follows the MCP protocol standards and properly handles the tool call interface.
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
    ValidationResult,
    DataProcessorGroup
)

# Create FastMCP server
server = FastMCP("Data Processor", 
                 instructions="A server for data processing, schema validation, and report generation")

# Create an instance of the data processor group
data_processor = DataProcessorGroup()

# Define validate_schema tool that properly adapts to MCP protocol
@server.tool(name="validate_schema")
async def validate_schema(data: any, schema: dict) -> ValidationResult:
    """Validate input data against a specified schema.
    
    Args:
        data: The data to validate
        schema: The schema to validate against
        
    Returns:
        ValidationResult: The validation result
    """
    # Create a schema validation request
    schema_obj = SchemaDefinition(**schema)
    request = SchemaValidationRequestSchema(data=data, schema=schema_obj)
    
    # Call the original method
    errors = []
    
    # Validate the data against the schema
    try:
        data_processor._validate_data_against_schema(request.data, request.schema, "", errors)
        valid = len(errors) == 0
    except Exception as e:
        errors.append({
            "path": "",
            "message": f"Validation error: {str(e)}"
        })
        valid = False
        
    return {"valid": valid, "errors": errors if errors else None}

# Define process_data tool
@server.tool(name="process_data")
async def process_data(data: list, parameters: dict = None) -> dict:
    """Process JSON data according to specified parameters.
    
    Args:
        data: List of data items to process
        parameters: Parameters for processing the data
        
    Returns:
        dict: The processed data
    """
    # Convert input to proper objects
    data_items = []
    for item_data in data:
        data_items.append(DataItem(**item_data))
        
    params = ProcessingParameters(**(parameters or {}))
    
    # Process the data
    processed_items = []
    
    for item in data_items:
        processed_item = data_processor._process_item(item, params)
        processed_items.append(processed_item)
        
    # Perform aggregation if requested
    result = {"processed_items": processed_items}
    if params.aggregate:
        result["aggregated"] = data_processor._aggregate_data(processed_items)
        
    return result

# Define generate_report tool
@server.tool(name="generate_report")
async def generate_report(processed_data: dict, format: dict = None) -> str:
    """Generate a formatted report from processed data.
    
    Args:
        processed_data: The processed data to generate a report for
        format: Formatting options for the report
        
    Returns:
        str: The formatted report as a string
    """
    # Create a report format object
    report_format = ReportFormat(**(format or {}))
    
    # Create a schema object
    report_schema = ReportGenerationSchema(
        processed_data=processed_data,
        format=report_format
    )
    
    # Use the processor's helper methods directly
    import datetime
    
    # Extract data from processed_data
    processed_items = processed_data.get("processed_items", [])
    aggregated_data = processed_data.get("aggregated", {})
    
    # Start building the report
    report_lines = []
    
    # Generate report based on format type
    format_type = report_format.format_type.lower()
    
    # Add title
    if format_type == "markdown":
        report_lines.append(f"# {report_format.title}")
        report_lines.append("")
    elif format_type == "html":
        report_lines.append(f"<h1>{report_format.title}</h1>")
    else:  # text
        report_lines.append(report_format.title)
        report_lines.append("=" * len(report_format.title))
        
    # Add timestamp if requested
    if report_format.include_timestamp:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if format_type == "markdown":
            report_lines.append(f"**Generated:** {timestamp}")
            report_lines.append("")
        elif format_type == "html":
            report_lines.append(f"<p><strong>Generated:</strong> {timestamp}</p>")
        else:  # text
            report_lines.append(f"Generated: {timestamp}")
            report_lines.append("")
            
    # Add summary if requested
    if report_format.include_summary and processed_items:
        if format_type == "markdown":
            report_lines.append("## Summary")
            report_lines.append("")
            report_lines.append(f"**Total items:** {len(processed_items)}")
            if aggregated_data:
                report_lines.append("")
                report_lines.append("### Aggregated Data")
                report_lines.append("")
                for key, value in aggregated_data.items():
                    report_lines.append(f"- **{key}:** {value}")
            report_lines.append("")
        elif format_type == "html":
            report_lines.append("<h2>Summary</h2>")
            report_lines.append(f"<p><strong>Total items:</strong> {len(processed_items)}</p>")
            if aggregated_data:
                report_lines.append("<h3>Aggregated Data</h3>")
                report_lines.append("<ul>")
                for key, value in aggregated_data.items():
                    report_lines.append(f"<li><strong>{key}:</strong> {value}</li>")
                report_lines.append("</ul>")
        else:  # text
            report_lines.append("Summary")
            report_lines.append("-------")
            report_lines.append(f"Total items: {len(processed_items)}")
            if aggregated_data:
                report_lines.append("")
                report_lines.append("Aggregated Data:")
                for key, value in aggregated_data.items():
                    report_lines.append(f"  {key}: {value}")
            report_lines.append("")
            
    # Join report lines based on format
    separator = "\n" if format_type != "html" else ""
    return separator.join(report_lines)

if __name__ == "__main__":
    print("Starting Data Processor MCP Server...")
    server.run("stdio")