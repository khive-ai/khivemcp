"""
AutoMCP Client Utilities

This module provides client utilities for connecting to and using AutoMCP servers.
It includes helper functions for creating connections, calling operations,
and parsing responses.
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, TypeVar, Union

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Define a console for rich output
console = Console()

# Type variable for generic response parsing
T = TypeVar("T")


class ProgressUpdate(NamedTuple):
    """Simple progress update container."""

    current: int
    total: int


async def create_client_connection(
    command: str, args: List[str], connect_timeout: float = 10.0
) -> Tuple[ClientSession, List[str]]:
    """
    Create a connection to an AutoMCP server using the MCP protocol.

    Args:
        command: The command to run the server
        args: Arguments to pass to the command
        connect_timeout: Timeout for connection in seconds

    Returns:
        A tuple of (client_session, available_tools)
    """
    # Create server parameters
    server_params = StdioServerParameters(command=command, args=args)

    try:
        # Connect to the server using stdio
        read_stream, write_stream = await asyncio.wait_for(
            stdio_client(server_params).__aenter__(), connect_timeout
        )

        # Create client session
        client = ClientSession(read_stream, write_stream)

        # Initialize the connection
        await client.initialize()

        # Get the list of available tools
        tools_result = await client.list_tools()
        available_tools = [tool.name for tool in tools_result.tools]

        return client, available_tools

    except asyncio.TimeoutError:
        raise TimeoutError(f"Timed out connecting to server after {connect_timeout}s")
    except Exception as e:
        raise ConnectionError(f"Failed to connect to AutoMCP server: {str(e)}")


async def connect_to_automcp_server(
    config_path: Union[str, Path], timeout: float = 30.0
) -> Tuple[ClientSession, List[str]]:
    """
    Connect to an AutoMCP server using a configuration file.

    Args:
        config_path: Path to the server configuration file
        timeout: Operation timeout in seconds

    Returns:
        A tuple of (client_session, available_tools)
    """
    config_path_str = str(config_path) if isinstance(config_path, Path) else config_path

    # Use the automcp CLI to start the server
    return await create_client_connection(
        command=sys.executable,
        args=["-m", "automcp.cli", "run", config_path_str, "--timeout", str(timeout)],
    )


async def call_operation(
    client: ClientSession,
    operation_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    show_progress: bool = True,
) -> Any:
    """
    Call an operation on an AutoMCP server.

    Args:
        client: The MCP client session
        operation_name: Name of the operation to call (with group prefix)
        arguments: Arguments to pass to the operation
        show_progress: Whether to show a progress spinner

    Returns:
        The raw ToolCallResponse from the MCP protocol
    """
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn(f"Calling {operation_name}..."),
        ) as progress:
            task = progress.add_task("", total=None)
            response = await client.call_tool(operation_name, arguments or {})
            progress.update(task, completed=True)
    else:
        response = await client.call_tool(operation_name, arguments or {})

    return response


def parse_text_response(response: Any) -> str:
    """
    Extract the text content from a tool call response.

    Args:
        response: The ToolCallResponse object

    Returns:
        The text content of the response
    """
    if not response.content:
        return ""

    return response.content[0].text if response.content[0].text is not None else ""


def parse_json_response(response: Any) -> Dict[str, Any]:
    """
    Parse a JSON response from a tool call.

    Args:
        response: The ToolCallResponse object

    Returns:
        The parsed JSON data
    """
    text = parse_text_response(response)
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to handle the case where the response is a Python dict representation
        try:
            # Using literal_eval is safer than eval
            from ast import literal_eval

            return literal_eval(text)
        except (SyntaxError, ValueError):
            raise ValueError(f"Response is not valid JSON or Python dict: {text}")


def parse_model_response(response: Any, model_class: type[T]) -> T:
    """
    Parse a response into a Pydantic model.

    Args:
        response: The ToolCallResponse object
        model_class: The Pydantic model class to parse into

    Returns:
        An instance of the model_class
    """
    if not issubclass(model_class, BaseModel):
        raise TypeError(
            f"model_class must be a Pydantic BaseModel subclass, got {model_class}"
        )

    # Get the JSON data
    data = parse_json_response(response)

    # Parse into the model
    return model_class.model_validate(data)


async def list_operations(client: ClientSession) -> Dict[str, Dict[str, Any]]:
    """
    List all available operations on the server with their details.

    Args:
        client: The MCP client session

    Returns:
        A dictionary mapping operation names to their details
    """
    tools_result = await client.list_tools()

    # Create a dict of operation details
    operations = {}
    for tool in tools_result.tools:
        operations[tool.name] = {
            "description": tool.description,
            "schema": tool.inputSchema,
        }

    return operations


async def safe_call(
    client: ClientSession,
    operation_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    retries: int = 0,
    retry_delay: float = 1.0,
) -> Tuple[Optional[Any], Optional[Exception]]:
    """
    Safely call an operation, catching and returning any exceptions.

    Args:
        client: The MCP client session
        operation_name: Name of the operation to call
        arguments: Arguments to pass to the operation
        retries: Number of retries if the call fails
        retry_delay: Delay between retries in seconds

    Returns:
        A tuple of (response, exception) where one is None
    """
    for attempt in range(retries + 1):
        try:
            response = await call_operation(
                client,
                operation_name,
                arguments,
                show_progress=(attempt == 0),  # Only show progress on first attempt
            )
            return response, None
        except Exception as e:
            if attempt < retries:
                # Sleep and retry
                await asyncio.sleep(retry_delay)
                continue
            else:
                # Final attempt failed
                return None, e


class AutoMCPClient:
    """A high-level client for interacting with AutoMCP servers."""

    def __init__(self, session: ClientSession, available_tools: List[str]):
        """
        Initialize the client.

        Args:
            session: The MCP client session
            available_tools: List of available tool names
        """
        self.session = session
        self.available_tools = available_tools
        self.console = Console()

    @classmethod
    async def connect(
        cls, config_path: Union[str, Path], timeout: float = 30.0
    ) -> "AutoMCPClient":
        """
        Create a client by connecting to an AutoMCP server.

        Args:
            config_path: Path to the server configuration file
            timeout: Operation timeout in seconds

        Returns:
            An AutoMCPClient instance
        """
        session, tools = await connect_to_automcp_server(config_path, timeout)
        return cls(session, tools)

    async def call(
        self,
        operation_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        model_class: Optional[type[T]] = None,
    ) -> Union[str, Dict[str, Any], T]:
        """
        Call an operation and parse the response.

        Args:
            operation_name: Name of the operation to call
            arguments: Arguments to pass to the operation
            model_class: Optional Pydantic model class to parse the response into

        Returns:
            The parsed response (str, dict, or model instance depending on model_class)
        """
        if operation_name not in self.available_tools:
            raise ValueError(
                f"Operation {operation_name} not available. Available operations: {', '.join(self.available_tools)}"
            )

        response = await call_operation(self.session, operation_name, arguments)

        if model_class:
            return parse_model_response(response, model_class)

        # Try to parse as JSON first
        try:
            return parse_json_response(response)
        except ValueError:
            # If not JSON, return as text
            return parse_text_response(response)

    async def list_tools(self) -> List[str]:
        """
        List all available tools provided by the server.

        Returns:
            A list of tool names
        """
        tools_result = await self.session.list_tools()
        return [tool.name for tool in tools_result.tools]

    async def get_tool_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about all available tools.

        Returns:
            A dictionary mapping tool names to their details (description and schema)
        """
        tools_result = await self.session.list_tools()

        # Create a dict of tool details
        tool_details = {}
        for tool in tools_result.tools:
            tool_details[tool.name] = {
                "description": tool.description,
                "schema": tool.inputSchema,
            }

        return tool_details

    async def close(self):
        """Close the client connection."""
        try:
            await self.session.shutdown()
        except Exception:
            # Ignore errors on shutdown
            pass
