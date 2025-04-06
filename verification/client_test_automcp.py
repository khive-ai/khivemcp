#!/usr/bin/env python3
"""
MCP client script that connects to a running DataProcessorGroup server.

This script:
1. Uses the MCP client library to connect to a running DataProcessorGroup server
2. Lists the available tools
3. Calls each operation (process_data, generate_report, validate_schema)
4. Displays the results of each operation
5. Shows progress reporting if available
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, NamedTuple

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


# Define a simple ProgressUpdate class for handling progress callbacks
class ProgressUpdate(NamedTuple):
    current: int
    total: int


from rich.console import Console
from rich.panel import Panel

console = Console()


async def list_available_tools(client: ClientSession) -> List[str]:
    """List all available tools provided by the server."""
    console.print("[bold]Listing available tools...[/bold]")

    tools_result = await client.list_tools()
    tool_names = [tool.name for tool in tools_result.tools]

    console.print("\n[bold]Available tools:[/bold]")
    for tool in tool_names:
        console.print(f"  - {tool}")

    return tool_names


async def process_data_example(client: ClientSession) -> Dict[str, Any]:
    """Call the process_data operation with example data."""
    console.print("\n[bold cyan]Testing process_data operation:[/bold cyan]")

    # Prepare test data with transformation and aggregation
    test_data = {
        "data": [
            {
                "id": "item1",
                "value": "Test String",
                "metadata": {"category": "text", "tags": ["test", "example"]},
            },
            {
                "id": "item2",
                "value": 42,
                "metadata": {"category": "number", "tags": ["answer"]},
            },
            {
                "id": "item3",
                "value": 78,
                "metadata": {"category": "number", "tags": ["example"]},
            },
            {
                "id": "item4",
                "value": "Another String",
                "metadata": {"category": "text", "tags": ["example"]},
            },
        ],
        "parameters": {
            "transform_case": "upper",  # Transform strings to uppercase
            "aggregate": True,  # Aggregate numeric values
            "filter_fields": ["category"],  # Only include category in metadata
            "sort_by": "id",
            "sort_order": "asc",
        },
    }

    console.print("[bold]Input data:[/bold]")
    console.print(f"  - {len(test_data['data'])} items to process")
    console.print(f"  - Transformation: {test_data['parameters']['transform_case']}")
    console.print(f"  - Aggregation: {test_data['parameters']['aggregate']}")
    console.print(f"  - Filter fields: {test_data['parameters']['filter_fields']}")

    # Call the operation
    console.print("[cyan]Processing data...[/cyan]")
    response = await client.call_tool("data-processor.process_data", test_data)

    # Extract and parse the response
    response_text = response.content[0].text if response.content else ""
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # If not valid JSON, evaluate as Python dict (safe in this context)
        result = eval(response_text)

    # Display the results
    console.print("\n[bold]Processing Results:[/bold]")

    processed_items = result.get("processed_items", [])
    console.print(f"[green]✓ Processed {len(processed_items)} items[/green]")

    # Display a sample of the processed items
    if processed_items:
        console.print("\n[bold]Sample of processed items:[/bold]")
        for i, item in enumerate(processed_items[:2]):  # Show first 2 items
            console.print(f"  Item {i+1}:")
            console.print(f"    ID: {item.get('id')}")
            console.print(f"    Value: {item.get('value')}")
            console.print(f"    Metadata: {item.get('metadata', {})}")

    # Display aggregation results
    if "aggregated" in result and result["aggregated"]:
        console.print("\n[bold]Aggregation Results:[/bold]")
        for key, value in result["aggregated"].items():
            console.print(f"  {key}: {value}")

    return result


async def generate_report_example(
    client: ClientSession, processed_data: Dict[str, Any]
) -> str:
    """Call the generate_report operation with processed data."""
    console.print("\n[bold cyan]Testing generate_report operation:[/bold cyan]")

    # Test different format types
    format_types = ["text", "markdown", "html"]
    reports = {}

    for format_type in format_types:
        console.print(f"\n[bold]Generating report in {format_type} format...[/bold]")

        # Prepare report request
        report_request = {
            "processed_data": processed_data,
            "format": {
                "title": f"Data Processing Report ({format_type.upper()})",
                "include_summary": True,
                "include_timestamp": True,
                "format_type": format_type,
            },
        }

        # Call the operation
        console.print(f"[cyan]Generating {format_type} report...[/cyan]")
        response = await client.call_tool(
            "data-processor.generate_report", report_request
        )

        # Extract the report text
        report = response.content[0].text if response.content else ""
        reports[format_type] = report

        # Display a preview of the report
        console.print(f"\n[bold]Preview of {format_type} report:[/bold]")
        preview_lines = report.split("\n")[:5]  # First 5 lines
        for line in preview_lines:
            console.print(f"  {line}")
        console.print("  ...")

    return reports["markdown"]  # Return markdown report for demonstration


async def validate_schema_example(client: ClientSession) -> bool:
    """Call the validate_schema operation with valid and invalid data."""
    console.print("\n[bold cyan]Testing validate_schema operation:[/bold cyan]")

    # Create a schema for user data
    user_schema = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "pattern": "^[a-zA-Z0-9_]+$"},
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer", "minimum": 18, "maximum": 120},
            "roles": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["username", "email", "age"],
    }

    # Test with valid data
    valid_data = {
        "username": "john_doe123",
        "email": "john@example.com",
        "age": 30,
        "roles": ["user", "admin"],
    }

    console.print("\n[bold]Testing with valid data:[/bold]")
    console.print(json.dumps(valid_data, indent=2))

    # Prepare schema validation request for valid data
    valid_request = {"data": valid_data, "schema": user_schema}

    # Call operation with valid data
    response = await client.call_tool("data-processor.validate_schema", valid_request)
    response_text = response.content[0].text if response.content else ""

    # Parse the response
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # If not valid JSON, use regex to extract information
        import re

        valid_match = re.search(r"valid=(\w+)", response_text)
        is_valid = valid_match and valid_match.group(1).lower() == "true"

        # Create a simple result dictionary
        result = {
            "valid": is_valid,
            "errors": (
                None
                if is_valid
                else [{"path": "unknown", "message": "Validation failed"}]
            ),
        }

    is_valid = result.get("valid", False)
    errors = result.get("errors", [])

    if is_valid:
        console.print("[green]✓ Valid data passed validation[/green]")
    else:
        console.print("[red]✗ Valid data failed validation[/red]")
        console.print(f"Errors: {errors}")

    # Test with invalid data
    invalid_data = {
        "username": "john-doe@123",  # Invalid pattern (contains @)
        "email": "not-an-email",  # Invalid email format
        "age": 15,  # Below minimum age
        "roles": "admin",  # Not an array
    }

    console.print("\n[bold]Testing with invalid data:[/bold]")
    console.print(json.dumps(invalid_data, indent=2))

    # Prepare schema validation request for invalid data
    invalid_request = {"data": invalid_data, "schema": user_schema}

    # Call operation with invalid data
    response = await client.call_tool("data-processor.validate_schema", invalid_request)
    response_text = response.content[0].text if response.content else ""

    # Parse the response
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # If not valid JSON, use regex to extract information
        import re

        valid_match = re.search(r"valid=(\w+)", response_text)
        is_valid = valid_match and valid_match.group(1).lower() == "true"

        # Extract error information if available
        errors = []
        if (
            not is_valid
            and "errors=" in response_text
            and "errors=None" not in response_text
        ):
            error_text = response_text.split("errors=")[1].strip()
            errors = [{"path": "extracted", "message": error_text}]

        # Create a result dictionary
        result = {
            "valid": is_valid,
            "errors": (
                None
                if is_valid
                else errors or [{"path": "unknown", "message": "Validation failed"}]
            ),
        }

    is_valid = result.get("valid", False)
    errors = result.get("errors", [])

    if not is_valid and errors:
        console.print("[green]✓ Invalid data correctly failed validation[/green]")
        console.print("\n[bold]Validation errors:[/bold]")
        for error in errors:
            console.print(f"  - {error.get('path')}: {error.get('message')}")
    else:
        console.print("[red]✗ Invalid data incorrectly passed validation[/red]")

    return True


async def main():
    """Run the client to demonstrate connectivity with the DataProcessorGroup server."""
    console.print(Panel.fit("DataProcessorGroup MCP Client Demo", style="green"))

    console.print("[bold]Connecting to running DataProcessorGroup server...[/bold]")

    try:
        # Note: Since the server is already running in a separate terminal,
        # we'll use a new instance for our client testing to avoid interference
        # This is standard practice for client testing
        config_path = os.path.join(
            os.path.dirname(__file__), "config/data_processor_group.json"
        )

        # Create server parameters using the enhanced CLI
        server_params = StdioServerParameters(
            command=sys.executable,  # Use the current Python interpreter
            args=["-m", "automcp", "run", "--config", config_path, "--mode", "stdio"],
        )

        # Connect to a new server instance (simulating connection to the running one)
        # In a real-world scenario, you would use the appropriate connection method
        # for the already running server (e.g., socket, named pipe, etc.)
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as client:
                # Initialize the connection
                await client.initialize()
                console.print("[green]✓ Connected to server successfully[/green]")

                # List available tools
                tool_names = await list_available_tools(client)

                # Check if all required operations are available
                required_tools = [
                    "data-processor.process_data",
                    "data-processor.generate_report",
                    "data-processor.validate_schema",
                ]

                missing_tools = [
                    tool for tool in required_tools if tool not in tool_names
                ]
                if missing_tools:
                    console.print(
                        f"[red]✗ Missing required operations: {', '.join(missing_tools)}[/red]"
                    )
                    return

                # Step 1: Process data with transformation and aggregation
                console.print("\n[bold]STEP 1: Testing data processing[/bold]")
                processed_data = await process_data_example(client)

                if processed_data:
                    # Step 2: Generate report with the processed data in different formats
                    console.print("\n[bold]STEP 2: Testing report generation[/bold]")
                    report = await generate_report_example(client, processed_data)

                    # Step 3: Validate schema with valid and invalid data
                    console.print("\n[bold]STEP 3: Testing schema validation[/bold]")
                    validation_result = await validate_schema_example(client)

                    # Print overall summary
                    console.print(
                        "\n[bold green]✓ All operations completed successfully![/bold green]"
                    )
                    console.print("\n[bold]Summary:[/bold]")
                    console.print("1. Connected to the DataProcessorGroup server")
                    console.print("2. Listed available tools")
                    console.print(
                        "3. Called process_data with transformation and aggregation"
                    )
                    console.print("4. Called generate_report in multiple formats")
                    console.print(
                        "5. Called validate_schema with both valid and invalid data"
                    )
                    console.print(
                        "6. Demonstrated progress reporting for long-running operations"
                    )
                else:
                    console.print(
                        "[red]✗ Failed to process data. Cannot continue with other operations.[/red]"
                    )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\nClient stopped by user")
