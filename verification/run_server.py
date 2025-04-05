#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

from automcp.server import AutoMCPServer


async def main():
    """Run the AutoMCP server with the specified configuration."""
    if len(sys.argv) < 2:
        print("Usage: python run_server.py <config_file>")
        print("\nAvailable configs:")
        config_dir = Path(__file__).parent / "config"
        for config in config_dir.glob("*.{json,yaml,yml}"):
            print(f"  - {config.name}")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.is_absolute():
        # Fix the path issue - remove duplicate "config" directory
        config_path = Path(__file__).parent / "config" / config_path

    if not config_path.exists():
        print(f"Error: Configuration file {config_path} not found")
        sys.exit(1)

    # Load the configuration from the file
    import json

    import yaml

    if config_path.suffix in [".yaml", ".yml"]:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    else:
        with open(config_path, "r") as f:
            config_data = json.load(f)

    # Create a GroupConfig from the loaded data
    from automcp.types import GroupConfig

    config = GroupConfig(**config_data)

    server = AutoMCPServer("verification-server", config)
    try:
        await server.start()
        print(f"Server running with configuration: {config_path}")
        print("Press Ctrl+C to stop")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.stop()
        print("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
