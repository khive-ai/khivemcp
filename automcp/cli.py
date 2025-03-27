"""AutoMCP CLI interface."""

import asyncio
import json
import traceback
from pathlib import Path
from typing import Optional

import typer
import yaml
from typing_extensions import Annotated

from automcp.core.errors import ConfigurationError
from automcp.core.server import AutoMCPServer
from automcp.schemas.base import GroupConfig, ServiceConfig

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
        raise ConfigurationError(f"Failed to load config: {str(e)}")


@app.command()
def run(
    config: Annotated[Path, typer.Argument(help="Path to configuration file")],
    group: Annotated[Optional[str], typer.Option(help="Specific group to run")] = None,
    timeout: Annotated[float, typer.Option(help="Operation timeout in seconds")] = 30.0,
    debug: Annotated[bool, typer.Option(help="Enable debug mode")] = False,
) -> None:
    """Run AutoMCP server."""
    try:
        # Resolve config path
        config_path = Path(config).resolve()
        if not config_path.exists():
            typer.echo(f"Config file not found: {config_path}")
            raise typer.Exit(1)

        # Load configuration
        cfg = load_config(config_path)

        # Handle group selection
        if isinstance(cfg, ServiceConfig) and group:
            if group not in cfg.groups:
                typer.echo(f"Group {group} not found in config")
                raise typer.Exit(1)
            cfg = cfg.groups[group]

        # Create and run server
        async def run_server():
            server = AutoMCPServer(name=cfg.name, config=cfg, timeout=timeout)
            async with server:
                await server.start()

        # Run event loop
        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            typer.echo("\nServer stopped")
        except Exception as e:
            if debug:
                typer.echo(f"\nFull traceback:\n{traceback.format_exc()}")
            typer.echo(f"Server error: {str(e)}")
            raise typer.Exit(1)

    except Exception as e:
        if debug:
            typer.echo(f"\nFull traceback:\n{traceback.format_exc()}")
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(1)


@app.command()
def validate(
    config: Annotated[Path, typer.Argument(help="Path to configuration file")],
) -> None:
    """Validate configuration file."""
    try:
        config_path = Path(config).resolve()
        if not config_path.exists():
            typer.echo(f"Config file not found: {config_path}")
            raise typer.Exit(1)

        cfg = load_config(config_path)
        typer.echo(f"Configuration valid: {config_path}")
        typer.echo(f"Type: {'Service' if isinstance(cfg, ServiceConfig) else 'Group'}")
        typer.echo(f"Name: {cfg.name}")

        if isinstance(cfg, ServiceConfig):
            typer.echo(f"Groups: {', '.join(cfg.groups.keys())}")

    except Exception as e:
        typer.echo(f"Configuration invalid: {str(e)}")
        raise typer.Exit(1)


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
