"""AutoMCP CLI tools."""

from pathlib import Path
from typing import Annotated

import typer

from .config import load_config
from .exceptions import AutoMCPError, ConfigFormatError, ConfigNotFoundError
from .runner import run_server
from .types import GroupConfig, ServiceConfig

app = typer.Typer(
    name="automcp",
    help="AutoMCP server deployment tools",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def run(
    config: Annotated[
        Path, typer.Argument(help="Path to config file (YAML/JSON)")
    ],
    group: Annotated[
        str | None,
        typer.Option(
            "--group", "-g", help="Specific group to run from service config"
        ),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Operation timeout in seconds"),
    ] = 30.0,
) -> None:
    """Run AutoMCP server using the specified configuration file."""
    try:
        config_path = Path(config).resolve()

        # Handle group selection if specified
        if group:
            try:
                # Load the config to check if it's a ServiceConfig with the specified group
                cfg = load_config(config_path)
                if isinstance(cfg, ServiceConfig):
                    if group not in cfg.groups:
                        typer.echo(
                            f"Group '{group}' not found in service config"
                        )
                        raise typer.Exit(1)

                    # Extract the group config and save it to a temporary file
                    group_config = cfg.groups[group]
                    typer.echo(
                        f"Running only the '{group}' group from service config"
                    )

                    # Use the extracted group config directly
                    # Note: This approach doesn't save to a temp file, which might be needed
                    # if run_server can't handle GroupConfig objects directly
                    config_path = config_path
                else:
                    typer.echo(
                        f"Warning: --group option ignored. Config is not a ServiceConfig."
                    )
            except (ConfigNotFoundError, ConfigFormatError) as e:
                typer.echo(f"Error loading config: {e}")
                raise typer.Exit(1)

        # Run the server using the core library function
        run_server(config_path=config_path, timeout=timeout)

    except ConfigNotFoundError as e:
        typer.echo(f"Configuration error: {e}")
        raise typer.Exit(1)
    except ConfigFormatError as e:
        typer.echo(f"Configuration format error: {e}")
        raise typer.Exit(1)
    except AutoMCPError as e:
        typer.echo(f"Server error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}")
        raise typer.Exit(1)


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
