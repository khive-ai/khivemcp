#!/usr/bin/env python3
"""
AutoMCP Server Template

This script provides a template for creating standalone AutoMCP servers.
Users can adapt this template to their own needs by:

1. Changing the configuration path
2. Customizing how ServiceGroups are loaded
3. Adding custom initialization logic
4. Modifying server settings

Usage:
    python -m automcp.cli.server_template path/to/config.yaml
    python -m automcp.cli.server_template path/to/config.json --group my-group
"""

import argparse
import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from automcp.group import ServiceGroup
from automcp.server import AutoMCPServer
from automcp.types import GroupConfig, ServiceConfig
from automcp.utils import load_config


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run an AutoMCP server")
    parser.add_argument("config", help="Path to config file (YAML/JSON)")
    parser.add_argument(
        "--group", "-g", help="Specific group to run from service config"
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=30.0,
        help="Operation timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["stdio", "http", "socket", "ws"],
        default="stdio",
        help="Server communication mode (default: stdio)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port for HTTP, WebSocket, or Socket mode (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP, WebSocket, or Socket mode (default: 127.0.0.1)",
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def import_group_class(class_path: str) -> Type[ServiceGroup]:
    """
    Import a ServiceGroup class from a module path string.

    Args:
        class_path: Module and class path in the format 'module.path:ClassName'

    Returns:
        The ServiceGroup class

    Raises:
        ImportError: If the module or class cannot be imported
        TypeError: If the imported class is not a ServiceGroup subclass
    """
    try:
        module_path, class_name = class_path.split(":")
        module = importlib.import_module(module_path)
        group_cls = getattr(module, class_name)

        # Validate that it's a ServiceGroup subclass
        if not issubclass(group_cls, ServiceGroup):
            raise TypeError(f"{class_path} is not a ServiceGroup subclass")

        return group_cls

    except (ValueError, ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import {class_path}: {e}")


def load_groups(config: ServiceConfig) -> Dict[str, ServiceGroup]:
    """
    Load ServiceGroup instances from a service configuration.

    Args:
        config: The service configuration containing group configurations

    Returns:
        A dictionary mapping group names to ServiceGroup instances

    Raises:
        RuntimeError: If a group initialization fails
    """
    groups = {}

    for class_path, group_config in config.groups.items():
        try:
            # Import group class from path
            group_cls = import_group_class(class_path)

            # Initialize group with config
            group = group_cls()
            group.config = group_config

            groups[group_config.name] = group

        except (ImportError, TypeError) as e:
            raise RuntimeError(f"Failed to initialize group {class_path}: {e}")

    return groups


def print_available_tools(server: AutoMCPServer) -> None:
    """
    Print available tools to stderr for debugging.

    Args:
        server: The AutoMCPServer instance
    """
    print("Available tools:", file=sys.stderr)
    for group_name, group in server.groups.items():
        for op_name in group.registry.keys():
            print(f"  - {group_name}.{op_name}", file=sys.stderr)


def configure_server_mode(mode: str, host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Configure the server communication mode.

    Args:
        mode: Server mode (stdio, http, socket, ws)
        host: Host for HTTP, WebSocket, or Socket mode
        port: Port for HTTP, WebSocket, or Socket mode
    """
    if mode == "stdio":
        os.environ["AUTOMCP_SERVER_MODE"] = "stdio"
    elif mode == "http":
        os.environ["AUTOMCP_SERVER_MODE"] = "http"
        os.environ["AUTOMCP_SERVER_HOST"] = host
        os.environ["AUTOMCP_SERVER_PORT"] = str(port)
    elif mode == "socket":
        os.environ["AUTOMCP_SERVER_MODE"] = "socket"
        os.environ["AUTOMCP_SERVER_HOST"] = host
        os.environ["AUTOMCP_SERVER_PORT"] = str(port)
    elif mode == "ws":
        os.environ["AUTOMCP_SERVER_MODE"] = "websocket"
        os.environ["AUTOMCP_SERVER_HOST"] = host
        os.environ["AUTOMCP_SERVER_PORT"] = str(port)
    else:
        print(
            f"Warning: Unknown server mode '{mode}', defaulting to stdio",
            file=sys.stderr,
        )
        os.environ["AUTOMCP_SERVER_MODE"] = "stdio"


async def run_server(
    config_path: Path,
    group_name: Optional[str] = None,
    timeout: float = 30.0,
    mode: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    debug: bool = False,
) -> None:
    """
    Run the AutoMCP server with the specified configuration.

    Args:
        config_path: Path to the configuration file
        group_name: Optional specific group to run from a service config
        timeout: Operation timeout in seconds
        mode: Server communication mode (stdio, http, socket, ws)
        host: Host for HTTP, WebSocket, or Socket mode
        port: Port for HTTP, WebSocket, or Socket mode
        debug: Whether to enable debug mode
    """
    # Configure server mode
    configure_server_mode(mode, host, port)

    if not config_path.exists():
        print(f"Error: Configuration file {config_path} not found", file=sys.stderr)
        sys.exit(1)

    # Load the configuration from the file
    try:
        config = load_config(config_path)
        print(f"Loaded configuration from {config_path}", file=sys.stderr)
    except Exception as e:
        print(f"Error: Failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle group selection for service configs
    if isinstance(config, ServiceConfig) and group_name:
        if group_name not in config.groups:
            print(f"Error: Group {group_name} not found in config", file=sys.stderr)
            sys.exit(1)
        group_config = next(
            (gc for path, gc in config.groups.items() if gc.name == group_name), None
        )
        if not group_config:
            print(f"Error: Group config for {group_name} not found", file=sys.stderr)
            sys.exit(1)
        config = group_config
        print(f"Using group config for {group_name}", file=sys.stderr)

    # Create the server with the loaded config
    server_name = config.name if hasattr(config, "name") else "automcp-server"
    server = AutoMCPServer(server_name, config, timeout)

    # Print available tools
    if debug:
        print_available_tools(server)

    server_type = "stdio"
    if "AUTOMCP_SERVER_MODE" in os.environ:
        server_type = os.environ["AUTOMCP_SERVER_MODE"]

    # Start server info
    if server_type == "stdio":
        print(f"Starting {server_name} with stdio protocol...", file=sys.stderr)
    else:
        server_host = os.environ.get("AUTOMCP_SERVER_HOST", "127.0.0.1")
        server_port = os.environ.get("AUTOMCP_SERVER_PORT", "8000")
        print(
            f"Starting {server_name} with {server_type} protocol at {server_host}:{server_port}...",
            file=sys.stderr,
        )

    try:
        # Start the server using configured protocol
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
        await server.stop()
        print("Server stopped", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_args()

    config_path = Path(args.config).resolve()
    group_name = args.group
    timeout = args.timeout
    mode = args.mode
    host = args.host
    port = args.port
    debug = args.debug

    try:
        asyncio.run(
            run_server(
                config_path=config_path,
                group_name=group_name,
                timeout=timeout,
                mode=mode,
                host=host,
                port=port,
                debug=debug,
            )
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)


if __name__ == "__main__":
    main()
