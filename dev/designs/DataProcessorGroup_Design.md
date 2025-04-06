# DataProcessorGroup Design Document

## Overview

The `DataProcessorGroup` is a ServiceGroup for the AutoMCP framework that demonstrates key capabilities including input schema validation, progress reporting, and various data processing operations. This group provides a set of operations for processing JSON data, generating reports, and validating data against schemas.

## ServiceGroup Structure

```python
class DataProcessorGroup(ServiceGroup):
    """Service group for data processing operations.
    
    This group demonstrates:
    1. Pydantic schema validation for inputs
    2. Progress reporting using Context
    3. Multiple operation types for data processing
    """
    
    @operation(schema=DataProcessingSchema)
    async def process_data(self, data: DataProcessingSchema, ctx: Context) -> dict:
        """Process JSON data according to specified parameters.
        
        Args:
            data: A DataProcessingSchema object containing the input data and processing parameters
            ctx: Context object for logging and progress reporting
            
        Returns:
            dict: The processed data
        """
        pass
        
    @operation(schema=ReportGenerationSchema)
    async def generate_report(self, config: ReportGenerationSchema, ctx: Context) -> str:
        """Generate a formatted report from processed data.
        
        Args:
            config: A ReportGenerationSchema object containing the data and report configuration
            ctx: Context object for logging and progress reporting
            
        Returns:
            str: The formatted report as a string
        """
        pass
        
    @operation(schema=SchemaValidationRequestSchema)
    async def validate_schema(self, request: SchemaValidationRequestSchema) -> ValidationResult:
        """Validate input data against a specified schema.
        
        Args:
            request: A SchemaValidationRequestSchema object containing the data and schema to validate against
            
        Returns:
            ValidationResult: The validation result containing success status and any error messages
        """
        pass
```

## Input/Output Schemas

### Data Processing Schemas

```python
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class DataItem(BaseModel):
    """Schema for a single data item with flexible content."""
    id: str = Field(..., description="Unique identifier for the data item")
    value: Any = Field(..., description="The value of the data item")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the data item")

class ProcessingParameters(BaseModel):
    """Schema for data processing parameters."""
    filter_fields: Optional[List[str]] = Field(None, description="Fields to include in the output")
    transform_case: Optional[str] = Field(None, description="Case transformation ('upper', 'lower', or None)")
    aggregate: Optional[bool] = Field(False, description="Whether to aggregate numeric values")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", description="Sort order ('asc' or 'desc')")

class DataProcessingSchema(BaseModel):
    """Schema for data processing operation."""
    data: List[DataItem] = Field(..., description="List of data items to process")
    parameters: ProcessingParameters = Field(
        default_factory=ProcessingParameters,
        description="Parameters for processing the data"
    )
```

### Report Generation Schemas

```python
class ReportFormat(BaseModel):
    """Schema for report formatting options."""
    title: str = Field("Data Processing Report", description="Title of the report")
    include_summary: bool = Field(True, description="Whether to include a summary section")
    include_timestamp: bool = Field(True, description="Whether to include a timestamp")
    format_type: str = Field("text", description="Output format type ('text', 'markdown', 'html')")
    
class ReportGenerationSchema(BaseModel):
    """Schema for report generation operation."""
    processed_data: Dict[str, Any] = Field(..., description="The processed data to generate a report for")
    format: ReportFormat = Field(
        default_factory=ReportFormat,
        description="Formatting options for the report"
    )
```

### Schema Validation Schemas

