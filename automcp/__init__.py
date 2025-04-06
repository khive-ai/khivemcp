# automcp/__init__.py
"""AutoMCP: Configuration-driven MCP server framework using FastMCP."""

# Expose key components for users importing the library
from .decorators import operation
from .types import GroupConfig, ServiceConfig

__version__ = "0.1.0"

__all__ = [
    "operation",
    "ServiceConfig",
    "GroupConfig",
]
