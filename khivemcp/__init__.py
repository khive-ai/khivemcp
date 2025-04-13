# khivemcp/__init__.py
"""khivemcp: Configuration-driven MCP server framework using FastMCP."""

# Expose key components for users importing the library
from .decorators import operation
from .types import GroupConfig, ServiceConfig, ServiceGroup

__version__ = "0.1.3"

__all__ = [
    "operation",
    "ServiceConfig",
    "GroupConfig",
    "ServiceGroup",
]
