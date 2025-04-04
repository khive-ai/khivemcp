#!/usr/bin/env python3
"""
Script to test AutoMCP timeout functionality.
"""

import asyncio
import importlib
import json
import sys
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig
from verification.groups.timeout_group import TimeoutGroup


async def main():
    """Run the AutoMCP server with a specific timeout."""
    if len(sys.argv) < 3:
        print("Usage: python timeout_test.py <config_file> <timeout>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    timeout = float(sys.argv[2])

    # Load the configuration from the file
    with open(config_path, "r") as f:
        config_data = json.load(f)

    # Create a GroupConfig from the loaded data
    config = GroupConfig(**config_data)

    # Create the server with the specified timeout
    server = AutoMCPServer("timeout-test", config, timeout=timeout)

    # Register the timeout group
    timeout_group = TimeoutGroup()
    server.groups["timeout"] = timeout_group

    # Start the server
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
