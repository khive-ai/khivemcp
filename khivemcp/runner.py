"""Async server runner using FastMCP's run_async() method."""

import asyncio
import logging

from fastmcp import FastMCP

from .types import ServiceGroup, TransportType

logger = logging.getLogger(__name__)


async def startup_groups(group_instances: list[ServiceGroup]) -> None:
    """Run startup hooks for all groups concurrently.

    Args:
        group_instances: List of instantiated service groups
    """
    if not group_instances:
        return

    logger.info(f"Starting up {len(group_instances)} group(s)...")

    # Use TaskGroup for concurrent startup (Python 3.11+)
    # Fallback to gather() for Python 3.10
    try:
        if hasattr(asyncio, "TaskGroup"):
            async with asyncio.TaskGroup() as tg:
                for group in group_instances:
                    if hasattr(group, "startup"):
                        tg.create_task(group.startup())
                        logger.debug(
                            f"Scheduled startup for {group.__class__.__name__}"
                        )
        else:
            # Fallback for Python 3.10
            tasks = []
            for group in group_instances:
                if hasattr(group, "startup"):
                    tasks.append(group.startup())
                    logger.debug(f"Scheduled startup for {group.__class__.__name__}")
            await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Critical failure during group startup: {e}")
        raise RuntimeError("Application startup failed") from e

    logger.info("All groups started successfully")


async def shutdown_groups(group_instances: list[ServiceGroup]) -> None:
    """Run shutdown hooks for all groups concurrently.

    Args:
        group_instances: List of instantiated service groups
    """
    if not group_instances:
        return

    logger.info(f"Shutting down {len(group_instances)} group(s)...")

    # Shutdown in reverse order
    try:
        if hasattr(asyncio, "TaskGroup"):
            async with asyncio.TaskGroup() as tg:
                for group in reversed(group_instances):
                    if hasattr(group, "shutdown"):
                        tg.create_task(group.shutdown())
                        logger.debug(
                            f"Scheduled shutdown for {group.__class__.__name__}"
                        )
        else:
            # Fallback for Python 3.10
            tasks = []
            for group in reversed(group_instances):
                if hasattr(group, "shutdown"):
                    tasks.append(group.shutdown())
                    logger.debug(f"Scheduled shutdown for {group.__class__.__name__}")
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        # Log errors but don't re-raise during shutdown
        logger.error(f"Error during group shutdown: {e}")

    logger.info("All groups shut down")


async def run_async_server(
    mcp: FastMCP,
    group_instances: list[ServiceGroup],
    transport: TransportType,
    host: str = "localhost",
    port: int = 8000,
) -> None:
    """Run the FastMCP server asynchronously with proper lifecycle management.

    Args:
        mcp: Configured FastMCP server
        group_instances: List of service group instances
        transport: Transport type to use
        host: Host to bind to (for HTTP/SSE transports)
        port: Port to bind to (for HTTP/SSE transports)
    """
    logger.info(f"Starting server with {transport} transport...")

    try:
        # Startup groups first
        await startup_groups(group_instances)

        # Run the server with the specified transport
        if transport == "stdio":
            await mcp.run_async()
        elif transport == "http":
            await mcp.run_async(transport="http", host=host, port=port)
        elif transport == "sse":
            logger.warning(
                "SSE transport is legacy - consider upgrading to HTTP transport"
            )
            await mcp.run_async(transport="sse", host=host, port=port)
        else:
            raise ValueError(f"Unknown transport: {transport}")

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Server execution failed: {type(e).__name__}: {e}")
        raise
    finally:
        # Always shutdown groups
        await shutdown_groups(group_instances)
