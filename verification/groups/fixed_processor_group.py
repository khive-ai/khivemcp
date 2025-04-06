"""Fixed DataProcessor service group implementation for AutoMCP verification."""

import datetime
import json
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


class FixedDataProcessorGroup(ServiceGroup):
    """Fixed version of DataProcessorGroup that handles MCP protocol correctly.
    
    This version is modified to handle the keyword arguments as they come in
    from the MCP protocol, rather than expecting positional arguments.
    """

    @operation(schema=DataProcessingSchema)
    async def process_data(self, **kwargs) -> dict:
        """Process JSON data according to specified parameters.

        Args:
            **kwargs: Keyword arguments that will be converted to a DataProcessingSchema

        Returns:
            dict: The processed data
        """
        # Create a schema from the keyword arguments
        data_items = []
        for item_data in kwargs.get("data", []):
            if isinstance(item_data, dict):
                data_items.append(DataItem(**item_data))
            else:
                data_items.append(item_data)
                
        parameters = kwargs.get("parameters", {})
        if isinstance(parameters, dict):
            parameters = ProcessingParameters(**parameters)
            
        # Create the schema object
        data_schema = DataProcessingSchema(data=data_items, parameters=parameters)
        
        # Create a context for progress reporting
        ctx = MockContext()
        ctx.info(
            f"Processing {len(data_schema.data)} data items with parameters: {data_schema.parameters}"
        )

        # Process the data
        processed_items = []
        total_items = len(data_schema.data)

        for i, item in enumerate(data_schema.data):
            # Report progress
            await ctx.report_progress(i + 1, total_items)

            # Process the item
            processed_item = self._process_item(item, data_schema.parameters)
            processed_items.append(processed_item)

        # Perform aggregation if requested
        result = {"processed_items": processed_items}
        if data_schema.parameters.aggregate:
            result["aggregated"] = self._aggregate_data(processed_items)

        ctx.info("Data processing completed successfully")
        return result
        
    @operation(schema=ReportGenerationSchema)
    async def generate_report(self, **kwargs) -> str:
        """Generate a formatted report from processed data.

        Args:
            **kwargs: Keyword arguments that will be converted to a ReportGenerationSchema

        Returns:
            str: The formatted report as a string
        """
        # Create a schema from the keyword arguments
        processed_data = kwargs.get("processed_data", {})
        format_data = kwargs.get("format", {})
        if isinstance(format_data, dict):
            format_data = ReportFormat(**format_data)
            
        # Create the schema object
        report_schema = ReportGenerationSchema(processed_data=processed_data, format=format_data)
        
        # Create a context for progress reporting
        ctx = MockContext()
        ctx.info(f"Generating report with format: {report_schema.format}")

        # Extract data from processed_data
        processed_items = report_schema.processed_data.get("processed_items", [])
        aggregated_data = report_schema.processed_data.get("aggregated", {})

        # Start building the report
        await ctx.report_progress(1, 3)
        report_lines = []

        # Generate report based on format type
        format_type = report_schema.format.format_type.lower()

        # Add title
        if format_type == "markdown":
            report_lines.append(f"# {report_schema.format.title}")
            report_lines.append("")
        elif format_type == "html":
            report_lines.append(f"<h1>{report_schema.format.title}</h1>")
        else:  # text
            report_lines.append(report_schema.format.title)
            report_lines.append("=" * len(report_schema.format.title))

        # Add timestamp if requested
        if report_schema.format.include_timestamp:
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
        if report_schema.format.include_summary and processed_items:
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
                report_lines.append(
                    f"<p><strong>Total items:</strong> {len(processed_items)}</p>"
                )
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
                    report_lines.append(
                        f"<p><strong>Value:</strong> {item.get('value')}</p>"
                    )
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

    @operation(schema=SchemaValidationRequestSchema)
    async def validate_schema(self, **kwargs) -> ValidationResult:
        """Validate input data against a specified schema.

        Args:
            **kwargs: Keyword arguments that will be converted to a SchemaValidationRequestSchema

        Returns:
            ValidationResult: The validation result containing success status and any error messages
        """
        # Create a schema from the keyword arguments
        data = kwargs.get("data")
        schema_dict = kwargs.get("schema", {})
        if isinstance(schema_dict, dict):
            schema_obj = SchemaDefinition(**schema_dict)
            
        # Create the schema object
        request = SchemaValidationRequestSchema(data=data, schema=schema_obj)
        
        errors = []

        # Validate the data against the schema
        try:
            self._validate_data_against_schema(request.data, request.schema, "", errors)
            valid = len(errors) == 0
        except Exception as e:
            errors.append(
                ValidationError(path="", message=f"Validation error: {str(e)}")
            )
            valid = False

        return ValidationResult(valid=valid, errors=errors if errors else None)
        
    # Copy the helper methods from the original DataProcessorGroup
    
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