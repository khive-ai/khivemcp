"""Tests for the DataProcessorGroup service group."""

import json

import pytest
from mcp.types import TextContent

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig
from verification.groups.data_processor_group import (
    DataItem,
    DataProcessingSchema,
    DataProcessorGroup,
    ProcessingParameters,
    ReportFormat,
    ReportGenerationSchema,
    SchemaDefinition,
    SchemaValidationRequestSchema,
    ValidationResult,
)
from verification.tests.test_helpers import (
    create_connected_automcp_server_and_client_session,
)


# Helper function to create a mock Context object
def create_mock_context():
    """Create a mock Context object for testing."""
    ctx = TextContent(type="text", text="")

    # Add progress tracking
    progress_tracking = []

    async def report_progress(current, total):
        progress_tracking.append((current, total))

    # Add logging
    logs = []

    def info(message):
        logs.append(message)

    ctx.report_progress = report_progress
    ctx.info = info

    # Add properties to track the calls
    ctx.progress_tracking = progress_tracking
    ctx.logs = logs

    return ctx


# Sample test data
def create_test_data():
    """Create sample data for testing."""
    return [
        DataItem(
            id="item1",
            value="Test Value",
            metadata={"category": "test", "priority": "high"},
        ),
        DataItem(
            id="item2",
            value=42,
            metadata={"category": "numeric", "priority": "medium"},
        ),
        DataItem(
            id="item3",
            value=True,
            metadata={"category": "boolean", "priority": "low"},
        ),
    ]


# Unit Tests
@pytest.mark.asyncio
async def test_process_data_direct():
    """Test process_data operation directly."""
    group = DataProcessorGroup()
    ctx = create_mock_context()

    # Test with default parameters
    test_data = create_test_data()
    result = await group.process_data(data=test_data, ctx=ctx)

    assert "processed_items" in result
    assert len(result["processed_items"]) == 3
    assert result["processed_items"][0]["id"] == "item1"
    assert result["processed_items"][0]["value"] == "Test Value"
    assert "aggregated" not in result

    # Verify progress reporting
    assert len(ctx.progress_tracking) == 3
    assert ctx.progress_tracking[0] == (1, 3)
    assert ctx.progress_tracking[2] == (3, 3)

    # Verify logging
    assert any("Processing 3 data items" in log for log in ctx.logs)
    assert any("completed successfully" in log for log in ctx.logs)


@pytest.mark.asyncio
async def test_process_data_with_transformations():
    """Test process_data with various transformations."""
    group = DataProcessorGroup()
    ctx = create_mock_context()

    # Test with case transformation
    test_data = create_test_data()
    result = await group.process_data(
        data=test_data, parameters={"transform_case": "upper"}, ctx=ctx
    )

    assert result["processed_items"][0]["value"] == "TEST VALUE"

    # Test with case transformation (lower)
    test_data = create_test_data()
    result = await group.process_data(
        data=test_data, parameters={"transform_case": "lower"}, ctx=ctx
    )

    assert result["processed_items"][0]["value"] == "test value"

    # Test with filter fields
    test_data = create_test_data()
    result = await group.process_data(
        data=test_data, parameters={"filter_fields": ["category"]}, ctx=ctx
    )

    assert "category" in result["processed_items"][0]["metadata"]
    assert "priority" not in result["processed_items"][0]["metadata"]


@pytest.mark.asyncio
async def test_process_data_with_aggregation():
    """Test process_data with aggregation."""
    group = DataProcessorGroup()
    ctx = create_mock_context()

    # Create test data with numeric values
    test_data = [
        DataItem(id="num1", value=10),
        DataItem(id="num2", value=20),
        DataItem(id="num3", value=30),
    ]

    # Test with aggregation
    result = await group.process_data(
        data=test_data, parameters={"aggregate": True}, ctx=ctx
    )

    assert "aggregated" in result
    assert result["aggregated"]["count"] == 3
    assert result["aggregated"]["sum"] == 60
    assert result["aggregated"]["average"] == 20
    assert result["aggregated"]["min"] == 10
    assert result["aggregated"]["max"] == 30


