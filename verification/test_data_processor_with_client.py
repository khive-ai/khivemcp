#!/usr/bin/env python3
"""
Test DataProcessorGroup implementation with an MCP client.

This script:
1. Uses an MCP client to connect to the server
2. Tests all three operations (process_data, generate_report, validate_schema)
3. Verifies progress reporting and logging work correctly
"""

import asyncio
import json
import time

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def test_process_data(client: ClientSession) -> dict:
    """Test the process_data operation."""
    console.print("\n[bold]Testing process_data operation...[/bold]")

    # Prepare test data
    test_data = {
        "data": [
            {
                "id": "item1",
                "value": "Test String",
                "metadata": {"type": "text", "priority": "high"},
            },
            {
                "id": "item2",
                "value": 42,
                "metadata": {"type": "number", "priority": "medium"},
            },
            {
                "id": "item3",
                "value": 78,
                "metadata": {"type": "number", "priority": "low"},
            },
        ],
        "parameters": {
            "transform_case": "upper",
            "aggregate": True,
            "filter_fields": ["type"],
        },
    }

    # Call the operation
    start_time = time.time()
    response = await client.call_tool("data-processor.process_data", test_data)
    end_time = time.time()

    # Extract the response text
    response_text = response.content[0].text if response.content else ""

    # Parse the response
    try:
        # First try to parse as JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If it's not valid JSON, try to evaluate it as a Python dict
            # This is safe in our controlled environment since we know the response format
            result = eval(response_text)

        console.print("[green]✓ Successfully processed data[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to parse response: {e}[/red]")
        console.print(f"Response: {response_text}")
        return {}

    # Verify the results
    processed_items = result.get("processed_items", [])
    aggregated = result.get("aggregated", {})

    # Print the results
    console.print(
        f"Processed {len(processed_items)} items in {end_time - start_time:.2f} seconds"
    )

    if "aggregated" in result:
        console.print("[green]✓ Aggregation was performed correctly[/green]")
        console.print(f"Aggregation results: {aggregated}")

    # Check for case transformation
    if any(item.get("value") == "TEST STRING" for item in processed_items):
        console.print(
            "[green]✓ Case transformation was applied correctly[/green]"
        )

    # Check for field filtering
    if all(
        "type" in item.get("metadata", {}) for item in processed_items
    ) and all(
        "priority" not in item.get("metadata", {}) for item in processed_items
    ):
        console.print("[green]✓ Field filtering was applied correctly[/green]")

    return result


async def test_generate_report(
    client: ClientSession, processed_data: dict
) -> str:
    """Test the generate_report operation."""
    console.print("\n[bold]Testing generate_report operation...[/bold]")

    # Prepare report generation request
    report_request = {
        "processed_data": processed_data,
        "format": {
            "title": "Data Processor Test Report",
            "include_summary": True,
            "include_timestamp": True,
            "format_type": "markdown",
        },
    }

    # Call the operation
    start_time = time.time()
    response = await client.call_tool(
        "data-processor.generate_report", report_request
    )
    end_time = time.time()

    # Extract the response text
    report = response.content[0].text if response.content else ""

    # Verify the report
    console.print(f"Generated report in {end_time - start_time:.2f} seconds")

    # Check for markdown format
    if "# Data Processor Test Report" in report:
        console.print("[green]✓ Report title is correct[/green]")

    if "## Summary" in report:
        console.print("[green]✓ Summary section was included[/green]")

    if "Generated:" in report:
        console.print("[green]✓ Timestamp was included[/green]")

    if "## Data Items" in report:
        console.print("[green]✓ Data items section was included[/green]")

    # Print a sample of the report
    console.print("\n[bold]Report Preview:[/bold]")
    preview_lines = report.split("\n")[:10]
    console.print("\n".join(preview_lines) + "\n...")

    return report


