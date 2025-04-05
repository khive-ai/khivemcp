"""Tests for schema validation in AutoMCP operations."""

import pytest
from mcp.types import TextContent
from pydantic import ValidationError

from automcp.server import AutoMCPServer
from automcp.types import ExecutionRequest, GroupConfig, ServiceRequest
from verification.groups.schema_group import SchemaGroup
from verification.schemas import ListProcessingSchema, MessageSchema, PersonSchema


class MockContext(TextContent):
    """Mock context for testing operations with progress reporting."""

    def __init__(self):
        super().__init__(type="text", text="")
        self.progress_updates = []
        self.info_messages = []

    def info(self, message):
        """Record an info message."""
        self.info_messages.append(message)

    async def report_progress(self, current, total):
        """Record a progress update."""
        self.progress_updates.append((current, total))


@pytest.mark.asyncio
async def test_schema_validation_success():
    """Test successful schema validation for operations."""
    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)

    # Create a schema group with a mock context
    schema_group = SchemaGroup()
    server.groups["schema"] = schema_group

    # Test PersonSchema validation directly
    person_data = {"name": "John Doe", "age": 30, "email": "john@example.com"}
    result = await schema_group.greet_person(**person_data)
    assert "Hello, John Doe!" in result
    assert "30 years old" in result
    assert "john@example.com" in result

    # Test MessageSchema validation directly
    ctx = MockContext()
    message_data = {"text": "Hello", "repeat": 3}
    result = await schema_group.repeat_message(**message_data, ctx=ctx)
    assert "Hello Hello Hello" in result

    # Test ListProcessingSchema validation directly
    list_data = {
        "items": ["apple", "banana", "cherry"],
        "prefix": "Fruit:",
        "uppercase": True,
    }
    result = await schema_group.process_list(**list_data)
    assert "Fruit: APPLE" in result[0]
    assert "Fruit: BANANA" in result[1]
    assert "Fruit: CHERRY" in result[2]


@pytest.mark.asyncio
async def test_schema_validation_failure():
    """Test schema validation failure for operations."""
    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)
    server.groups["schema"] = SchemaGroup()

    # Test missing required field in PersonSchema
    invalid_person_data = {"name": "John Doe"}  # Missing required 'age' field
    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="greet_person", arguments=invalid_person_data)
        ]
    )

    # The server should handle the validation error and return an error response
    result = await server._handle_service_request("schema", request)
    assert (
        "error" in result.content.text.lower()
        or "validation" in result.content.text.lower()
    )

    # Test invalid field type in PersonSchema
    invalid_person_data = {
        "name": "John Doe",
        "age": "thirty",
    }  # Age should be an integer
    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="greet_person", arguments=invalid_person_data)
        ]
    )

    result = await server._handle_service_request("schema", request)
    assert (
        "error" in result.content.text.lower()
        or "validation" in result.content.text.lower()
    )

    # Test value out of range in MessageSchema
    invalid_message_data = {"text": "Hello", "repeat": 15}  # repeat must be <= 10
    request = ServiceRequest(
        requests=[
            ExecutionRequest(operation="repeat_message", arguments=invalid_message_data)
        ]
    )

    result = await server._handle_service_request("schema", request)
    assert (
        "error" in result.content.text.lower()
        or "validation" in result.content.text.lower()
    )


@pytest.mark.asyncio
async def test_schema_optional_fields():
    """Test schema validation with optional fields."""
    # Create a server with the SchemaGroup
    config = GroupConfig(name="schema", description="Schema group")
    server = AutoMCPServer("test-server", config)

    # Create a schema group
    schema_group = SchemaGroup()
    server.groups["schema"] = schema_group

    # Test PersonSchema with optional email omitted
    person_data = {"name": "John Doe", "age": 30}  # No email
    result = await schema_group.greet_person(**person_data)
    assert "Hello, John Doe!" in result
    assert "30 years old" in result
    assert "email" not in result.lower()

    # Test ListProcessingSchema with default values
    list_data = {"items": ["apple", "banana"]}  # No prefix or uppercase
    result = await schema_group.process_list(**list_data)
    assert "Item: apple" in result[0]
    assert "Item: banana" in result[1]


@pytest.mark.asyncio
async def test_direct_schema_validation():
    """Test direct schema validation with Pydantic models."""
    # Test valid PersonSchema
    valid_person = PersonSchema(name="John Doe", age=30, email="john@example.com")
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
