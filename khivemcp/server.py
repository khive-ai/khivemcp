"""FastMCP server initialization and management."""

import asyncio
import logging

from fastmcp import FastMCP
from fastmcp.server.auth import AuthProvider
from starlette.responses import JSONResponse, PlainTextResponse

from .types import GroupConfig, ServiceConfig, ServiceGroup

logger = logging.getLogger(__name__)


def create_fastmcp_server(
    config: ServiceConfig | GroupConfig,
    auth_provider: AuthProvider | None = None,
) -> FastMCP:
    """Create and configure a FastMCP server instance.

    Args:
        config: Service or group configuration
        auth_provider: Optional authentication provider

    Returns:
        Configured FastMCP server instance
    """
    server_name = config.name
    server_description = getattr(config, "description", None)

    logger.info(
        f"Creating FastMCP server '{server_name}' (Auth: {'Yes' if auth_provider else 'No'})"
    )

    # Create FastMCP server - try instructions parameter
    try:
        mcp = FastMCP(
            name=server_name, instructions=server_description or "", auth=auth_provider
        )
    except TypeError:
        # Fallback to basic constructor
        logger.debug("FastMCP doesn't accept instructions parameter, using name only")
        mcp = FastMCP(name=server_name, auth=auth_provider)

    return mcp


def add_health_routes(mcp: FastMCP, group_instances: list[ServiceGroup] = None) -> None:
    """Add health check endpoints to the FastMCP server.

    Args:
        mcp: FastMCP server instance
        group_instances: List of service group instances for readiness checks
    """
    logger.debug("Adding health check routes")

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_):
        """Basic liveness check (no dependencies)."""
        return PlainTextResponse("OK")

    @mcp.custom_route("/ready", methods=["GET"])
    async def readiness_check(_):
        """Aggregate readiness check across all service groups."""
        if not group_instances:
            return PlainTextResponse("READY")

        # Gather readiness status from all groups
        results = await asyncio.gather(
            *(group.readiness() for group in group_instances), return_exceptions=True
        )

        # Process results and determine overall status
        readiness_data = []
        overall_ready = True

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Group readiness check failed
                group_name = group_instances[i].__class__.__name__
                readiness_data.append(
                    {"name": group_name, "status": "down", "error": str(result)}
                )
                overall_ready = False
            else:
                # Successful readiness check
                readiness_data.append(result.model_dump())
                if result.status != "ready":
                    overall_ready = False

        # Return 503 if any group is not ready, 200 otherwise
        status_code = 200 if overall_ready else 503
        return JSONResponse(readiness_data, status_code=status_code)

    logger.debug("Health check routes added")
