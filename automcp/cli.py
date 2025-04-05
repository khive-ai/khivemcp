"""AutoMCP CLI tools."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from .server import AutoMCPServer
from .types import GroupConfig, ServiceConfig
from .utils import load_config

app = typer.Typer(
    name="automcp",
    help="AutoMCP server deployment tools",
    add_completion=False,
    no_args_is_help=True,
)


async def run_server(server: AutoMCPServer) -> None:
    """Run MCP server."""
    try:
        async with server:
            await server.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        typer.echo(f"Server error: {e}")
        raise typer.Exit(1)


@app.command()
def run(
    config: Annotated[Path, typer.Argument(help="Path to config file (YAML/JSON)")],
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="Specific group to run from service config"),
    ] = None,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", help="Operation timeout in seconds")
    ] = 30.0,
) -> None:
    """Run AutoMCP server."""
    try:
        config_path = Path(config).resolve()

        # Load configuration
        try:
            cfg = load_config(config_path)
        except FileNotFoundError:
            typer.echo(f"Config file not found: {config_path}")
            raise typer.Exit(1)
        except ValueError as e:
            typer.echo(f"Failed to load config: {e}")
            raise typer.Exit(1)

        # Handle service config with group selection
        if isinstance(cfg, ServiceConfig) and group:
            if group not in cfg.groups:
                typer.echo(f"Group {group} not found in config")
                raise typer.Exit(1)
            cfg = cfg.groups[group]

        # Create and run server
        server = AutoMCPServer(name=cfg.name, config=cfg, timeout=timeout)

        asyncio.run(run_server(server))

    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
