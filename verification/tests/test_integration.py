"""Integration tests for AutoMCP server with different configurations using new testing infrastructure."""

import asyncio
import json
import time
from pathlib import Path

import pytest
import yaml

from automcp.schemas.registry import SchemaRegistry
from automcp.server import AutoMCPServer
from automcp.testing.server import (
    TestServer,
    create_connected_server_and_client_session,
)
from automcp.testing.transforms import (
    CompositeParameterTransformer,
    FlatParameterTransformer,
    NestedParameterTransformer,
)
from automcp.types import GroupConfig, ServiceConfig
from verification.groups.example_group import ExampleGroup
from verification.groups.schema_group import SchemaGroup
from verification.groups.timeout_group import TimeoutGroup

# Path to configuration files
CONFIG_DIR = Path(__file__).parent.parent / "config"


@pytest.mark.asyncio
async def test_example_group_integration():
    """Test end-to-end functionality of ExampleGroup through MCP protocol."""
    # Load the JSON file
    config_path = CONFIG_DIR / "example_group.json"
    with open(config_path) as f:
        config_data = json.load(f)

    # Create a GroupConfig from the loaded data
    config = GroupConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the group manually for testing
    example_group = ExampleGroup()
    example_group.config = config  # Set the config attribute
    server.groups["example"] = example_group

    # Create parameter transformers for example group operations
    parameter_transformers = {
        "example.hello_world": FlatParameterTransformer(),
        "example.echo": FlatParameterTransformer(),
        "example.count_to": FlatParameterTransformer(),
    }

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server, parameter_transformers
    ) as (test_server, client):
        # Get the list of available tools
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        # Verify the expected tools are available
        assert "example.hello_world" in tool_names
        assert "example.echo" in tool_names
        assert "example.count_to" in tool_names

        # Test hello_world operation
        response = await client.execute_tool("example.hello_world", {})
        assert "Hello, World!" in response.text

        # Test echo operation
        test_text = "Integration Test"
        response = await client.execute_tool(
            "example.echo", {"message": test_text}
        )
        assert f"Echo: {test_text}" in response.text

        # Test count_to operation
        test_number = 5
        response = await client.execute_tool(
            "example.count_to", {"number": test_number}
        )
        assert "1, 2, 3, 4, 5" in response.text


@pytest.mark.asyncio
async def test_schema_group_integration():
    """Test end-to-end functionality of SchemaGroup through MCP protocol."""
    # Load the JSON file
    config_path = CONFIG_DIR / "schema_group.json"
    with open(config_path) as f:
        config_data = json.load(f)

    # Create a ServiceConfig from the loaded data
    config = ServiceConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the group manually for testing
    schema_group = SchemaGroup()
    schema_group.config = GroupConfig(
        name="schema",
        description="Schema validation group for AutoMCP verification",
    )
    server.groups["schema"] = schema_group

    # Create a schema registry
    registry = SchemaRegistry()
    from automcp.schemas import common

    registry.register_all_from_module(common)

    # Create parameter transformers for schema group operations
    parameter_transformers = {
        "schema.greet_person": registry.create_transformer(
            "PersonSchema", "person"
        ),
        "schema.repeat_message": registry.create_transformer(
            "MessageSchema", "message"
        ),
        "schema.process_list": registry.create_transformer(
            "ListProcessingSchema", "data"
        ),
    }

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server, parameter_transformers
    ) as (test_server, client):
        # Get the list of available tools
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        # Verify the expected tools are available
        assert "schema.greet_person" in tool_names
        assert "schema.repeat_message" in tool_names
        assert "schema.process_list" in tool_names

        # Test greet_person operation
        person_data = {
            "name": "Integration Test",
            "age": 42,
            "email": "test@example.com",
        }
        response = await client.execute_tool(
            "schema.greet_person", person_data
        )
        assert "Hello, Integration Test!" in response.text
        assert "42 years old" in response.text
        assert "test@example.com" in response.text

        # Test process_list operation
        list_data = {
            "items": ["one", "two"],
            "prefix": "->",
            "uppercase": True,
        }
        response = await client.execute_tool("schema.process_list", list_data)
        assert "-> ONE" in response.text
        assert "-> TWO" in response.text

        # Test schema validation error
        invalid_data = {
            "name": "Test",
            "email": "test@example.com",
        }  # Missing required 'age'
        response = await client.execute_tool(
            "schema.greet_person", invalid_data
        )
        assert (
            "error" in response.text.lower()
            or "validation" in response.text.lower()
        )


