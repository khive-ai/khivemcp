"""Tests for AutoMCP server configuration loading."""

import json
import os
from pathlib import Path

import pytest
import yaml

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig, ServiceConfig
from verification.groups.example_group import ExampleGroup
from verification.groups.schema_group import SchemaGroup
from verification.groups.timeout_group import TimeoutGroup


@pytest.mark.asyncio
async def test_load_single_group_from_json():
    """Test that AutoMCPServer can load a single group from JSON config."""
    config_path = Path(__file__).parent.parent / "config" / "example_group.json"

    # Load the JSON file
    with open(config_path, "r") as f:
        config_data = json.load(f)

    # Create a GroupConfig from the loaded data
    config = GroupConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the group manually for testing
    server.groups["example"] = ExampleGroup()

    # Verify the group was loaded
    assert "example" in server.groups
    assert isinstance(server.groups["example"], ExampleGroup)

    # Verify operation execution
    from automcp.types import ExecutionRequest, ServiceRequest

    request = ServiceRequest(
        requests=[ExecutionRequest(operation="hello_world", arguments={})]
    )

    result = await server._handle_service_request("example", request)
    assert "Hello, World!" in result.content.text


@pytest.mark.asyncio
async def test_load_multi_group_from_yaml():
    """Test that AutoMCPServer can load multiple groups from YAML config."""
    config_path = Path(__file__).parent.parent / "config" / "multi_group.yaml"

    # Load the YAML file
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # Create a ServiceConfig from the loaded data
    config = ServiceConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the groups manually for testing
    server.groups["example"] = ExampleGroup()
    server.groups["schema"] = SchemaGroup()
    server.groups["timeout"] = TimeoutGroup()

    # Verify all groups were loaded
    assert "example" in server.groups
    assert "schema" in server.groups
    assert "timeout" in server.groups

    assert isinstance(server.groups["example"], ExampleGroup)
    assert isinstance(server.groups["schema"], SchemaGroup)
    assert isinstance(server.groups["timeout"], TimeoutGroup)

    # Verify operation from each group
    from automcp.types import ExecutionRequest, ServiceRequest

    # Test example group
    request = ServiceRequest(
        requests=[ExecutionRequest(operation="hello_world", arguments={})]
    )
    result = await server._handle_service_request("example", request)
    assert "Hello, World!" in result.content.text

    # Test schema group
    request = ServiceRequest(
        requests=[
            ExecutionRequest(
                operation="greet_person",
                arguments={"name": "Test User", "age": 30, "email": "test@example.com"},
            )
        ]
    )
    result = await server._handle_service_request("schema", request)
    assert "Hello, Test User!" in result.content.text

    # Test timeout group
    request = ServiceRequest(
        requests=[ExecutionRequest(operation="sleep", arguments={"seconds": 0.1})]
    )
    result = await server._handle_service_request("timeout", request)
    assert "Slept for 0.1 seconds" in result.content.text


@pytest.mark.asyncio
async def test_load_specific_group_from_yaml():
    """Test that AutoMCPServer can load a specific group from multi-group YAML config."""
    config_path = Path(__file__).parent.parent / "config" / "multi_group.yaml"

    # Load the YAML file to get the group config
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # Extract just the schema group configuration
    schema_group_config = {
        "name": "schema",
        "description": "Schema validation group for AutoMCP verification",
        "packages": config_data["packages"],
    }

    # Create a GroupConfig from the extracted data
    config = GroupConfig(**schema_group_config)

    # Create server with the specific group config
    server = AutoMCPServer("test-server", config)

    # Register the schema group manually for testing
    server.groups["schema"] = SchemaGroup()

    # Verify only the schema group was loaded
    assert "schema" in server.groups
    assert isinstance(server.groups["schema"], SchemaGroup)

    # Verify operation execution
    from automcp.types import ExecutionRequest, ServiceRequest

    request = ServiceRequest(
        requests=[
            ExecutionRequest(
                operation="greet_person",
                arguments={"name": "Test User", "age": 30, "email": "test@example.com"},
            )
        ]
    )

    result = await server._handle_service_request("schema", request)
    assert "Hello, Test User!" in result.content.text
