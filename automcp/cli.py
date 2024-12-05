"""AutoMCP CLI tools."""

import asyncio
import json
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml

from .server import AutoMCPServer
from .types import GroupConfig, ServiceConfig

app = typer.Typer(
    name="automcp",
    help="AutoMCP server deployment tools",
    add_completion=False,
    no_args_is_help=True,
)


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
        typer.echo(f"Failed to load config: {e}")
        raise typer.Exit(1)


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
        if not config_path.exists():
            typer.echo(f"Config file not found: {config_path}")
            raise typer.Exit(1)

        # Load configuration
        cfg = load_config(config_path)

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
