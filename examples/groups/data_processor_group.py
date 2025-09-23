"""Data processor service group implementation - Using khiveMCP wrappers."""

import datetime
import json
import re
import sys
from typing import Any

from pydantic import BaseModel, Field

from khivemcp.decorators import operation
from khivemcp.types import ServiceGroup


# --- Pydantic Schemas (Copied from previous example for completeness) ---
class DataItem(BaseModel):
    id: str
    value: Any
    metadata: dict[str, Any] | None = None


class ProcessingParameters(BaseModel):
    filter_fields: list[str] | None = None
    transform_case: str | None = None
    aggregate: bool | None = False
    sort_by: str | None = None
    sort_order: str | None = "asc"


class DataProcessingSchema(BaseModel):
    data: list[DataItem]
    parameters: ProcessingParameters = Field(default_factory=ProcessingParameters)


class ReportFormat(BaseModel):
    title: str = "Data Processing Report"
    include_summary: bool = True
    include_timestamp: bool = True
    format_type: str = "text"


class ReportGenerationSchema(BaseModel):
    processed_data: dict[str, Any]
    format: ReportFormat = Field(default_factory=ReportFormat)


class SchemaDefinition(BaseModel):
    type: str
    properties: dict[str, dict[str, Any]] | None = None
    required: list[str] | None = None
    items: dict[str, Any] | None = None
    format: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None


class SchemaValidationRequestSchema(BaseModel):
    data: Any
    schema_def: SchemaDefinition = Field(..., alias="schema")

    class Config:
        allow_population_by_field_name = True


class ValidationError(BaseModel):
    path: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationError] | None = None


class ErrorTestSchema(BaseModel):
    error_type: str = Field(
        ...,
        description="Type of error to raise",
        examples=[
            "value_error",
            "type_error",
            "key_error",
            "index_error",
            "runtime_error",
            "assertion_error",
        ],
    )


