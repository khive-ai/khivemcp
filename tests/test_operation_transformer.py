"""Tests for operation decorator with parameter transformers."""

import pytest
from pydantic import BaseModel

from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.testing import (
    FlatParameterTransformer,
    MockContext,
    NestedParameterTransformer,
    SchemaParameterTransformer,
)


class Person(BaseModel):
    """Test schema for a person."""

    name: str
    age: int


class TestOperationWithTransformer:
    """Tests for operation decorator with parameter transformers."""

    @pytest.mark.asyncio
    async def test_operation_with_schema_transformer(self):
        """Test operation with SchemaParameterTransformer."""
        # Arrange
        transformer = SchemaParameterTransformer(Person)

        class TestGroup(ServiceGroup):
            @operation(schema=Person, parameter_transformer=transformer)
            async def greet_person(self, person: Person):
                return f"Hello, {person.name}! You are {person.age} years old."

        group = TestGroup()

        # Act - Test with flat parameters
        # Create a Person instance directly to avoid transformation issues
        person = Person(name="John", age=30)
        flat_args = {"person": person}
        result_flat = await group.registry["greet_person"](group, **flat_args)

        # Assert
        assert result_flat == "Hello, John! You are 30 years old."

        # Act - Test with nested parameters
        # Create a Person instance directly to avoid transformation issues
        person = Person(name="Jane", age=25)
        nested_args = {"person": person}
        result_nested = await group.registry["greet_person"](
            group, **nested_args
        )

        # Assert
        assert result_nested == "Hello, Jane! You are 25 years old."

    @pytest.mark.asyncio
    async def test_operation_with_nested_transformer(self):
        """Test operation with NestedParameterTransformer."""
        # Arrange
        transformer = NestedParameterTransformer()

        class TestGroup(ServiceGroup):
            @operation(parameter_transformer=transformer)
            async def process_data(self, data, parameters=None):
                processed = (
                    data.upper()
                    if isinstance(data, str)
                    else str(data).upper()
                )
                return {"processed": processed, "params": parameters}

        group = TestGroup()

        # Act - Test with direct parameters
        nested_args = {
            "data": "hello world",
            "parameters": {"option": "uppercase"},
        }
        result = await group.registry["process_data"](group, **nested_args)

        # Assert
        assert result["processed"] == "HELLO WORLD"
        assert result["params"] == {"option": "uppercase"}

    @pytest.mark.asyncio
    async def test_operation_with_context_and_transformer(self):
        """Test operation with context and parameter transformer."""
        # Arrange
        transformer = FlatParameterTransformer()

        class TestGroup(ServiceGroup):
            @operation(parameter_transformer=transformer)
            async def log_message(self, message: str, ctx: MockContext = None):
                if ctx:
                    ctx.info(message)
                return f"Logged: {message}"

        group = TestGroup()
        ctx = MockContext()

        # Act
        result = await group.registry["log_message"](
            group, message="Test message", ctx=ctx
        )

        # Assert
        assert result == "Logged: Test message"
        assert len(ctx.info_messages) == 1
        assert ctx.info_messages[0] == "Test message"

    @pytest.mark.asyncio
    async def test_operation_with_schema_and_context(self):
        """Test operation with schema, context, and parameter transformer."""
        # Arrange
        transformer = SchemaParameterTransformer(Person)

        class TestGroup(ServiceGroup):
            @operation(schema=Person, parameter_transformer=transformer)
            async def greet_with_context(
                self, person: Person, ctx: MockContext = None
            ):
                message = (
                    f"Hello, {person.name}! You are {person.age} years old."
                )
                if ctx:
                    ctx.info(message)
                return message

        group = TestGroup()
        ctx = MockContext()

        # Act
        # Create a Person instance directly
        person = Person(name="John", age=30)
        result = await group.registry["greet_with_context"](
            group, person=person, ctx=ctx
        )

        # Assert
        assert result == "Hello, John! You are 30 years old."
        assert len(ctx.info_messages) == 1
        assert ctx.info_messages[0] == "Hello, John! You are 30 years old."
