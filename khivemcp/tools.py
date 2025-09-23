"""Tool wrapper creation and registration for FastMCP."""

import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_access_token
from pydantic import TypeAdapter

from .tool_spec import ToolSpec

logger = logging.getLogger(__name__)


def create_tool_wrapper(spec: ToolSpec):
    """Create a wrapper function compatible with FastMCP tool registration.

    Handles Pydantic conversion, RBAC enforcement, and FastMCP Context injection
    based on the tool specification.

    Args:
        spec: ToolSpec containing method and metadata

    Returns:
        Wrapped function ready for FastMCP registration
    """
    bound_method = spec.bound_method
    schema_cls = spec.schema_cls
    accepts_ctx = spec.accepts_ctx

    # Cache TypeAdapter for better performance
    adapter = TypeAdapter(schema_cls) if schema_cls else None

    async def _coerce_request(payload):
        """Convert various request formats to the expected schema."""
        if adapter is None:
            return payload

        try:
            if isinstance(payload, str):
                return adapter.validate_json(payload)
            else:
                return adapter.validate_python(payload)
        except Exception as e:
            logger.error(f"Request validation failed for {spec.full_tool_name}: {e}")
            raise ValueError(f"Invalid request format: {e}")

    async def _check_authz(ctx: Context | None):
        """Check authorization if required for this tool."""
        if not spec.auth_required:
            return  # No auth required

        if ctx is None:
            raise PermissionError(
                f"Authentication required for tool '{spec.full_tool_name}'"
            )

        # Try common Context shapes without hard-coding FastMCP internals
        token = getattr(ctx, "access_token", None) or getattr(ctx, "token", None)
        if token is None:
            raise PermissionError(
                f"Authentication required for tool '{spec.full_tool_name}'"
            )

        # Check if token has required scopes
        token_scopes = set(getattr(token, "scopes", []) or [])
        required_scopes = set(spec.auth_required)

        if not required_scopes.issubset(token_scopes):
            missing = sorted(required_scopes - token_scopes)
            raise PermissionError(
                f"Missing required scopes for tool '{spec.full_tool_name}': {missing}"
            )

    # Strategy: If auth is required, always request Context so we can authorize,
    # even if the underlying method doesn't accept ctx.
    # Otherwise mirror the method's declared context usage.
    if spec.auth_required or accepts_ctx:

        async def tool_with_context(ctx: Context, request: dict | str | Any):
            await _check_authz(ctx)
            coerced_request = await _coerce_request(request)
            if accepts_ctx:
                return await bound_method(ctx=ctx, request=coerced_request)
            else:
                # Underlying method does not accept ctx
                return await bound_method(request=coerced_request)

        tool_with_context.__annotations__ = {
            "ctx": Context,
            "request": dict,
            "return": Any,
        }
        wrapper = tool_with_context
    else:
        # Standard method without context
        async def tool_without_context(request: dict | str | Any):
            # No auth required here; if required, we used tool_with_context above
            coerced_request = await _coerce_request(request)
            return await bound_method(request=coerced_request)

        tool_without_context.__annotations__ = {"request": dict, "return": Any}
        wrapper = tool_without_context

    # Set metadata for FastMCP
    wrapper.__name__ = spec.full_tool_name.replace("-", "_")
    wrapper.__qualname__ = spec.full_tool_name.replace("-", "_")
    wrapper.__doc__ = spec.description

    logger.debug(
        f"Created wrapper for tool '{spec.full_tool_name}' "
        f"(context: {accepts_ctx}, schema: {schema_cls is not None}, "
        f"auth: {spec.auth_required is not None})"
    )

    return wrapper


def register_tools(mcp: FastMCP, tool_specs: list[ToolSpec]) -> int:
    """Register all tool specifications with the FastMCP server.

    Args:
        mcp: FastMCP server instance
        tool_specs: List of tool specifications to register

    Returns:
        Number of tools successfully registered
    """
    logger.info(f"Registering {len(tool_specs)} tools...")
    registered_count = 0

    for spec in tool_specs:
        try:
            wrapper = create_tool_wrapper(spec)
            mcp.tool(wrapper)
            registered_count += 1
            logger.debug(f"Registered tool '{spec.full_tool_name}'")

        except Exception as e:
            logger.error(f"Failed to register tool '{spec.full_tool_name}': {e}")

    logger.info(f"Successfully registered {registered_count}/{len(tool_specs)} tools")
    return registered_count