@pytest.mark.asyncio
async def test_timeout_group_integration():
    """Test end-to-end functionality of TimeoutGroup through MCP protocol."""
    # Load the JSON file
    config_path = CONFIG_DIR / "timeout_group.json"
    with open(config_path) as f:
        config_data = json.load(f)

    # Create a ServiceConfig from the loaded data
    config = ServiceConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the group manually for testing
    timeout_group = TimeoutGroup()
    timeout_group.config = GroupConfig(
        name="timeout",
        description="Timeout testing group for AutoMCP verification",
    )
    server.groups["timeout"] = timeout_group

    # Create parameter transformers for timeout group operations
    parameter_transformers = {
        "timeout.sleep": FlatParameterTransformer(),
        "timeout.slow_counter": FlatParameterTransformer(),
        "timeout.cpu_intensive": FlatParameterTransformer(),
    }

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server, parameter_transformers
    ) as (test_server, client):
        # Get the list of available tools
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        # Verify the expected tools are available
        assert "timeout.sleep" in tool_names
        assert "timeout.slow_counter" in tool_names
        assert "timeout.cpu_intensive" in tool_names

        # Test sleep operation
        sleep_time = 0.2
        start_time = time.time()
        response = await client.execute_tool(
            "timeout.sleep", {"seconds": sleep_time}
        )
        elapsed = time.time() - start_time
        assert f"Slept for {sleep_time} seconds" in response.text
        assert (
            sleep_time <= elapsed <= sleep_time + 0.5
        )  # Allow small timing variance

        # Test slow_counter operation
        response = await client.execute_tool(
            "timeout.slow_counter", {"limit": 3, "delay": 0.1}
        )
        assert "Counted to 3" in response.text
        assert "1, 2, 3" in response.text

        # Test cpu_intensive operation with small iteration count
        response = await client.execute_tool(
            "timeout.cpu_intensive", {"iterations": 100}
        )
        assert "Completed 100 iterations" in response.text
        assert "result:" in response.text


@pytest.mark.asyncio
async def test_multi_group_integration():
    """Test end-to-end functionality of multiple groups through MCP protocol."""
    # Load the YAML file
    config_path = CONFIG_DIR / "multi_group.yaml"
    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    # Create a ServiceConfig from the loaded data
    config = ServiceConfig(**config_data)

    # Create server with the config
    server = AutoMCPServer("test-server", config)

    # Register the groups manually for testing
    example_group = ExampleGroup()
    example_group.config = GroupConfig(
        name="example",
        description="Basic example group for AutoMCP verification",
    )
    server.groups["example"] = example_group

    schema_group = SchemaGroup()
    schema_group.config = GroupConfig(
        name="schema",
        description="Schema validation group for AutoMCP verification",
    )
    server.groups["schema"] = schema_group

    timeout_group = TimeoutGroup()
    timeout_group.config = GroupConfig(
        name="timeout",
        description="Timeout testing group for AutoMCP verification",
    )
    server.groups["timeout"] = timeout_group

    # Create a schema registry
    registry = SchemaRegistry()
    from automcp.schemas import common

    registry.register_all_from_module(common)

    # Create parameter transformers for all operations
    parameter_transformers = {
        # Example group
        "example.hello_world": FlatParameterTransformer(),
        "example.echo": FlatParameterTransformer(),
        "example.count_to": FlatParameterTransformer(),
        # Schema group
        "schema.greet_person": registry.create_transformer(
            "PersonSchema", "person"
        ),
        "schema.repeat_message": registry.create_transformer(
            "MessageSchema", "message"
        ),
        "schema.process_list": registry.create_transformer(
            "ListProcessingSchema", "data"
        ),
        # Timeout group
        "timeout.sleep": FlatParameterTransformer(),
        "timeout.slow_counter": FlatParameterTransformer(),
        "timeout.cpu_intensive": FlatParameterTransformer(),
    }

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server, parameter_transformers
    ) as (test_server, client):
        # Get the list of available tools
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        # Verify tools from all groups are available
        example_tools = [
            name for name in tool_names if name.startswith("example.")
        ]
        schema_tools = [
            name for name in tool_names if name.startswith("schema.")
        ]
        timeout_tools = [
            name for name in tool_names if name.startswith("timeout.")
        ]

        assert len(example_tools) >= 3
        assert len(schema_tools) >= 3
        assert len(timeout_tools) >= 3

        # Test one operation from each group
        # Example group
        response = await client.execute_tool("example.hello_world", {})
        assert "Hello, World!" in response.text

        # Schema group
        person_data = {
            "name": "Multi Group",
            "age": 30,
            "email": "multi@example.com",
        }
        response = await client.execute_tool(
            "schema.greet_person", person_data
        )
        assert "Hello, Multi Group!" in response.text

        # Timeout group
        response = await client.execute_tool("timeout.sleep", {"seconds": 0.1})
        assert "Slept for 0.1 seconds" in response.text


