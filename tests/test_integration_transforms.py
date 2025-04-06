"""Integration tests for parameter transformers with AutoMCP server."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

import anyio
import pytest
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)
from mcp.client.session import ClientSession
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import JSONRPCMessage, TextContent
from pydantic import BaseModel

from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.server import AutoMCPServer
from automcp.testing import (
    FlatParameterTransformer,
    NestedParameterTransformer,
    SchemaParameterTransformer,
)
from automcp.types import GroupConfig

# Define a type for message streams
MessageStream = tuple[
    MemoryObjectReceiveStream[JSONRPCMessage | Exception],
    MemoryObjectSendStream[JSONRPCMessage],
]


@contextlib.asynccontextmanager
async def create_client_server_memory_streams() -> (
    AsyncGenerator[tuple[MessageStream, MessageStream], None]
):
    """
    Creates a pair of bidirectional memory streams for client-server communication.

    Returns:
        A tuple of (client_streams, server_streams) where each is a tuple of
        (read_stream, write_stream)
    """
    # Create streams for both directions
    server_to_client_send, server_to_client_receive = (
        anyio.create_memory_object_stream[JSONRPCMessage | Exception](1)
    )
    client_to_server_send, client_to_server_receive = (
        anyio.create_memory_object_stream[JSONRPCMessage | Exception](1)
    )

    client_streams = (server_to_client_receive, client_to_server_send)
    server_streams = (client_to_server_receive, server_to_client_send)

    async with (
        server_to_client_receive,
        client_to_server_send,
        client_to_server_receive,
        server_to_client_send,
    ):
        yield client_streams, server_streams


@contextlib.asynccontextmanager
async def create_connected_server_and_client_session(
    server: AutoMCPServer,
    parameter_transformers: Dict[str, Any] = None,
    read_timeout_seconds: timedelta | None = None,
) -> AsyncGenerator[tuple[AutoMCPServer, ClientSession], None]:
    """
    Creates a ClientSession that is connected to a running AutoMCP server.

    Args:
        server: The AutoMCPServer instance to connect to
        parameter_transformers: Optional dictionary mapping operation names to
            parameter transformers for custom parameter handling
        read_timeout_seconds: Optional timeout for read operations

    Returns:
        A tuple of (server, client_session)
    """
    async with create_client_server_memory_streams() as (
        client_streams,
        server_streams,
    ):
        client_read, client_write = client_streams
        server_read, server_write = server_streams

        # Create a cancel scope for the server task
        async with anyio.create_task_group() as tg:
            # Start the server's internal MCP server
            async def run_server():
                # Prior to running, ensure all tools are registered
                for group_name, group in server.groups.items():
                    for op_name, operation in group.registry.items():
                        try:
                            tool_name = f"{group_name}.{op_name}"

                            # Check if we have a parameter transformer for this operation
                            transformer = None
                            if parameter_transformers:
                                transformer = parameter_transformers.get(
                                    tool_name
                                )

                            # If the operation has a transformer defined, use that
                            if (
                                hasattr(operation, "parameter_transformer")
                                and operation.parameter_transformer
                            ):
                                transformer = operation.parameter_transformer

                            # Create a handler function that uses the transformer
                            async def handler(
                                arguments: dict | None = None,
                                ctx: TextContent = None,
                            ) -> TextContent:
                                try:
                                    # Transform parameters if needed
                                    transformed_args = arguments or {}
                                    if transformer:
                                        transformed_args = (
                                            await transformer.transform(
                                                op_name, transformed_args, ctx
                                            )
                                        )

                                    # Add context if needed
                                    if (
                                        hasattr(operation, "requires_context")
                                        and operation.requires_context
                                    ):
                                        transformed_args["ctx"] = ctx

                                    # Execute operation
                                    result = await group.registry[op_name](
                                        group, **transformed_args
                                    )

                                    # Convert result to TextContent
                                    response_text = ""
                                    if isinstance(result, BaseModel):
                                        response_text = (
                                            result.model_dump_json()
                                        )
                                    elif isinstance(result, (dict, list)):
                                        import json

                                        response_text = json.dumps(result)
                                    elif result is not None:
                                        response_text = str(result)

                                    return TextContent(
                                        type="text", text=response_text
                                    )

                                except Exception as e:
                                    error_msg = f"Error during '{op_name}' execution: {str(e)}"
                                    import logging

                                    logging.exception(error_msg)
                                    return TextContent(
                                        type="text", text=error_msg
                                    )

                            # Register the handler with the server
                            server.server.add_tool(
                                handler,
                                name=tool_name,
                                description=operation.doc
                                or f"Operation {op_name} in group {group_name}",
                            )
                        except Exception as e:
                            print(
                                f"Warning: Failed to register tool {tool_name}: {str(e)}"
                            )

                # Use the _mcp_server attribute which has the run method that accepts the streams
                await server.server._mcp_server.run(
                    server_read,
                    server_write,
                    InitializationOptions(
                        server_name=server.name,
                        server_version="1.0.0",
                        capabilities=server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )

            tg.start_soon(run_server)

            try:
                # Create and initialize the client session
                async with ClientSession(
                    read_stream=client_read,
                    write_stream=client_write,
                    read_timeout_seconds=read_timeout_seconds,
                ) as client_session:
                    await client_session.initialize()
                    yield server, client_session
            finally:
                tg.cancel_scope.cancel()


class Person(BaseModel):
    """Test schema for a person."""

    name: str
    age: int


class TestGroup(ServiceGroup):
    """Test service group with operations using parameter transformers."""

    @operation(
        schema=Person, parameter_transformer=SchemaParameterTransformer(Person)
    )
    async def greet_person(self, person: Person):
        """Greet a person with their name and age."""
        return f"Hello, {person.name}! You are {person.age} years old."

    @operation(parameter_transformer=NestedParameterTransformer())
    async def process_data(self, data, parameters=None):
        """Process data with optional parameters."""
        processed = (
            data.upper() if isinstance(data, str) else str(data).upper()
        )
        return {"processed": processed, "params": parameters}

    @operation(parameter_transformer=FlatParameterTransformer())
    async def simple_operation(self, message: str):
        """Simple operation with flat parameters."""
        return f"Message: {message}"


class TestIntegrationWithTransformers:
    """Integration tests for parameter transformers with AutoMCP server."""

    @pytest.mark.asyncio
    async def test_schema_transformer_integration(self):
        """Test integration with SchemaParameterTransformer."""
        # Arrange
        group_config = GroupConfig(name="test-group")
        server = AutoMCPServer("test-server", group_config)
        server.groups["test-group"] = TestGroup()

        async with create_connected_server_and_client_session(server) as (
            _,
            client,
        ):
            # Act - Test with flat parameters
            flat_result = await client.call_tool(
                "test-group.greet_person", {"name": "John", "age": 30}
            )

            # Assert
            assert (
                flat_result.content[0].text
                == "Hello, John! You are 30 years old."
            )

            # Act - Test with nested parameters
            nested_result = await client.call_tool(
                "test-group.greet_person",
                {"person": {"name": "Jane", "age": 25}},
            )

            # Assert
            assert (
                nested_result.content[0].text
                == "Hello, Jane! You are 25 years old."
            )

    @pytest.mark.asyncio
    async def test_nested_transformer_integration(self):
        """Test integration with NestedParameterTransformer."""
        # Arrange
        group_config = GroupConfig(name="test-group")
        server = AutoMCPServer("test-server", group_config)
        server.groups["test-group"] = TestGroup()

        async with create_connected_server_and_client_session(server) as (
            _,
            client,
        ):
            # Act - Test with nested parameters
            result = await client.call_tool(
                "test-group.process_data",
                {
                    "process_data": {
                        "data": "hello world",
                        "parameters": {"option": "uppercase"},
                    }
                },
            )

            # Assert
            import json

            data = json.loads(result.content[0].text)
            assert data["processed"] == "HELLO WORLD"
            assert data["params"] == {"option": "uppercase"}

    @pytest.mark.asyncio
    async def test_flat_transformer_integration(self):
        """Test integration with FlatParameterTransformer."""
        # Arrange
        group_config = GroupConfig(name="test-group")
        server = AutoMCPServer("test-server", group_config)
        server.groups["test-group"] = TestGroup()

        async with create_connected_server_and_client_session(server) as (
            _,
            client,
        ):
            # Act
            result = await client.call_tool(
                "test-group.simple_operation", {"message": "Test message"}
            )

            # Assert
            assert result.content[0].text == "Message: Test message"
