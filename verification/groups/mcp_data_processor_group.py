"""MCP-compatible Data Processor Group for AutoMCP."""

import datetime
from typing import Any, Dict, List, Optional, Union

from mcp.types import TextContent as Context
from pydantic import BaseModel, Field

from automcp.group import MockContext, ServiceGroup
from automcp.operation import operation
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
)


class MCPDataProcessorGroup(ServiceGroup):
    """MCP-compatible version of DataProcessorGroup.
    
    This class is designed to handle the MCP protocol format, which passes arguments
    as keyword arguments rather than positional arguments.
    """

    def __init__(self):
        """Initialize the MCP Data Processor Group."""
        super().__init__()
        self.config = {
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

    @operation(schema=SchemaValidationRequestSchema)
    async def validate_schema(self, *args, **kwargs) -> ValidationResult:
        """Validate input data against a specified schema.
        
        This version handles both positional and keyword arguments to be maximally compatible.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            ValidationResult: The validation result
        """
        print(f"DEBUG: validate_schema called with args={args}, kwargs={kwargs}")
        
        # Extract data and schema from arguments
        data = None
        schema = None
        
        # Case 1: Called with positional schema arg (from operation decorator)
        if len(args) > 0 and hasattr(args[0], 'data') and hasattr(args[0], 'schema'):
            data = args[0].data
            schema = args[0].schema
        # Case 2: Called with separate keyword args (from MCP)
        elif 'data' in kwargs or 'schema' in kwargs:
            data = kwargs.get('data')
            schema_dict = kwargs.get('schema')
            if isinstance(schema_dict, dict):
                schema = SchemaDefinition(**schema_dict)
            else:
                schema = schema_dict
        # Case 3: Called with a 'request' parameter
        elif 'request' in kwargs and hasattr(kwargs['request'], 'data') and hasattr(kwargs['request'], 'schema'):
            data = kwargs['request'].data
            schema = kwargs['request'].schema

        # Validate the data
        errors = []
        try:
            # Make sure schema is a SchemaDefinition before validating
            schema_obj = None
            if isinstance(schema, SchemaDefinition):
                schema_obj = schema
            elif isinstance(schema, dict):
                schema_obj = SchemaDefinition(**schema)
            else:
                # If we got a SchemaValidationRequestSchema, extract schema from it
                if hasattr(schema, 'schema'):
                    schema_obj = schema.schema
                else:
                    # Create a simple string schema as fallback
                    schema_obj = SchemaDefinition(type="string")
            
            # Do the validation with proper schema object
            self._validate_data_against_schema(data, schema_obj, "", errors)
            valid = len(errors) == 0
        except Exception as e:
            errors.append(ValidationError(path="", message=f"Validation error: {str(e)}"))
            valid = False

        return ValidationResult(valid=valid, errors=errors if errors else None)

    @operation(schema=DataProcessingSchema)
    async def process_data(self, *args, **kwargs) -> dict:
        """Process JSON data according to specified parameters.
        
        This version handles both positional and keyword arguments for maximum compatibility.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            dict: The processed data
        """
        print(f"DEBUG: process_data called with args={args}, kwargs={kwargs}")
        
        # Extract data and parameters from arguments
        data = None
        parameters = None
        
        # Case 1: Called with positional schema arg (from operation decorator)
        if len(args) > 0 and hasattr(args[0], 'data') and hasattr(args[0], 'parameters'):
            data = args[0].data
            parameters = args[0].parameters
        # Case 2: Called with separate keyword args (from MCP)
        elif 'data' in kwargs or 'parameters' in kwargs:
            data = kwargs.get('data', [])
            parameters_dict = kwargs.get('parameters', {})
            if isinstance(parameters_dict, dict):
                parameters = ProcessingParameters(**parameters_dict)
            else:
                parameters = parameters_dict
        # Case 3: Called with a 'data_schema' parameter
        elif 'data_schema' in kwargs and hasattr(kwargs['data_schema'], 'data') and hasattr(kwargs['data_schema'], 'parameters'):
            data = kwargs['data_schema'].data
            parameters = kwargs['data_schema'].parameters
        
        # Convert data to DataItem objects if needed
        data_items = []
        if data:
            for item in data:
                if isinstance(item, dict):
                    data_items.append(DataItem(**item))
                else:
                    data_items.append(item)
        
        # Convert parameters to ProcessingParameters if needed
        if isinstance(parameters, dict):
            params = ProcessingParameters(**parameters)
        else:
            params = parameters or ProcessingParameters()
        
        # Create a context for progress reporting
        ctx = MockContext()
        ctx.info(f"Processing {len(data_items)} data items with parameters: {params}")
        
        # Process the data
        processed_items = []
        total_items = len(data_items)
        
        for i, item in enumerate(data_items):
            # Report progress
            await ctx.report_progress(i + 1, total_items)
            
            # Process the item
            processed_item = self._process_item(item, params)
            processed_items.append(processed_item)
        
        # Perform aggregation if requested
        result = {"processed_items": processed_items}
        if params.aggregate:
            result["aggregated"] = self._aggregate_data(processed_items)
        
        ctx.info("Data processing completed successfully")
        return result

    @operation(schema=ReportGenerationSchema)
    async def generate_report(self, *args, **kwargs) -> str:
        """Generate a formatted report from processed data.
        
        This version handles both positional and keyword arguments for maximum compatibility.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            str: The formatted report as a string
        """
        print(f"DEBUG: generate_report called with args={args}, kwargs={kwargs}")
        
        # Extract processed_data and format from arguments
        processed_data = None
        format_data = None
        
        # Case 1: Called with positional schema arg (from operation decorator)
        if len(args) > 0 and hasattr(args[0], 'processed_data') and hasattr(args[0], 'format'):
            processed_data = args[0].processed_data
            format_data = args[0].format
        # Case 2: Called with separate keyword args (from MCP)
        elif 'processed_data' in kwargs or 'format' in kwargs:
            processed_data = kwargs.get('processed_data', {})
            format_dict = kwargs.get('format', {})
            if isinstance(format_dict, dict):
                format_data = ReportFormat(**format_dict)
            else:
                format_data = format_dict
        # Case 3: Called with a 'config' parameter
        elif 'config' in kwargs and hasattr(kwargs['config'], 'processed_data') and hasattr(kwargs['config'], 'format'):
            processed_data = kwargs['config'].processed_data
            format_data = kwargs['config'].format
        
        # Ensure we have valid objects
        if not format_data:
            format_data = ReportFormat()
        if not processed_data:
            processed_data = {}
            
        # Create a context for progress reporting
        ctx = MockContext()
        ctx.info(f"Generating report with format: {format_data}")
        
        # Extract data from processed_data
        processed_items = processed_data.get("processed_items", [])
        aggregated_data = processed_data.get("aggregated", {})
        
        # Start building the report
        await ctx.report_progress(1, 3)
        report_lines = []
        
        # Generate report based on format type
        format_type = format_data.format_type.lower()
        
        # Add title
        if format_type == "markdown":
            report_lines.append(f"# {format_data.title}")
            report_lines.append("")
        elif format_type == "html":
            report_lines.append(f"<h1>{format_data.title}</h1>")
        else:  # text
            report_lines.append(format_data.title)
            report_lines.append("=" * len(format_data.title))
        
        # Add timestamp if requested
        if format_data.include_timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if format_type == "markdown":
                report_lines.append(f"**Generated:** {timestamp}")
                report_lines.append("")
            elif format_type == "html":
                report_lines.append(f"<p><strong>Generated:</strong> {timestamp}</p>")
            else:  # text
                report_lines.append(f"Generated: {timestamp}")
                report_lines.append("")
        
        await ctx.report_progress(2, 3)
        
        # Add summary if requested
        if format_data.include_summary and processed_items:
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
        
        # Add data items
        if processed_items:
            if format_type == "markdown":
                report_lines.append("## Data Items")
                report_lines.append("")
                for item in processed_items:
                    report_lines.append(f"### Item: {item.get('id')}")
                    report_lines.append(f"- **Value:** {item.get('value')}")
                    if "metadata" in item and item["metadata"]:
                        report_lines.append("- **Metadata:**")
                        for meta_key, meta_value in item["metadata"].items():
                            report_lines.append(f"  - {meta_key}: {meta_value}")
                    report_lines.append("")
            elif format_type == "html":
                report_lines.append("<h2>Data Items</h2>")
                for item in processed_items:
                    report_lines.append(f"<div class='item'>")
                    report_lines.append(f"<h3>Item: {item.get('id')}</h3>")
                    report_lines.append(f"<p><strong>Value:</strong> {item.get('value')}</p>")
                    if "metadata" in item and item["metadata"]:
                        report_lines.append("<div class='metadata'>")
                        report_lines.append("<p><strong>Metadata:</strong></p>")
                        report_lines.append("<ul>")
                        for meta_key, meta_value in item["metadata"].items():
                            report_lines.append(f"<li>{meta_key}: {meta_value}</li>")
                        report_lines.append("</ul>")
                        report_lines.append("</div>")
                    report_lines.append("</div>")
            else:  # text
                report_lines.append("Data Items")
                report_lines.append("---------")
                for item in processed_items:
                    report_lines.append(f"Item: {item.get('id')}")
                    report_lines.append(f"Value: {item.get('value')}")
                    if "metadata" in item and item["metadata"]:
                        report_lines.append("Metadata:")
                        for meta_key, meta_value in item["metadata"].items():
                            report_lines.append(f"  {meta_key}: {meta_value}")
                    report_lines.append("")
        
        await ctx.report_progress(3, 3)
        ctx.info("Report generation completed successfully")
        
        # Join report lines based on format
        separator = "\n" if format_type != "html" else ""
        return separator.join(report_lines)

    # Helper methods copied from DataProcessorGroup
    def _process_item(
        self, item: DataItem, params: ProcessingParameters
    ) -> Dict[str, Any]:
        """Process a single data item according to the parameters."""
        processed = {"id": item.id}

        # Add value with possible transformation
        if isinstance(item.value, str) and params.transform_case:
            if params.transform_case.lower() == "upper":
                processed["value"] = item.value.upper()
            elif params.transform_case.lower() == "lower":
                processed["value"] = item.value.lower()
            else:
                processed["value"] = item.value
        else:
            processed["value"] = item.value

        # Add metadata if present
        if item.metadata:
            if params.filter_fields:
                # Only include specified fields
                filtered_metadata = {
                    k: v for k, v in item.metadata.items() if k in params.filter_fields
                }
                processed["metadata"] = filtered_metadata
            else:
                processed["metadata"] = item.metadata

        return processed

    def _aggregate_data(self, processed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate numeric values in the processed data."""
        numeric_values = []
        for item in processed_items:
            if isinstance(item["value"], (int, float)):
                numeric_values.append(item["value"])

        if not numeric_values:
            return {}

        return {
            "count": len(numeric_values),
            "sum": sum(numeric_values),
            "average": sum(numeric_values) / len(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values),
        }

    def _validate_data_against_schema(
        self,
        data: Any,
        schema: SchemaDefinition,
        path: str,
        errors: List[ValidationError],
    ) -> None:
        """Recursively validate data against a schema definition."""
        # Check type
        schema_type = schema.type.lower()

        if schema_type == "object":
            if not isinstance(data, dict):
                errors.append(
                    ValidationError(
                        path=path, message=f"Expected object, got {type(data).__name__}"
                    )
                )
                return

            # Check required properties
            if schema.required:
                for required_prop in schema.required:
                    if required_prop not in data:
                        errors.append(
                            ValidationError(
                                path=(
                                    f"{path}.{required_prop}" if path else required_prop
                                ),
                                message=f"Required property '{required_prop}' is missing",
                            )
                        )

            # Validate properties
            if schema.properties:
                for prop_name, prop_schema in schema.properties.items():
                    if prop_name in data:
                        prop_path = f"{path}.{prop_name}" if path else prop_name
                        # Create a SchemaDefinition from the property schema
                        prop_schema_def = SchemaDefinition(**prop_schema)
                        self._validate_data_against_schema(
                            data[prop_name], prop_schema_def, prop_path, errors
                        )

        elif schema_type == "array":
            if not isinstance(data, list):
                errors.append(
                    ValidationError(
                        path=path, message=f"Expected array, got {type(data).__name__}"
                    )
                )
                return

            # Validate array items
            if schema.items:
                items_schema = SchemaDefinition(**schema.items)
                for i, item in enumerate(data):
                    item_path = f"{path}[{i}]" if path else f"[{i}]"
                    self._validate_data_against_schema(
                        item, items_schema, item_path, errors
                    )

        elif schema_type == "string":
            if not isinstance(data, str):
                errors.append(
                    ValidationError(
                        path=path, message=f"Expected string, got {type(data).__name__}"
                    )
                )
                return

            # Validate format
            if schema.format == "email" and "@" not in data:
                errors.append(
                    ValidationError(path=path, message="Invalid email format")
                )

            # Validate pattern
            if schema.pattern and not self._matches_pattern(data, schema.pattern):
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"String does not match pattern: {schema.pattern}",
                    )
                )

        elif schema_type in ["number", "integer"]:
            if not isinstance(data, (int, float)):
                errors.append(
                    ValidationError(
                        path=path, message=f"Expected number, got {type(data).__name__}"
                    )
                )
                return

            if schema_type == "integer" and not isinstance(data, int):
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Expected integer, got {type(data).__name__}",
                    )
                )
                return

            # Validate minimum
            if schema.minimum is not None and data < schema.minimum:
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Value {data} is less than minimum {schema.minimum}",
                    )
                )

            # Validate maximum
            if schema.maximum is not None and data > schema.maximum:
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Value {data} is greater than maximum {schema.maximum}",
                    )
                )

        elif schema_type == "boolean":
            if not isinstance(data, bool):
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Expected boolean, got {type(data).__name__}",
                    )
                )

        elif schema_type == "null":
            if data is not None:
                errors.append(
                    ValidationError(
                        path=path, message=f"Expected null, got {type(data).__name__}"
                    )
                )

    def _matches_pattern(self, data: str, pattern: str) -> bool:
        """Simple pattern matching for string validation."""
        import re

        try:
            return bool(re.match(pattern, data))
        except Exception:
            return False