@pytest.mark.asyncio
async def test_timeout_handling_integration():
    """Test timeout handling through MCP protocol."""
    # Load the JSON file
    config_path = CONFIG_DIR / "timeout_group.json"
    with open(config_path) as f:
        config_data = json.load(f)

    # Create a ServiceConfig from the loaded data
    config = ServiceConfig(**config_data)

    # Test with operation that completes before timeout
    server1 = AutoMCPServer("test-server", config, timeout=1.0)
    timeout_group1 = TimeoutGroup()
    timeout_group1.config = GroupConfig(
        name="timeout",
        description="Timeout testing group for AutoMCP verification",
    )
    server1.groups["timeout"] = timeout_group1

    # Create parameter transformers
    parameter_transformers = {
        "timeout.sleep": FlatParameterTransformer(),
    }

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server1, parameter_transformers
    ) as (test_server, client):
        # Test operation that completes before timeout
        response = await client.execute_tool("timeout.sleep", {"seconds": 0.2})
        assert "Slept for 0.2 seconds" in response.text

    # Test with operation that exceeds timeout
    server2 = AutoMCPServer("test-server", config, timeout=0.2)
    timeout_group2 = TimeoutGroup()
    timeout_group2.config = GroupConfig(
        name="timeout",
        description="Timeout testing group for AutoMCP verification",
    )
    server2.groups["timeout"] = timeout_group2

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server2, parameter_transformers
    ) as (test_server, client):
        # Test operation that exceeds timeout
        try:
            response = await client.execute_tool(
                "timeout.sleep", {"seconds": 1.0}
            )
            # If we get a response, it should indicate a timeout or error
            assert (
                "timeout" in response.text.lower()
                or "error" in response.text.lower()
            )
        except Exception as e:
            # If we get an exception, it should be related to timeout
            assert "timeout" in str(e).lower() or "error" in str(e).lower()


@pytest.mark.asyncio
async def test_specific_group_loading():
    """Test loading a specific group from multi-group config."""
    # Load the YAML file
    config_path = CONFIG_DIR / "multi_group.yaml"
    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    # Extract just the example group configuration
    example_group_config = {
        "name": "example",
        "description": "Basic example group for AutoMCP verification",
    }

    # Create a GroupConfig from the extracted data
    config = GroupConfig(**example_group_config)

    # Create server with the specific group config
    server = AutoMCPServer("test-server", config)

    # Register the example group manually for testing
    example_group = ExampleGroup()
    example_group.config = config  # Set the config attribute
    server.groups["example"] = example_group

    # Create parameter transformers
    parameter_transformers = {
        "example.hello_world": FlatParameterTransformer(),
        "example.echo": FlatParameterTransformer(),
        "example.count_to": FlatParameterTransformer(),
    }

    # Create a TestServer with the parameter transformers
    async with create_connected_server_and_client_session(
        server, parameter_transformers
    ) as (test_server, client):
        # Get the list of available tools
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        # Verify only example group tools are available
        example_tools = [
            name for name in tool_names if name.startswith("example.")
        ]
        schema_tools = [
            name for name in tool_names if name.startswith("schema.")
        ]
        timeout_tools = [
            name for name in tool_names if name.startswith("timeout.")
        ]

        assert len(example_tools) >= 3
        assert len(schema_tools) == 0
        assert len(timeout_tools) == 0

        # Test an example group operation
        response = await client.execute_tool("example.hello_world", {})
        assert "Hello, World!" in response.text