@pytest.mark.asyncio
async def test_generate_report_direct():
    """Test generate_report operation directly."""
    group = DataProcessorGroup()
    ctx = create_mock_context()

    # Create processed data
    processed_data = {
        "processed_items": [
            {
                "id": "item1",
                "value": "Test Value",
                "metadata": {"category": "test"},
            },
            {
                "id": "item2",
                "value": 42,
                "metadata": {"category": "numeric"},
            },
        ]
    }

    # Test with default format (text)
    result = await group.generate_report(
        processed_data=processed_data, ctx=ctx
    )

    assert "Data Processing Report" in result
    assert "Generated:" in result
    assert "Total items: 2" in result
    assert "Item: item1" in result
    assert "Value: Test Value" in result

    # Verify progress reporting
    assert len(ctx.progress_tracking) == 3
    assert ctx.progress_tracking[0] == (1, 3)
    assert ctx.progress_tracking[2] == (3, 3)


@pytest.mark.asyncio
async def test_generate_report_formats():
    """Test generate_report with different formats."""
    group = DataProcessorGroup()
    ctx = create_mock_context()

    # Create processed data with aggregation
    processed_data = {
        "processed_items": [
            {"id": "item1", "value": 10},
            {"id": "item2", "value": 20},
        ],
        "aggregated": {
            "count": 2,
            "sum": 30,
            "average": 15,
        },
    }

    # Test markdown format
    result = await group.generate_report(
        processed_data=processed_data,
        format={"format_type": "markdown"},
        ctx=ctx,
    )

    assert "# Data Processing Report" in result
    assert "## Summary" in result
    assert "### Aggregated Data" in result
    assert "## Data Items" in result

    # Test HTML format
    result = await group.generate_report(
        processed_data=processed_data, format={"format_type": "html"}, ctx=ctx
    )

    assert "<h1>Data Processing Report</h1>" in result
    assert "<h2>Summary</h2>" in result
    assert "<strong>Total items:</strong>" in result

    # Test without summary and timestamp
    result = await group.generate_report(
        processed_data=processed_data,
        format={"include_summary": False, "include_timestamp": False},
        ctx=ctx,
    )

    assert "Data Processing Report" in result
    assert "Generated:" not in result
    assert "Summary" not in result
    assert "Data Items" in result


@pytest.mark.asyncio
async def test_validate_schema_direct():
    """Test validate_schema operation directly."""
    group = DataProcessorGroup()

    # Test with valid data
    # Test with valid data
    schema_def = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0, "maximum": 120},
        },
        "required": ["name"],
    }

    valid_data = {"name": "John Doe", "age": 30}
    result = await group.validate_schema(data=valid_data, schema=schema_def)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert result.errors is None

    # Test with invalid data (wrong type)
    invalid_data = {"name": "John Doe", "age": "thirty"}
    result = await group.validate_schema(data=invalid_data, schema=schema_def)

    assert result.valid is False
    assert len(result.errors) > 0
    assert any("Expected number" in error.message for error in result.errors)

    # Test with invalid data (missing required)
    invalid_data = {"age": 30}
    result = await group.validate_schema(data=invalid_data, schema=schema_def)

    assert result.valid is False
    assert len(result.errors) > 0
    assert any(
        "Required property 'name' is missing" in error.message
        for error in result.errors
    )


@pytest.mark.asyncio
async def test_validate_schema_advanced():
    """Test validate_schema with more complex schemas."""
    group = DataProcessorGroup()

    # Test array validation
    array_schema = {
        "type": "array",
        "items": {"type": "integer", "minimum": 0},
    }

    valid_array = [1, 2, 3, 4, 5]
    result = await group.validate_schema(data=valid_array, schema=array_schema)

    assert result.valid is True

    invalid_array = [1, 2, "three", 4, 5]
    result = await group.validate_schema(
        data=invalid_array, schema=array_schema
    )

    assert result.valid is False
    assert any("[2]" in error.path for error in result.errors)

    # Test nested object validation
    nested_schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "contact": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "phone": {"type": "string"},
                        },
                        "required": ["email"],
                    },
                },
                "required": ["name", "contact"],
            }
        },
        "required": ["user"],
    }

    valid_nested = {
        "user": {
            "name": "Alice",
            "contact": {
                "email": "alice@example.com",
                "phone": "555-1234",
            },
        }
    }

    result = await group.validate_schema(
        data=valid_nested, schema=nested_schema
    )

    assert result.valid is True

    invalid_nested = {
        "user": {
            "name": "Bob",
            "contact": {
                # Missing required email
                "phone": "555-5678",
            },
        }
    }

    result = await group.validate_schema(
        data=invalid_nested, schema=nested_schema
    )

    assert result.valid is False
    assert any("contact.email" in error.path for error in result.errors)