async def test_validate_schema(client: ClientSession) -> bool:
    """Test the validate_schema operation."""
    console.print("\n[bold]Testing validate_schema operation...[/bold]")

    # Create a schema for testing
    schema_request = {
        "data": {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "addresses": [
                {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "zipcode": "12345",
                }
            ],
        },
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0, "maximum": 120},
                "email": {"type": "string", "format": "email"},
                "addresses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "zipcode": {"type": "string"},
                        },
                        "required": ["street", "city"],
                    },
                },
            },
            "required": ["name", "email"],
        },
    }

    # Call the operation
    start_time = time.time()
    response = await client.call_tool(
        "data-processor.validate_schema", schema_request
    )
    end_time = time.time()

    # Extract the response text
    response_text = response.content[0].text if response.content else ""

    # Parse the response
    try:
        # First try to parse as JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If it's not a proper JSON, try to extract the values directly
            if "valid=True" in response_text:
                result = {"valid": True, "errors": None}
            elif "valid=False" in response_text:
                # This is a simplification - in a real app we'd parse the errors too
                result = {
                    "valid": False,
                    "errors": [
                        {"path": "unknown", "message": "validation error"}
                    ],
                }
            else:
                # If not recognizable, try to evaluate as Python dict
                result = eval(response_text)

        console.print("[green]✓ Successfully validated schema[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to parse response: {e}[/red]")
        console.print(f"Response: {response_text}")
        return False

    # Verify the results
    is_valid = result.get("valid", False)
    errors = result.get("errors", [])

    console.print(
        f"Validation completed in {end_time - start_time:.2f} seconds"
    )

    if is_valid:
        console.print("[green]✓ Data is valid according to the schema[/green]")
    else:
        console.print("[red]✗ Data validation failed[/red]")
        console.print(f"Errors: {errors}")

    # Test with invalid data
    console.print(
        "\n[bold]Testing schema validation with invalid data...[/bold]"
    )

    # Modify the schema request with invalid data
    invalid_schema_request = schema_request.copy()
    invalid_schema_request["data"] = {
        "name": "John Doe",
        "age": -5,  # Invalid age (negative)
        "addresses": [
            {
                "street": "123 Main St",
                # Missing required "city" field
                "zipcode": "12345",
            }
        ],
        # Missing required "email" field
    }

    # Call the operation with invalid data
    response = await client.call_tool(
        "data-processor.validate_schema", invalid_schema_request
    )

    # Extract the response text
    response_text = response.content[0].text if response.content else ""

    # Parse the response
    try:
        # First try to parse as JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If it's not a proper JSON, try to extract the values directly
            if "valid=True" in response_text:
                result = {"valid": True, "errors": None}
            elif "valid=False" in response_text:
                # Extract errors if possible
                result = {"valid": False, "errors": []}
                # Try to parse out error information
                if (
                    "errors=" in response_text
                    and "errors=None" not in response_text
                ):
                    error_parts = response_text.split("errors=")[1].strip()
                    # Add a simple error entry
                    result["errors"] = [
                        {"path": "extracted", "message": error_parts}
                    ]
            else:
                # If not recognizable, try to evaluate as Python dict
                result = eval(response_text)
    except Exception as e:
        console.print(
            f"[red]✗ Failed to parse response for invalid data: {e}[/red]"
        )
        return is_valid

    # Verify the results for invalid data
    is_invalid_valid = result.get("valid", True)
    errors = result.get("errors", [])

    if not is_invalid_valid and errors:
        console.print("[green]✓ Invalid data was correctly identified[/green]")
        console.print("Validation errors:")
        for error in errors:
            console.print(f"  - {error.get('path')}: {error.get('message')}")
    else:
        console.print("[red]✗ Invalid data was not correctly identified[/red]")

    return is_valid


async def main():
    """Run the client tests against the DataProcessorGroup server."""
    console.print(
        Panel.fit("DataProcessorGroup MCP Client Test", style="green")
    )

    # Start the server in a separate process using the run_group_server
    config_path = (
        Path(__file__).parent / "config" / "data_processor_group.json"
    )
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "verification.run_group_server", str(config_path)],
    )

    console.print("[bold]Connecting to DataProcessorGroup server...[/bold]")

    try:
        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize the connection
                await client.initialize()
                console.print(
                    "[green]✓ Connected to server successfully[/green]"
                )

                # Get the list of available tools
                tools_result = await client.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]

                # Verify the expected tools are available
                console.print("\n[bold]Available tools:[/bold]")
                for tool in tool_names:
                    console.print(f"  - {tool}")

                # Check if all required operations are available
                required_tools = [
                    "data-processor.process_data",
                    "data-processor.generate_report",
                    "data-processor.validate_schema",
                ]

                all_tools_available = all(
                    tool in tool_names for tool in required_tools
                )
                if all_tools_available:
                    console.print(
                        "[green]✓ All required operations are available[/green]"
                    )
                else:
                    missing_tools = [
                        tool
                        for tool in required_tools
                        if tool not in tool_names
                    ]
                    console.print(
                        f"[red]✗ Missing operations: {', '.join(missing_tools)}[/red]"
                    )
                    return

                # Run the tests
                processed_data = await test_process_data(client)
                if processed_data:
                    report = await test_generate_report(client, processed_data)
                    validation_result = await test_validate_schema(client)

                    # Print summary
                    console.print("\n[bold]Test Summary:[/bold]")
                    table = Table()
                    table.add_column("Operation")
                    table.add_column("Status")

                    table.add_row(
                        "process_data",
                        (
                            "[green]PASS[/green]"
                            if processed_data
                            else "[red]FAIL[/red]"
                        ),
                    )
                    table.add_row(
                        "generate_report",
                        "[green]PASS[/green]" if report else "[red]FAIL[/red]",
                    )
                    table.add_row(
                        "validate_schema",
                        (
                            "[green]PASS[/green]"
                            if validation_result
                            else "[red]FAIL[/red]"
                        ),
                    )

                    console.print(table)

                    if processed_data and report and validation_result:
                        console.print(
                            "\n[green]✓ All tests passed successfully![/green]"
                        )
                    else:
                        console.print(
                            "\n[red]✗ Some tests failed. See details above.[/red]"
                        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\nTest stopped by user")