# --- Service Group Class ---
class DataProcessorGroup(ServiceGroup):
    """Service group using khiveMCP decorators and context."""

    def __init__(self, config: dict | None = None):
        """Initialize the group. Optionally accepts config from khiveMCP."""
        super().__init__(config=config)

        print(
            f"[DataProcessorGroup] Initialized with config: {self.group_config}",
            file=sys.stderr,
        )

    # --- Tool Methods ---

    @operation(
        name="process_data",
        schema=DataProcessingSchema,
    )
    async def process_data(self, *, request: DataProcessingSchema) -> dict:
        """Process JSON data according to specified parameters"""
        processed_items = []
        total_items = len(request.data)

        max_items = self.group_config.get("max_items_per_request", float("inf"))
        if total_items > max_items:
            # Return an error structure or raise an exception that FastMCP can handle
            # For now, returning an empty dict with error info might be one way
            return {"error": f"Exceeded max items limit ({max_items})"}

        for i, item in enumerate(request.data):
            try:
                processed_item = self._process_item(item, request.parameters)
                processed_items.append(processed_item)
            except Exception as e:
                pass
            if (
                i + 1
            ) % 10 == 0 or i == total_items - 1:  # Update progress periodically
                pass

        result = {"processed_items": processed_items}
        if request.parameters.aggregate:
            try:
                result["aggregated"] = self._aggregate_data(processed_items)
            except Exception as e:
                pass
        return result

    @operation(
        name="generate_report",
        schema=ReportGenerationSchema,
    )
    async def generate_report(self, *, request: ReportGenerationSchema) -> str:
        """Generate a formatted report from processed data."""
        report_format_config = request.format
        format_type = report_format_config.format_type.lower()
        default_format = self.group_config.get("default_report_format", "text")
        if format_type not in ["text", "markdown", "html"]:
            format_type = default_format

        processed_items = request.processed_data.get("processed_items", [])
        aggregated_data = request.processed_data.get("aggregated", {})
        report_lines = []

        # 1. Title
        title = report_format_config.title
        if format_type == "markdown":
            report_lines.extend([f"# {title}", ""])
        elif format_type == "html":
            report_lines.append(f"<h1>{title}</h1>")
        else:
            report_lines.extend([title, "=" * len(title), ""])

        # 2. Timestamp
        if report_format_config.include_timestamp:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            if format_type == "markdown":
                report_lines.extend([f"**Generated:** {ts}", ""])
            elif format_type == "html":
                report_lines.append(f"<p><strong>Generated:</strong> {ts}</p>")
            else:
                report_lines.extend([f"Generated: {ts}", ""])

        # 3. Summary
        if report_format_config.include_summary and processed_items:
            total_items_str = f"Total items: {len(processed_items)}"
            if format_type == "markdown":
                report_lines.extend(["## Summary", "", f"**{total_items_str}**", ""])
                if aggregated_data:
                    report_lines.extend(["### Aggregated Data", ""])
                    for k, v in aggregated_data.items():
                        report_lines.append(f"- **{k.capitalize()}:** {v}")
                    report_lines.append("")
            elif format_type == "html":
                report_lines.append("<h2>Summary</h2>")
                report_lines.append(f"<p><strong>{total_items_str}</strong></p>")
                if aggregated_data:
                    report_lines.append("<h3>Aggregated Data</h3><ul>")
                    for k, v in aggregated_data.items():
                        report_lines.append(
                            f"<li><strong>{k.capitalize()}:</strong> {v}</li>"
                        )
                    report_lines.append("</ul>")
            else:  # text
                report_lines.extend(["Summary", "-------", total_items_str, ""])
                if aggregated_data:
                    report_lines.append("Aggregated Data:")
                    for k, v in aggregated_data.items():
                        report_lines.append(f"  {k.capitalize()}: {v}")
                    report_lines.append("")

        # 4. Data Items
        if processed_items:
            if format_type == "markdown":
                report_lines.extend(["## Data Items", ""])
                for item in processed_items:
                    report_lines.append(f"### Item ID: {item.get('id', 'N/A')}")
                    report_lines.append(
                        f"- **Value:** `{json.dumps(item.get('value'))}`"
                    )
                    if item.get("metadata"):
                        report_lines.append("- **Metadata:**")
                        for k, v in item["metadata"].items():
                            report_lines.append(f"  - `{k}`: `{json.dumps(v)}`")
                    report_lines.append("")
            elif format_type == "html":
                report_lines.append("<h2>Data Items</h2>")
                for item in processed_items:
                    report_lines.append(
                        "<div style='border:1px solid #ccc; margin-bottom:10px; padding:10px;'>"
                    )
                    report_lines.append(f"<h3>Item ID: {item.get('id', 'N/A')}</h3>")
                    report_lines.append(
                        f"<p><strong>Value:</strong> <code>{json.dumps(item.get('value'))}</code></p>"
                    )
                    if item.get("metadata"):
                        report_lines.append("<p><strong>Metadata:</strong></p><ul>")
                        for k, v in item["metadata"].items():
                            report_lines.append(
                                f"<li><code>{k}</code>: <code>{json.dumps(v)}</code></li>"
                            )
                        report_lines.append("</ul>")
                    report_lines.append("</div>")
            else:  # text
                report_lines.extend(["Data Items", "----------", ""])
                for item in processed_items:
                    report_lines.append(f"Item ID: {item.get('id', 'N/A')}")
                    report_lines.append(f"  Value: {json.dumps(item.get('value'))}")
                    if item.get("metadata"):
                        report_lines.append("  Metadata:")
                        for k, v in item["metadata"].items():
                            report_lines.append(f"    {k}: {json.dumps(v)}")
                    report_lines.append("")  # Blank line between items
        separator = "\n"
        # HTML needs careful joining, maybe wrap in basic HTML structure?
        if format_type == "html":
            return f"<!DOCTYPE html><html><head><title>{report_format_config.title}</title></head><body>{''.join(report_lines)}</body></html>"

        return separator.join(report_lines)

    @operation(
        name="validate_schema",
        description="Validate input data against a specified schema.",
        schema=SchemaValidationRequestSchema,
    )
    async def validate_schema(
        self, *, request: SchemaValidationRequestSchema
    ) -> ValidationResult:
        """Validate input data against a specified schema."""

        errors: list[ValidationError] = []
        valid = False
        try:
            self._validate_data_against_schema(
                request.data, request.schema_def, "", errors
            )
            valid = len(errors) == 0
        except Exception as e:
            errors.append(
                ValidationError(
                    path="", message=f"Internal validation error: {type(e).__name__}"
                )
            )
            valid = False

        return ValidationResult(valid=valid, errors=errors if errors else None)

    @operation(
        name="test_error",
        description="Test operation that raises different types of errors based on input.",
        schema=ErrorTestSchema,
    )
    async def test_error(self, *, request: ErrorTestSchema) -> dict:
        """
        Test operation that raises different types of errors based on input.

        Args:
            request: Schema containing the error type to raise. Options:
                - "value_error": Raises ValueError
                - "type_error": Raises TypeError
                - "key_error": Raises KeyError
                - "index_error": Raises IndexError
                - "runtime_error": Raises RuntimeError
                - "assertion_error": Raises AssertionError

        Returns:
            A dictionary with the result if no error is raised

        Raises:
            Various exceptions based on error_type
        """
        error_type = request.error_type

        if error_type == "value_error":
            raise ValueError("Intentional test error: ValueError")
        elif error_type == "type_error":
            raise TypeError("Intentional test error: TypeError")
        elif error_type == "key_error":
            empty_dict = {}
            # This will raise KeyError
            return {"result": empty_dict["nonexistent_key"]}
        elif error_type == "index_error":
            empty_list = []
            # This will raise IndexError
            return {"result": empty_list[10]}
        elif error_type == "runtime_error":
            raise RuntimeError("Intentional test error: RuntimeError")
        elif error_type == "assertion_error":
            assert False, "Intentional test error: AssertionError"
        else:
            return {"result": f"Unknown error_type: {error_type}"}

    # --- Helper Methods (Keep as they were, ensure they are correct) ---
    def _process_item(
        self, item: DataItem, params: ProcessingParameters
    ) -> dict[str, Any]:
        """Process a single data item."""
        processed = {"id": item.id}
        value = item.value
        if isinstance(value, str) and params.transform_case:
            case = params.transform_case.lower()
            value = (
                value.upper()
                if case == "upper"
                else (value.lower() if case == "lower" else value)
            )
        processed["value"] = value

        if item.metadata:
            if params.filter_fields:
                processed["metadata"] = {
                    k: v for k, v in item.metadata.items() if k in params.filter_fields
                }
            else:
                processed["metadata"] = item.metadata
        return processed

    def _aggregate_data(self, processed_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate numeric values."""
        numeric_values = [
            item["value"]
            for item in processed_items
            if isinstance(item.get("value"), (int, float))
        ]
        if not numeric_values:
            return {}
        count = len(numeric_values)
        total = sum(numeric_values)
        return {
            "count": count,
            "sum": total,
            "average": total / count if count > 0 else 0,
            "min": min(numeric_values),
            "max": max(numeric_values),
        }

    def _validate_data_against_schema(
        self,
        data: Any,
        schema: SchemaDefinition,
        path: str,
        errors: list[ValidationError],
    ) -> None:
        """Recursively validate data against a schema definition."""
        schema_type = schema.type.lower()

        # Type checking
        type_valid = False
        expected_type_msg = schema_type
        current_type_name = type(data).__name__

        if (
            schema_type == "object"
            and isinstance(data, dict)
            or schema_type == "array"
            and isinstance(data, list)
            or schema_type == "string"
            and isinstance(data, str)
            or schema_type == "number"
            and isinstance(data, (int, float))
            or schema_type == "integer"
            and isinstance(data, int)
            or schema_type == "boolean"
            and isinstance(data, bool)
            or schema_type == "null"
            and data is None
        ):
            type_valid = True

        if not type_valid:
            errors.append(
                ValidationError(
                    path=path or "$",
                    message=f"Expected type '{expected_type_msg}', got {current_type_name}",
                )
            )
            return  # Stop validation for this path if type is wrong

        # Further validation based on type
        if schema_type == "object":
            if schema.required:
                for req_prop in schema.required:
                    if req_prop not in data:
                        errors.append(
                            ValidationError(
                                path=path or "$",
                                message=f"Required property '{req_prop}' missing",
                            )
                        )
            if schema.properties:
                for prop_name, prop_schema_dict in schema.properties.items():
                    if prop_name in data:
                        prop_path = f"{path}.{prop_name}" if path else prop_name
                        try:
                            prop_schema = SchemaDefinition(**prop_schema_dict)
                            self._validate_data_against_schema(
                                data[prop_name], prop_schema, prop_path, errors
                            )
                        except ValidationError as e_pydantic:
                            errors.append(
                                ValidationError(
                                    path=prop_path,
                                    message=f"Invalid property schema definition for '{prop_name}': {e_pydantic}",
                                )
                            )
                        except Exception as e:
                            errors.append(
                                ValidationError(
                                    path=prop_path,
                                    message=f"Error validating property '{prop_name}': {e}",
                                )
                            )

        elif schema_type == "array" and schema.items:
            try:
                item_schema = SchemaDefinition(**schema.items)
                for i, item in enumerate(data):
                    item_path = f"{path}[{i}]"
                    self._validate_data_against_schema(
                        item, item_schema, item_path, errors
                    )
            except ValidationError as e_pydantic:
                errors.append(
                    ValidationError(
                        path=path or "$",
                        message=f"Invalid array items schema definition: {e_pydantic}",
                    )
                )
            except Exception as e:
                errors.append(
                    ValidationError(
                        path=path or "$", message=f"Error validating array items: {e}"
                    )
                )

        elif schema_type == "string":
            if schema.pattern and not self._matches_pattern(data, schema.pattern):
                errors.append(
                    ValidationError(
                        path=path or "$",
                        message=f"Value does not match pattern: {schema.pattern}",
                    )
                )
            # Basic email format check
            if schema.format == "email":
                if (
                    not isinstance(data, str)
                    or "@" not in data
                    or "." not in data.split("@")[-1]
                ):
                    errors.append(
                        ValidationError(
                            path=path or "$", message="Invalid email format"
                        )
                    )
            # Add other format checks if needed (date-time, etc.)

        elif schema_type in ["number", "integer"]:
            # Ensure data is numeric (already checked by type_valid)
            num_data = data
            if schema.minimum is not None and num_data < schema.minimum:
                errors.append(
                    ValidationError(
                        path=path or "$",
                        message=f"Value {num_data} is less than minimum {schema.minimum}",
                    )
                )
            if schema.maximum is not None and num_data > schema.maximum:
                errors.append(
                    ValidationError(
                        path=path or "$",
                        message=f"Value {num_data} is greater than maximum {schema.maximum}",
                    )
                )

    def _matches_pattern(self, data: str, pattern: str) -> bool:
        """Simple regex pattern matching."""
        if not isinstance(data, str):  # Should not happen if type validation runs first
            return False
        try:
            # Use re.fullmatch for complete string matching against pattern
            return bool(re.fullmatch(pattern, data))
        except re.error as e:
            # Log regex error, but treat as non-match for validation purposes
            print(
                f"[Warning] Invalid regex pattern '{pattern}' encountered during validation: {e}",
                file=sys.stderr,
            )
            return False
