"""AutoMCP - Model Context Protocol server implementation."""

import argparse
import asyncio
import json
from pathlib import Path

import yaml

from automcp.core.errors import ConfigurationError, OperationError
from automcp.core.server import AutoMCPServer, serve
from automcp.core.service import ServiceGroup, operation
from automcp.schemas.base import (
    ExecutionResponse,
    GroupConfig,
    ServiceConfig,
    ServiceRequest,
    ServiceResponse,
)

__all__ = [
    "ServiceGroup",
    "operation",
    "AutoMCPServer",
    "ServiceConfig",
    "GroupConfig",
    "ExecutionResponse",
    "ServiceRequest",
    "ServiceResponse",
    "ConfigurationError",
    "OperationError",
    "serve",
]

__all__ = [
    "ServiceGroup",
    "operation",
    "AutoMCPServer",
    "ServiceConfig",
    "GroupConfig",
    "ExecutionResponse",
    "ServiceRequest",
    "ServiceResponse",
    "ConfigurationError",
    "OperationError",
    "serve",
]


def load_config(path: Path) -> ServiceConfig | GroupConfig:
    """Load configuration from file."""
    try:
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                data = yaml.safe_load(f)
            return ServiceConfig(**data)
        else:
            with open(path) as f:
                data = json.load(f)
            return GroupConfig(**data)
    except Exception as e:
        raise ConfigurationError(f"Failed to load config: {str(e)}")


def main():
    """AutoMCP server - MCP server implementation with group support."""
    parser = argparse.ArgumentParser(
        description="Run an MCP server with support for service groups"
    )
    parser.add_argument("config", type=Path, help="Path to configuration file")
    parser.add_argument("--group", type=str, help="Specific group to run")
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Operation timeout in seconds"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    try:
        # Load configuration
        config_path = args.config.resolve()
        if not config_path.exists():
            print(f"Config file not found: {config_path}")
            exit(1)

        cfg = load_config(config_path)

        # Handle group selection
        if isinstance(cfg, ServiceConfig) and args.group:
            if args.group not in cfg.groups:
                print(f"Group {args.group} not found in config")
                exit(1)
            cfg = cfg.groups[args.group]

        # Run server
        asyncio.run(serve(cfg, args.timeout))

    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        if args.debug:
            import traceback

            print(f"\nFull traceback:\n{traceback.format_exc()}")
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