# Integration Tests
@pytest.mark.asyncio
async def test_data_processor_group_integration():
    """Test end-to-end functionality of DataProcessorGroup through MCP protocol."""
    # Load the JSON file
    config_path = "verification/config/data_processor_group.json"
    with open(config_path, "r") as f:
        config_data = json.load(f)

    # Create a GroupConfig from the loaded data
    config = GroupConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the group manually for testing
    data_processor_group = DataProcessorGroup()
    data_processor_group.config = config
    server.groups["data-processor"] = data_processor_group

    # Create a connected server and client session
    async with create_connected_automcp_server_and_client_session(server) as (
        _,
        client,
    ):
        # Get the list of available tools
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        # Verify the expected tools are available
        assert "data-processor.process_data" in tool_names
        assert "data-processor.generate_report" in tool_names
        assert "data-processor.validate_schema" in tool_names

        # Test process_data operation
        process_data = {
            "data": [
                {
                    "id": "test1",
                    "value": "Hello World",
                    "metadata": {"type": "greeting", "language": "english"},
                },
                {
                    "id": "test2",
                    "value": 123,
                    "metadata": {"type": "number", "category": "integer"},
                },
            ],
            "parameters": {
                "transform_case": "upper",
                "aggregate": True,
            },
        }

        response = await client.call_tool(
            "data-processor.process_data", process_data
        )
        response_text = response.content[0].text if response.content else ""

        # Check for expected content in response
        assert "HELLO WORLD" in response_text
        assert "test1" in response_text
        assert "test2" in response_text
        assert "processed_items" in response_text
        assert "aggregated" in response_text
        # Use the response text for next operation
        processed_data_str = response_text

        # Test generate_report operation
        # Create simplified test data directly
        report_data = {
            "processed_data": {
                "processed_items": [
                    {"id": "test1", "value": "HELLO WORLD"},
                    {"id": "test2", "value": 123},
                ]
            },
            "format": {
                "title": "Integration Test Report",
                "format_type": "markdown",
            },
        }

        response = await client.call_tool(
            "data-processor.generate_report", report_data
        )
        response_text = response.content[0].text if response.content else ""

        assert "# Integration Test Report" in response_text

        # Test validate_schema operation
        schema_data = {
            "data": {"name": "Test User", "email": "test@example.com"},
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                },
                "required": ["name", "email"],
            },
        }

        response = await client.call_tool(
            "data-processor.validate_schema", schema_data
        )
        response_text = response.content[0].text if response.content else ""

        assert "valid" in response_text
        assert "true" in response_text.lower()


@pytest.mark.asyncio
async def test_data_processor_validation_errors():
    """Test validation error handling for DataProcessorGroup."""
    # Create server with the config
    config = GroupConfig(
        name="data-processor",
        description="Group for data processing operations",
    )
    server = AutoMCPServer("test-server", config)

    # Register the group manually for testing
    data_processor_group = DataProcessorGroup()
    data_processor_group.config = config
    server.groups["data-processor"] = data_processor_group

    # Create a connected server and client session
    async with create_connected_automcp_server_and_client_session(server) as (
        _,
        client,
    ):
        # Test process_data with invalid data (missing required field)
        invalid_process_data = {
            "data": [
                {
                    # Missing required "id" field
                    "value": "Test Value",
                }
            ]
        }

        response = await client.call_tool(
            "data-processor.process_data", invalid_process_data
        )
        response_text = response.content[0].text if response.content else ""

        assert (
            "error" in response_text.lower()
            or "validation" in response_text.lower()
            or "missing" in response_text.lower()
        )

        # Test validate_schema with invalid schema
        # Using schema with invalid value constraints instead of invalid type
        invalid_schema_data = {
            "data": {"age": -10},  # Negative age
            "schema": {
                "type": "object",
                "properties": {
                    "age": {"type": "number", "minimum": 0}  # Age must be >= 0
                },
                "required": ["age"],
            },
        }

        response = await client.call_tool(
            "data-processor.validate_schema", invalid_schema_data
        )
        response_text = response.content[0].text if response.content else ""

        assert "valid" in response_text.lower()
        assert "error" in response_text.lower()
        assert (
            "minimum" in response_text.lower()
            or "less than" in response_text.lower()
        )
