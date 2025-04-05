#!/usr/bin/env python3
"""
Run a ServiceGroup server for testing with MCP clients.

This script uses the new automcp.run_server function to start a server
from a configuration file.

Usage:
  python -m verification.run_group_server <config_file> [timeout]
"""

import sys
from pathlib import Path

from automcp import run_server
from automcp.exceptions import AutoMCPError


def main():
    """Run the server with the specified configuration."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m verification.run_group_server <config_file> [timeout]"
        )
        print("\nAvailable configs:")
        config_dir = Path(__file__).parent / "config"
        for config in config_dir.glob("*.{json,yaml,yml}"):
            print(f"  - {config.name}")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / "config" / config_path

    timeout = 30.0
    if len(sys.argv) > 2:
        try:
            timeout = float(sys.argv[2])
        except ValueError:
            print(
                f"Invalid timeout value: {sys.argv[2]}. Using default: {timeout}"
            )

    try:
        run_server(config_path=config_path, timeout=timeout)
    except AutoMCPError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
