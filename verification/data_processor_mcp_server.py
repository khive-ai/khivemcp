#!/usr/bin/env python3
"""
Standalone DataProcessorGroup server script for Roo's MCP client.

This script:
1. Loads the DataProcessorGroup configuration
2. Creates an AutoMCPServer instance with the DataProcessorGroup
3. Makes it accessible via MCP stdio protocol
4. Prints available tools on startup

Usage:
    python verification/data_processor_mcp_server.py
"""

import asyncio
import os
import sys
from pathlib import Path

from automcp.server import AutoMCPServer
from automcp.utils import load_config
from verification.groups.data_processor_group import DataProcessorGroup

# Configure server to use stdio for MCP communication
os.environ["AUTOMCP_SERVER_MODE"] = "stdio"


async def main():
    """Run the DataProcessorGroup server with stdio MCP protocol."""
    # Get the path to the data_processor_group.json config
    config_path = Path(__file__).parent / "config" / "data_processor_group.json"

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

    # Create the server with the loaded config
    server = AutoMCPServer("data-processor-mcp-server", config)

    # Ensure the DataProcessorGroup is registered
    data_processor_group = DataProcessorGroup()
    data_processor_group.config = config
    server.groups["data-processor"] = data_processor_group

    # Print available tools to stderr (not to interfere with stdio protocol)
    print(f"Starting DataProcessorGroup MCP server...", file=sys.stderr)
    print(f"Available tools:", file=sys.stderr)
    for op_name in data_processor_group.registry.keys():
        print(f"  - data-processor.{op_name}", file=sys.stderr)

    try:
        # Start the server using stdio protocol
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
        await server.stop()
        print("Server stopped", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
