#!/usr/bin/env python3
"""
Script to test AutoMCP timeout functionality.

This script starts an AutoMCP server with a specified timeout value.
"""

import sys
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from automcp import run_server
from automcp.exceptions import AutoMCPError


def main():
    """Run the AutoMCP server with a specific timeout."""
    if len(sys.argv) < 3:
        print("Usage: python timeout_test.py <config_file> <timeout>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    timeout = float(sys.argv[2])

    try:
        print(f"Starting server with timeout: {timeout} seconds")
        run_server(config_path=config_path, timeout=timeout)
    except AutoMCPError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
