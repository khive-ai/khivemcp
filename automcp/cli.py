"""AutoMCP CLI tools with enhanced options."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from .server import AutoMCPServer
from .types import GroupConfig, ServiceConfig
from .utils import load_config

app = typer.Typer(
    name="automcp",
    help="AutoMCP server deployment tools (enhanced)",
    add_completion=False,
    no_args_is_help=True,
)


def setup_logging(verbose: bool, mode: str) -> None:
    """
    Configure logging based on verbosity and server mode.

    Args:
        verbose (bool): Whether to enable verbose (DEBUG) logging or not.
        mode (str): The server mode, either "normal" or "stdio".
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    # If stdio mode, log to stderr so we don't interfere with protocol
    if mode == "stdio":
        logging.basicConfig(
            level=log_level,
            stream=sys.stderr,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


async def run_mcp_server(server: AutoMCPServer, mode: str) -> None:
    """
    Run the given AutoMCP server, handling keyboard interrupts and errors.

    Args:
        server (AutoMCPServer): The configured server instance.
        mode (str): The server mode ("normal" or "stdio").
    """
    try:
        # If we care about environment variable fallback for the server code:
        os.environ["AUTOMCP_SERVER_MODE"] = mode

        async with server:
            await server.start()
    except KeyboardInterrupt:
        logging.info("Server interrupted by user.")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        raise typer.Exit(code=1)


@app.callback()
def callback():
    """
    AutoMCP server deployment tools with enhanced options.
    """
    pass


@app.command()
def run(
    config_path: Annotated[
        Optional[Path],
        typer.Argument(
            help="Path to config file (YAML/JSON). If omitted, uses AUTOMCP_CONFIG_PATH environment variable.",
            exists=False,  # We'll check existence later
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="Specific group to run from service config"),
    ] = None,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", help="Operation timeout in seconds")
    ] = 30.0,
    mode: Annotated[
        str | None,
        typer.Option("--mode", "-m", help="Server mode: 'normal' or 'stdio'"),
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose (DEBUG) logging")
    ] = False,
) -> None:
    """
    Run the AutoMCP server with enhanced options:

    - Optional --mode (normal or stdio) fallback to $AUTOMCP_SERVER_MODE or 'normal'
    - Optional --verbose for debug logs
    - Load config from CLI arg, environment var
    - Optionally run a specific group from a service config
    - Timeout for operations
    """

    # 2.1 Determine the Server Mode
    env_mode = os.getenv("AUTOMCP_SERVER_MODE", "normal")
    server_mode = mode if mode else env_mode
    if server_mode not in ["normal", "stdio"]:
        logging.warning(f"Unknown server mode '{server_mode}'. Using 'normal'.")
        server_mode = "normal"

    # 2.2 Setup Logging
    setup_logging(verbose, server_mode)

    # 2.3 Determine Config Path
    final_config_path = None
    if config_path:
        final_config_path = config_path.resolve()
    else:
        env_config_path = os.getenv("AUTOMCP_CONFIG_PATH")
        if env_config_path:
            final_config_path = Path(env_config_path).resolve()

    # 2.4 Check if config was found or not
    if not final_config_path:
        typer.echo(
            "No config file specified via CLI or environment (AUTOMCP_CONFIG_PATH). Exiting."
        )
        raise typer.Exit(code=1)

    if not final_config_path.exists():
        typer.echo(f"Config file not found: {final_config_path}")
        raise typer.Exit(code=1)

    logging.info(f"Using config file: {final_config_path}")

    # 2.5 Load Configuration
    try:
        cfg = load_config(final_config_path)
        logging.info(f"Loaded configuration: {cfg.name}")
    except Exception as e:
        typer.echo(f"Failed to load config: {e}")
        raise typer.Exit(code=1)

    # 2.6 Handle ServiceConfig group selection if requested
    if isinstance(cfg, ServiceConfig) and group:
        if group not in cfg.groups:
            typer.echo(f"Group '{group}' not found in service config.")
            raise typer.Exit(code=1)
        cfg = cfg.groups[group]
        logging.debug(f"Selected sub-group: {cfg.name}")

    # 2.7 Create & Run the Server
    try:
        server = AutoMCPServer(name=cfg.name, config=cfg, timeout=timeout)

        # Special handling for DataProcessorGroup
        if cfg.name == "data-processor":
            try:
                # Dynamically import to avoid hard dependency
                from verification.groups.data_processor_group import DataProcessorGroup

                # Create and register the DataProcessorGroup instance
                data_processor_group = DataProcessorGroup()
                data_processor_group.config = cfg
                server.groups["data-processor"] = data_processor_group

                # Print available operations
                if server_mode == "stdio":
                    print(f"Available DataProcessorGroup operations:", file=sys.stderr)
                    for op_name in data_processor_group.registry.keys():
                        print(f"  - data-processor.{op_name}", file=sys.stderr)
                else:
                    logging.info("Available DataProcessorGroup operations:")
                    for op_name in data_processor_group.registry.keys():
                        logging.info(f"  - data-processor.{op_name}")
            except ImportError as e:
                logging.warning(f"Could not import DataProcessorGroup: {e}")
                logging.warning("Continuing with standard configuration-based setup.")

        if server_mode == "normal":
            typer.echo(
                f"Starting server '{cfg.name}' in normal mode (timeout={timeout}s)..."
            )
        else:
            typer.echo(
                f"Starting server '{cfg.name}' in stdio mode (timeout={timeout}s)..."
            )

        # Launch the server
        asyncio.run(run_mcp_server(server, server_mode))

    except Exception as e:
        typer.echo(f"Error while running server: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
