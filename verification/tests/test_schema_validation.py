"""Tests for schema validation in AutoMCP operations using the new testing infrastructure."""

import pytest
from pydantic import ValidationError

from automcp.schemas import ListProcessingSchema, MessageSchema, PersonSchema
from automcp.schemas.registry import SchemaRegistry
from automcp.server import AutoMCPServer
from automcp.testing.context import MockContext
from automcp.testing.server import TestServer
from automcp.testing.transforms import SchemaParameterTransformer
from automcp.types import ExecutionRequest, GroupConfig, ServiceRequest
from verification.groups.schema_group import SchemaGroup


@pytest.mark.asyncio
async def test_schema_validation_success():
    """Test successful schema validation for operations using the Schema Registry and TestServer."""
    # Create a schema registry and register our schemas
    registry = SchemaRegistry()
    registry.register(PersonSchema)
    registry.register(MessageSchema)
    registry.register(ListProcessingSchema)

    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)

    # Create a schema group with a mock context
    schema_group = SchemaGroup()
    server.groups["schema"] = schema_group

    # Create parameter transformers for each schema
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

    # Create a test server with the parameter transformers
    test_server = TestServer(server, parameter_transformers)

    # Test PersonSchema validation with the test server
    async with test_server.create_client_session() as client:
        person_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
        }
        result = await client.execute_tool("schema.greet_person", person_data)
        assert "Hello, John Doe!" in result.text
        assert "30 years old" in result.text
        assert "john@example.com" in result.text

        # Test nested format for PersonSchema
        nested_person_data = {
            "person": {
                "name": "Jane Doe",
                "age": 25,
                "email": "jane@example.com",
            }
        }
        result = await client.execute_tool(
            "schema.greet_person", nested_person_data
        )
        assert "Hello, Jane Doe!" in result.text
        assert "25 years old" in result.text
        assert "jane@example.com" in result.text

    # Test MessageSchema validation with the test server
    async with test_server.create_client_session() as client:
        message_data = {"text": "Hello", "repeat": 3}
        result = await client.execute_tool(
            "schema.repeat_message", message_data
        )
        assert "Hello Hello Hello" in result.text

        # Test nested format for MessageSchema
        nested_message_data = {"message": {"text": "World", "repeat": 2}}
        result = await client.execute_tool(
            "schema.repeat_message", nested_message_data
        )
        assert "World World" in result.text

    # Test ListProcessingSchema validation with the test server
    async with test_server.create_client_session() as client:
        list_data = {
            "items": ["apple", "banana", "cherry"],
            "prefix": "Fruit:",
            "uppercase": True,
        }
        result = await client.execute_tool("schema.process_list", list_data)
        result_json = result.text.strip("[]").replace('"', "").split(",")
        assert "Fruit: APPLE" in result_json[0]
        assert "Fruit: BANANA" in result_json[1]
        assert "Fruit: CHERRY" in result_json[2]

        # Test nested format for ListProcessingSchema
        nested_list_data = {
            "data": {
                "items": ["dog", "cat", "bird"],
                "prefix": "Animal:",
                "uppercase": True,
            }
        }
        result = await client.execute_tool(
            "schema.process_list", nested_list_data
        )
        result_json = result.text.strip("[]").replace('"', "").split(",")
        assert "Animal: DOG" in result_json[0]
        assert "Animal: CAT" in result_json[1]
        assert "Animal: BIRD" in result_json[2]


@pytest.mark.asyncio
async def test_schema_validation_failure():
    """Test schema validation failure using the TestServer."""
    # Create a schema registry and register our schemas
    registry = SchemaRegistry()
    registry.register(PersonSchema)
    registry.register(MessageSchema)
    registry.register(ListProcessingSchema)

    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)
    server.groups["schema"] = SchemaGroup()

    # Create parameter transformers for each schema
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

    # Create a test server with the parameter transformers
    test_server = TestServer(server, parameter_transformers)

    # Test missing required field in PersonSchema
    async with test_server.create_client_session() as client:
        invalid_person_data = {
            "name": "John Doe"
        }  # Missing required 'age' field
        result = await client.execute_tool(
            "schema.greet_person", invalid_person_data
        )
        assert (
            "error" in result.text.lower()
            or "validation" in result.text.lower()
        )

        # Test invalid field type in PersonSchema
        invalid_person_data = {
            "name": "John Doe",
            "age": "thirty",  # Age should be an integer
        }
        result = await client.execute_tool(
            "schema.greet_person", invalid_person_data
        )
        assert (
            "error" in result.text.lower()
            or "validation" in result.text.lower()
        )

        # Test value out of range in MessageSchema
        invalid_message_data = {
            "text": "Hello",
            "repeat": 15,  # repeat must be <= 10
        }
        result = await client.execute_tool(
            "schema.repeat_message", invalid_message_data
        )
        assert (
            "error" in result.text.lower()
            or "validation" in result.text.lower()
        )


@pytest.mark.asyncio
async def test_schema_optional_fields():
    """Test schema validation with optional fields using the TestServer."""
    # Create a schema registry and register our schemas
    registry = SchemaRegistry()
    registry.register(PersonSchema)
    registry.register(MessageSchema)
    registry.register(ListProcessingSchema)

    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)

    # Create a schema group
    schema_group = SchemaGroup()
    server.groups["schema"] = schema_group

    # Create parameter transformers for each schema
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

    # Create a test server with the parameter transformers
    test_server = TestServer(server, parameter_transformers)

    # Test PersonSchema with optional email omitted
    async with test_server.create_client_session() as client:
        person_data = {"name": "John Doe", "age": 30}  # No email
        result = await client.execute_tool("schema.greet_person", person_data)
        assert "Hello, John Doe!" in result.text
        assert "30 years old" in result.text
        assert "email" not in result.text.lower()

        # Test ListProcessingSchema with default values
        list_data = {"items": ["apple", "banana"]}  # No prefix or uppercase
        result = await client.execute_tool("schema.process_list", list_data)
        result_json = result.text.strip("[]").replace('"', "").split(",")
        assert "Item: apple" in result_json[0]
        assert "Item: banana" in result_json[1]


@pytest.mark.asyncio
async def test_direct_schema_validation():
    """Test direct schema validation with Pydantic models."""
    # Test valid PersonSchema
    valid_person = PersonSchema(
        name="John Doe", age=30, email="john@example.com"
    )
    assert valid_person.name == "John Doe"
    assert valid_person.age == 30
    assert valid_person.email == "john@example.com"

    # Test PersonSchema with missing required field
    with pytest.raises(ValidationError):
        PersonSchema(name="John Doe")  # Missing required 'age' field

    # Test MessageSchema with value out of range
    with pytest.raises(ValidationError):
        MessageSchema(text="Hello", repeat=15)  # repeat must be <= 10

    # Test ListProcessingSchema with default values
    list_schema = ListProcessingSchema(items=["apple", "banana"])
    assert list_schema.prefix == "Item:"
    assert list_schema.uppercase is False