```python
class SchemaDefinition(BaseModel):
    """Schema for defining a validation schema."""
    type: str = Field(..., description="Schema type (e.g., 'object', 'array', 'string')")
    properties: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Properties for object types")
    required: Optional[List[str]] = Field(None, description="Required properties for object types")
    items: Optional[Dict[str, Any]] = Field(None, description="Schema for array items")
    format: Optional[str] = Field(None, description="Format for string types")
    minimum: Optional[float] = Field(None, description="Minimum value for number types")
    maximum: Optional[float] = Field(None, description="Maximum value for number types")
    pattern: Optional[str] = Field(None, description="Regex pattern for string types")
    
class SchemaValidationRequestSchema(BaseModel):
    """Schema for schema validation operation."""
    data: Any = Field(..., description="The data to validate")
    schema: SchemaDefinition = Field(..., description="The schema to validate against")

class ValidationError(BaseModel):
    """Schema for validation error details."""
    path: str = Field(..., description="Path to the error location in the data")
    message: str = Field(..., description="Error message")
    
class ValidationResult(BaseModel):
    """Schema for validation result."""
    valid: bool = Field(..., description="Whether the data is valid against the schema")
    errors: Optional[List[ValidationError]] = Field(None, description="List of validation errors if any")
```

## Context Usage

The `DataProcessorGroup` uses the `mcp.server.fastmcp.Context` object for two main purposes:

1. **Progress Reporting**: For long-running operations like data processing and report generation, the group uses `ctx.report_progress(current, total)` to provide real-time feedback on the operation's progress.

2. **Logging**: The group uses `ctx.info()` to log important information about the operation, such as the start and completion of processing steps.

Example context usage in the `process_data` operation:

```python
@operation(schema=DataProcessingSchema)
async def process_data(self, data: DataProcessingSchema, ctx: Context) -> dict:
    """Process JSON data according to specified parameters."""
    ctx.info(f"Processing {len(data.data)} data items with parameters: {data.parameters}")
    
    processed_items = []
    total_items = len(data.data)
    
    for i, item in enumerate(data.data):
        # Report progress
        await ctx.report_progress(i + 1, total_items)
        
        # Process the item (implementation details)
        processed_item = self._process_item(item, data.parameters)
        processed_items.append(processed_item)
    
    ctx.info("Data processing completed successfully")
    return {"processed_items": processed_items}
```

## Implementation Considerations

1. **Error Handling**:
   - All operations should include robust error handling
   - Validation errors should be clearly reported
   - Processing errors should be caught and reported with context

2. **Performance**:
   - For large data sets, consider implementing batched processing
   - Use efficient data structures for processing
   - Consider memory usage when handling large data sets

3. **Extensibility**:
   - The schema designs should allow for future extensions
   - Processing parameters should be easily extensible
   - Report formats should be extensible to support additional output types

4. **Testing**:
   - Unit tests should cover all operations
   - Test with various data types and sizes
   - Test error conditions and edge cases

## Configuration

The configuration file (YAML or JSON) for the DataProcessorGroup would look like:

### As part of a multi-group service (YAML):

```yaml
name: data-processing-service
description: Service for data processing operations
packages:
  - pydantic>=2.0.0
groups:
  "path.to.module:DataProcessorGroup":
    name: data-processor
    description: Group for data processing operations
    config:
      default_processing:
        filter_fields: null
        transform_case: null
        aggregate: false
        sort_by: null
        sort_order: "asc"
      default_report_format:
        title: "Data Processing Report"
        include_summary: true
        include_timestamp: true
        format_type: "text"
```

### As a single group (JSON):

```json
{
  "name": "data-processor",
  "description": "Group for data processing operations",
  "config": {
    "default_processing": {
      "filter_fields": null,
      "transform_case": null,
      "aggregate": false,
      "sort_by": null,
      "sort_order": "asc"
    },
    "default_report_format": {
      "title": "Data Processing Report",
      "include_summary": true,
      "include_timestamp": true,
      "format_type": "text"
    }
  }
}
```

## Conclusion

The `DataProcessorGroup` demonstrates key capabilities of the AutoMCP framework, including input validation with Pydantic schemas, progress reporting using Context, and multiple operation types for data processing. The design provides a clear structure for implementing data processing operations with a focus on validation, progress reporting, and flexibility.