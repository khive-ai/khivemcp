"""
Server runner module for AutoMCP.

This module provides the main entry point for running AutoMCP servers,
handling configuration loading, server lifecycle, and error handling.
"""

import asyncio
from pathlib import Path
from typing import Optional

import mcp.server.stdio

from .config import load_config
from .exceptions import AutoMCPError, ConfigFormatError, ConfigNotFoundError
from .server import AutoMCPServer


def run_server(config_path: Path, timeout: float = 30.0) -> None:
    """
    Run an AutoMCP server with the specified configuration.

    This is the main entry point for running an AutoMCP server. It loads the
    configuration from the specified path, creates and starts the server,
    and handles the server lifecycle until termination.

    Args:
        config_path: Path to the configuration file (YAML or JSON)
        timeout: Operation timeout in seconds (default: 30.0)

    Raises:
        ConfigNotFoundError: If the configuration file does not exist
        ConfigFormatError: If the configuration file has invalid format
        ServerError: If there's an error during server initialization or execution
    """
    try:
        # Run the async implementation with asyncio.run
        asyncio.run(_run_server_async(config_path, timeout))
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nServer stopped by user")
    except ConfigNotFoundError:
        # Re-raise specific exceptions without wrapping
        raise
    except ConfigFormatError:
        # Re-raise specific exceptions without wrapping
        raise
    except Exception as e:
        # Wrap other exceptions in AutoMCPError
        raise AutoMCPError(f"Error running server: {e}") from e


async def _run_server_async(config_path: Path, timeout: float = 30.0) -> None:
    """
    Async implementation of run_server.

    This function loads the configuration, creates the server instance,
    and manages the server lifecycle.

    Args:
        config_path: Path to the configuration file (YAML or JSON)
        timeout: Operation timeout in seconds (default: 30.0)

    Raises:
        ConfigNotFoundError: If the configuration file does not exist
        ConfigFormatError: If the configuration file has invalid format
        ServerError: If there's an error during server initialization or execution
    """
    # Load configuration
    config = load_config(config_path)

    # Determine server name from config
    if hasattr(config, "name"):
        server_name = config.name
    else:
        # Use filename as fallback
        server_name = config_path.stem

    # Create server instance
    server = AutoMCPServer(server_name, config, timeout=timeout)

    try:
        # Start the server
        print(
            f"Starting AutoMCP server '{server_name}' with configuration: {config_path}"
        )
        await server.start()
        print("Server running. Press Ctrl+C to stop.")

        # Keep the server running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # This will be caught by the outer run_server function
        raise
    except Exception as e:
        print(f"Error during server execution: {e}")
        raise
    finally:
        # Ensure server is properly stopped
        await server.stop()
        print("Server stopped")
