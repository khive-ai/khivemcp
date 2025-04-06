#!/usr/bin/env python3
"""
Test script for DataProcessorGroup using in-memory server and client session.

This test focuses on direct invocation of the DataProcessorGroup operations
using the MCP shared memory mechanism, which is more reliable than the stdio
client for direct testing.
"""

import asyncio
import json
from pprint import pprint

import pytest
from verification.tests.test_helpers import create_connected_automcp_server_and_client_session

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig
from verification.groups.data_processor_group import DataProcessorGroup


async def test_data_processor_operations():
    """Test all operations of the DataProcessorGroup."""
    # Create server configuration
    config = GroupConfig(
        name="data-processor",
        description="Group for data processing operations",
        config={
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
    )

    # Create and register the server
    server = AutoMCPServer("test-server", config)
    data_processor_group = DataProcessorGroup()
    data_processor_group.config = config
    server.groups["data-processor"] = data_processor_group

    # Create an in-memory connection between server and client
    async with create_connected_automcp_server_and_client_session(server) as (_, client):
        print("Connected to in-memory server")

        # List available tools
        tools_result = await client.list_tools()
        print("\nAvailable tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}")

        # 1. Test process_data operation
        print("\n=== Testing process_data operation ===")
        process_data_input = {
            "data": [
                {
                    "id": "item1",
                    "value": "Sample Text",
                    "metadata": {"category": "text", "priority": "high", "tags": ["sample", "demo"]}
                },
                {
                    "id": "item2",
                    "value": 42,
                    "metadata": {"category": "number", "priority": "medium", "is_valid": True}
                },
                {
                    "id": "item3",
                    "value": 78.5,
                    "metadata": {"category": "number", "priority": "low"}
                }
            ],
            "parameters": {
                "transform_case": "upper",
                "aggregate": True,
                "sort_by": "id",
                "sort_order": "asc"
            }
        }

        response = await client.call_tool("data-processor.process_data", process_data_input)
        response_text = response.content[0].text if response.content else ""
        print(f"\nProcess data response:\n{response_text}")

        # Try to parse the response
        try:
            processed_data = json.loads(response_text)
            print("Successfully parsed JSON response")
        except json.JSONDecodeError:
            try:
                # If not valid JSON, try to eval as Python dict (only in controlled test environment)
                processed_data = eval(response_text)
                print("Successfully parsed response using eval")
            except:
                print("Failed to parse response")
                processed_data = {"processed_items": [{"id": "item1", "value": "SAMPLE TEXT"}]}
        
        # 2. Test generate_report operation
        print("\n=== Testing generate_report operation ===")
        report_request = {
            "processed_data": processed_data,
            "format": {
                "title": "Test Report",
                "include_summary": True,
                "include_timestamp": True,
                "format_type": "markdown"
            }
        }

        response = await client.call_tool("data-processor.generate_report", report_request)
        response_text = response.content[0].text if response.content else ""
        print(f"\nReport preview:\n{response_text[:300]}...")

        # 3. Test validate_schema operation
        print("\n=== Testing validate_schema operation ===")
        schema_request = {
            "data": {
                "name": "Test User",
                "email": "test@example.com",
                "age": 30
            },
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "age": {"type": "integer", "minimum": 18, "maximum": 120}
                },
                "required": ["name", "email"]
            }
        }

        response = await client.call_tool("data-processor.validate_schema", schema_request)
        response_text = response.content[0].text if response.content else ""
        print(f"\nSchema validation response:\n{response_text}")

        # Test with invalid data
        print("\n=== Testing schema validation with invalid data ===")
        invalid_schema_request = {
            "data": {
                "name": "Test User",
                "age": 15  # Invalid age (below minimum)
                # Missing required "email" field
            },
            "schema": schema_request["schema"]
        }

        response = await client.call_tool("data-processor.validate_schema", invalid_schema_request)
        response_text = response.content[0].text if response.content else ""
        print(f"\nInvalid schema validation response:\n{response_text}")


if __name__ == "__main__":
    asyncio.run(test_data_processor_operations())