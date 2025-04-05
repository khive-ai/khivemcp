"""
AutoMCP: A framework for building MCP-compatible service groups.

This package provides tools and utilities for creating, configuring, and running
MCP (Machine Conversation Protocol) servers with structured service groups and operations.
It simplifies the process of exposing Python functions as MCP tools with input validation,
timeout handling, and standardized error reporting.

Key components:
- ServiceGroup: Base class for creating groups of related operations
- operation: Decorator for marking methods as callable operations with schema validation
- AutoMCPServer: MCP server implementation that hosts service groups
- run_server: Main entry point for running an AutoMCP server from a configuration file
- Configuration models: GroupConfig and ServiceConfig for structured configuration
- Exception hierarchy: Structured exceptions for error handling

For more information, see the documentation and examples.
"""

from .config import load_config
from .exceptions import (
    AutoMCPError,
    ConfigError,
    ConfigFormatError,
    ConfigNotFoundError,
    OperationError,
    OperationTimeoutError,
    ServerError,
)
from .group import ServiceGroup
from .operation import operation
from .runner import run_server
from .server import AutoMCPServer
from .types import GroupConfig, ServiceConfig
from .version import __version__

__all__ = [
    # Main functionality
    "load_config",
    "ServiceGroup",
    "operation",
    "run_server",
    "AutoMCPServer",
    # Configuration models
    "GroupConfig",
    "ServiceConfig",
    # Exception classes
    "AutoMCPError",
    "ConfigError",
    "ConfigFormatError",
    "ConfigNotFoundError",
    "OperationError",
    "OperationTimeoutError",
    "ServerError",
    # Version information
    "__version__",
]
