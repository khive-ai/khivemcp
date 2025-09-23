"""khivemcp Command Line Interface (Refactored)."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

from khivemcp.groups import load_and_instantiate_groups, resolve_auth_provider
from khivemcp.logging_config import setup_logging
from khivemcp.runner import run_async_server
from khivemcp.server import add_health_routes, create_fastmcp_server
from khivemcp.tool_spec import collect_tools_from_groups
from khivemcp.tools import register_tools
from khivemcp.types import AuthProviderChoice, GroupConfig, ServiceConfig, TransportType
from khivemcp.utils import load_config

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="khivemcp",
    help="khivemcp: Run configuration-driven MCP servers using FastMCP.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


async def run_khivemcp_server(
    config: ServiceConfig | GroupConfig,
    transport: TransportType = "stdio",
    host: str = "localhost",
    port: int = 8000,
    auth_choice: AuthProviderChoice = "auto",
) -> None:
    """Initialize and run the FastMCP server with two-pass initialization.

    Two-pass initialization process:
    1. Collect: Load groups, collect tools, collect auth providers
    2. Create: Create FastMCP server with selected auth provider
    3. Register: Register all collected tools

    Args:
        config: Service or group configuration
        transport: Transport type to use
        host: Host to bind to (for HTTP/SSE transports)
        port: Port to bind to (for HTTP/SSE transports)
        auth_choice: Auth provider selection strategy
    """
    logger.info(f"Starting khivemcp server '{config.name}'")

    # PASS 1: Collect groups, tools, and auth providers
    logger.debug("Phase 1: Loading and collecting resources...")

    # Load and instantiate groups
    instantiated_groups, auth_candidates = load_and_instantiate_groups(config)

    if not instantiated_groups:
        logger.error("No groups were successfully instantiated")
        sys.exit(1)

    # Collect tools from groups
    tool_specs = collect_tools_from_groups(instantiated_groups)

    # Resolve auth provider
    auth_provider = resolve_auth_provider(auth_candidates, auth_choice)

    # PASS 2: Create FastMCP server
    logger.debug("Phase 2: Creating FastMCP server...")
    mcp = create_fastmcp_server(config, auth_provider)

    # PASS 3: Register tools
    logger.debug("Phase 3: Registering tools...")
    tools_registered = register_tools(mcp, tool_specs)

    if tools_registered == 0:
        logger.warning("No tools were registered")

    # Extract group instances for lifecycle management
    group_instances = [instance for instance, _ in instantiated_groups]

    # Add health endpoints for HTTP transport (after groups are available)
    if transport in ["http", "sse"]:
        add_health_routes(mcp, group_instances)

    # Run the server
    logger.info(f"Server ready with {tools_registered} tools on {transport} transport")
    await run_async_server(mcp, group_instances, transport, host, port)


@app.command()
def run(
    config_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the configuration file (YAML/JSON).",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    transport: Annotated[
        str,
        typer.Option(
            "--transport",
            "-t",
            help="Transport: 'stdio' (local), 'http' (production remote), 'sse' (legacy remote)",
        ),
    ] = "stdio",
    host: Annotated[
        str,
        typer.Option(
            "--host",
            "-h",
            help="Host to bind to (for HTTP/SSE). Use 0.0.0.0 for external access.",
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to bind to (for HTTP/SSE)"),
    ] = 8000,
    auth_provider: Annotated[
        str,
        typer.Option(
            "--auth-provider",
            "-a",
            help="Auth provider selection: 'auto' (first found), 'none' (disabled)",
        ),
    ] = "auto",
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            "-l",
            help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = "INFO",
    log_config: Annotated[
        Path | None,
        typer.Option(
            "--log-config", help="External logging configuration file (YAML/JSON)"
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output except errors"),
    ] = False,
) -> None:
    """Load configuration and run the khivemcp server using FastMCP.

    Examples:
        # Run locally with stdio (default)
        khivemcp run config.yaml

        # Run as remote server with HTTP transport (recommended)
        khivemcp run config.yaml --transport http --port 8080

        # Run with SSE transport (legacy)
        khivemcp run config.yaml --transport sse --port 8080

        # Run with debug logging
        khivemcp run config.yaml --log-level DEBUG

        # Run with external logging config
        khivemcp run config.yaml --log-config logging.yaml
    """
    # Set up logging first
    setup_logging(log_level, quiet, log_config)

    # Validate transport
    valid_transports = ["stdio", "http", "sse"]
    if transport not in valid_transports:
        logger.error(
            f"Invalid transport '{transport}'. Must be one of: {', '.join(valid_transports)}"
        )
        raise typer.Exit(code=1)

    # Validate auth provider
    valid_auth_choices = ["auto", "none"]
    if auth_provider not in valid_auth_choices:
        logger.error(
            f"Invalid auth provider '{auth_provider}'. Must be one of: {', '.join(valid_auth_choices)}"
        )
        raise typer.Exit(code=1)

    # Log transport recommendation
    if transport == "sse":
        logger.warning(
            "SSE transport is legacy. Consider using 'http' transport for production."
        )

    # Load configuration
    try:
        config = load_config(config_file)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise typer.Exit(code=1)

    # Run the async server
    try:
        asyncio.run(run_khivemcp_server(config, transport, host, port, auth_provider))
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server execution failed: {type(e).__name__}: {e}")
        raise typer.Exit(code=1)


def main():
    """CLI entry point function."""
    app()


if __name__ == "__main__":
    main()
