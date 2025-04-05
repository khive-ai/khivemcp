#!/usr/bin/env python3
"""
Run a DataProcessorGroup server for testing with MCP clients.

This script loads the data_processor_group.json config, creates an AutoMCPServer instance,
and starts the server for MCP client connections.
"""

import asyncio
import sys
from pathlib import Path

from automcp.server import AutoMCPServer
from automcp.utils import load_config
from verification.groups.data_processor_group import DataProcessorGroup


async def main():
    """Run the DataProcessorGroup server."""
    # Get the path to the data_processor_group.json config
    config_path = Path(__file__).parent / "config" / "data_processor_group.json"

    if not config_path.exists():
        print(f"Error: Configuration file {config_path} not found")
        sys.exit(1)

    # Load the configuration from the file
    try:
        config = load_config(config_path)
        print(f"Loaded configuration from {config_path}")
    except Exception as e:
        print(f"Error: Failed to load configuration: {e}")
        sys.exit(1)

    # Create the server with the loaded config
    server = AutoMCPServer("data-processor-server", config)

    # Ensure the DataProcessorGroup is registered
    data_processor_group = DataProcessorGroup()
    data_processor_group.config = config
    server.groups["data-processor"] = data_processor_group

    print(f"Starting DataProcessorGroup server...")
    print(f"Available operations:")
    for op_name in data_processor_group.registry.keys():
        print(f"  - data-processor.{op_name}")

    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.stop()
        print("Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
