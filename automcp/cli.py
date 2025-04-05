"""AutoMCP CLI tools."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ._cli.server_template import configure_server_mode
from .server import AutoMCPServer
from .types import GroupConfig, ServiceConfig
from .utils import load_config
from .version import __version__

# Create console for rich output
console = Console()

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
    mode: Annotated[
        str,
        typer.Option(
            "--mode", "-m", help="Server communication mode (stdio, http, socket, ws)"
        ),
    ] = "stdio",
    host: Annotated[
        str,
        typer.Option(
            "--host", help="Host for HTTP/WebSocket/Socket server (default: 127.0.0.1)"
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port", "-p", help="Port for HTTP/WebSocket/Socket server (default: 8000)"
        ),
    ] = 8000,
    debug: Annotated[
        bool, typer.Option("--debug", "-d", help="Enable debug output")
    ] = False,
) -> None:
    """Run AutoMCP server with various communication protocols."""
    try:
        # Configure the server mode
        configure_server_mode(mode, host, port)

        config_path = Path(config).resolve()

        # Load configuration
        try:
            cfg = load_config(config_path)
            if debug:
                console.print(f"Loaded configuration from {config_path}")
        except FileNotFoundError:
            console.print(f"[bold red]Config file not found:[/bold red] {config_path}")
            raise typer.Exit(1)
        except ValueError as e:
            console.print(f"[bold red]Failed to load config:[/bold red] {e}")
            raise typer.Exit(1)

        # Handle service config with group selection
        if isinstance(cfg, ServiceConfig) and group:
            # First check if the group name exists in the config
            if group not in [g_cfg.name for g_cfg in cfg.groups.values()]:
                console.print(f"[bold red]Group {group} not found in config[/bold red]")
                raise typer.Exit(1)

            # Get the group config by name
            group_config = next(
                g_cfg for g_cfg in cfg.groups.values() if g_cfg.name == group
            )
            cfg = group_config
            if debug:
                console.print(f"Using group config for {group}")

        # Create and run server
        server = AutoMCPServer(name=cfg.name, config=cfg, timeout=timeout)

        # Print available tools if debug is enabled
        if debug:
            console.print("[bold]Available tools:[/bold]")
            for group_name, group in server.groups.items():
                for op_name in group.registry.keys():
                    console.print(f"  - {group_name}.{op_name}")

        # Show server information
        server_type = os.environ.get("AUTOMCP_SERVER_MODE", "stdio")
        if server_type == "stdio":
            console.print(
                Panel.fit(
                    f"[bold]Starting {cfg.name} with stdio protocol[/bold]",
                    title="AutoMCP Server",
                    subtitle=f"v{__version__}",
                )
            )
        else:
            server_host = os.environ.get("AUTOMCP_SERVER_HOST", "127.0.0.1")
            server_port = os.environ.get("AUTOMCP_SERVER_PORT", "8000")
            console.print(
                Panel.fit(
                    f"[bold]Starting {cfg.name} with {server_type} protocol[/bold]\n"
                    f"URL: http://{server_host}:{server_port}",
                    title="AutoMCP Server",
                    subtitle=f"v{__version__}",
                )
            )

        asyncio.run(run_server(server))

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if debug:
            import traceback

            console.print("[bold red]Traceback:[/bold red]")
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def generate_config(
    config: Annotated[
        Path, typer.Argument(help="Path to AutoMCP config file (YAML/JSON)")
    ],
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o", help="Output path for the generated Roo MCP config"
        ),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="Specific group to include in the config"),
    ] = None,
    server_command: Annotated[
        str,
        typer.Option(
            "--command",
            "-c",
            help="Command to run the server (default: python -m automcp.cli run)",
        ),
    ] = None,
    pretty: Annotated[
        bool, typer.Option("--pretty", "-p", help="Generate pretty-printed JSON")
    ] = True,
) -> None:
    """Generate a Roo-compatible MCP configuration from an AutoMCP config."""
    try:
        config_path = Path(config).resolve()

        # Load configuration
        try:
            cfg = load_config(config_path)
        except FileNotFoundError:
            console.print(f"[bold red]Config file not found:[/bold red] {config_path}")
            raise typer.Exit(1)
        except ValueError as e:
            console.print(f"[bold red]Failed to load config:[/bold red] {e}")
            raise typer.Exit(1)

        # Handle service config with group selection
        if isinstance(cfg, ServiceConfig) and group:
            # First check if the group name exists in the config
            if group not in [g_cfg.name for g_cfg in cfg.groups.values()]:
                console.print(f"[bold red]Group {group} not found in config[/bold red]")
                raise typer.Exit(1)

            # Get the group config by name
            group_config = next(
                g_cfg for g_cfg in cfg.groups.values() if g_cfg.name == group
            )

            # For MCP config generation, we'll just focus on this group
            groups_to_include = [group]
        else:
            # If it's a service config with multiple groups, include all of them
            if isinstance(cfg, ServiceConfig):
                groups_to_include = [g_cfg.name for g_cfg in cfg.groups.values()]
            else:
                # It's a single group config
                groups_to_include = [cfg.name]

        # Determine the server command
        if not server_command:
            config_arg = str(config_path)
            if group:
                server_command = (
                    f"python -m automcp.cli run {config_arg} --group {group}"
                )
            else:
                server_command = f"python -m automcp.cli run {config_arg}"

        # Create the MCP configuration
        mcp_config = {
            "name": cfg.name,
            "description": (
                cfg.description
                if hasattr(cfg, "description")
                else f"AutoMCP server for {cfg.name}"
            ),
            "server": {
                "name": f"{cfg.name}-mcp-server",
                "command": server_command,
                "protocol": "stdio",
            },
            "tools": [],
        }

        # Create a temporary server to get tool information
        server = AutoMCPServer(name=cfg.name, config=cfg)

        # Add tool information
        for group_name, group in server.groups.items():
            # Skip groups that weren't included
            if group_name not in groups_to_include:
                continue

            for op_name, operation in group.registry.items():
                # Extract schema if available
                input_schema = {}
                if operation.schema:
                    try:
                        schema_dict = operation.schema.model_json_schema()
                        if isinstance(schema_dict, dict):
                            input_schema = schema_dict
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning:[/yellow] Failed to extract schema for {group_name}.{op_name}: {e}"
                        )

                tool = {
                    "name": f"{group_name}.{op_name}",
                    "description": operation.doc
                    or f"{op_name} operation from {group_name} group",
                    "inputSchema": input_schema,
                }
                mcp_config["tools"].append(tool)

        # Determine the output path
        if not output:
            output_name = f"{cfg.name}_mcp_config.json"
            output = Path(output_name)

        # Write the configuration
        output_path = Path(output).resolve()
        with open(output_path, "w") as f:
            indent = 2 if pretty else None
            json.dump(mcp_config, f, indent=indent)

        console.print(
            f"[bold green]✓[/bold green] Generated Roo MCP configuration at [cyan]{output_path}[/cyan]"
        )

        # Show a summary of the configuration
        console.print("\n[bold]Configuration Summary:[/bold]")
        console.print(f"Server Name: {mcp_config['name']}")
        console.print(f"Server Command: {mcp_config['server']['command']}")
        console.print(f"Number of Tools: {len(mcp_config['tools'])}")

        # Show tool names
        if len(mcp_config["tools"]) > 0:
            console.print("\n[bold]Available Tools:[/bold]")
            for tool in mcp_config["tools"]:
                console.print(f"  - {tool['name']}")

        # Show usage instructions
        console.print("\n[bold]Usage with Roo:[/bold]")
        console.print("1. Add this configuration to your Roo mode settings.")
        console.print("2. Enable the necessary MCP tool in Roo settings.")
        console.print(
            "3. Interact with the tool in Roo using the tool names listed above."
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def create_project(
    name: Annotated[str, typer.Argument(help="Name of the project to create")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory for the project"),
    ] = None,
    group_name: Annotated[
        str, typer.Option("--group", "-g", help="Name of the service group")
    ] = None,
    description: Annotated[
        str, typer.Option("--description", "-d", help="Project description")
    ] = None,
) -> None:
    """Create a new AutoMCP project with basic structure."""
    try:
        # Set default values
        if not group_name:
            group_name = name.lower().replace(" ", "-").replace("_", "-")

        if not description:
            description = f"AutoMCP server for {name}"

        # Determine output directory
        if not output:
            output = Path(name.lower().replace(" ", "_").replace("-", "_"))

        output_dir = Path(output).resolve()

        # Check if directory exists and is not empty
        if output_dir.exists() and any(output_dir.iterdir()):
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Directory {output_dir} already exists and is not empty."
            )
            overwrite = typer.confirm("Continue and possibly overwrite files?")
            if not overwrite:
                console.print("Aborted.")
                return

        # Create directory structure
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create package structure
        group_dir = output_dir / "groups"
        config_dir = output_dir / "config"
        tests_dir = output_dir / "tests"

        group_dir.mkdir(exist_ok=True)
        config_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)

        # Create __init__.py files
        (output_dir / "__init__.py").touch(exist_ok=True)
        (group_dir / "__init__.py").touch(exist_ok=True)
        (tests_dir / "__init__.py").touch(exist_ok=True)

        # Create service group module
        group_module_name = f"{group_name.lower().replace('-', '_')}_group"
        group_class_name = f"{group_name.title().replace('-', '')}Group"

        group_module_content = f'''"""
{name} ServiceGroup implementation.

This module defines the {group_class_name} class which provides operations for {description}.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

import automcp
from automcp.group import ServiceGroup


class {group_class_name}(ServiceGroup):
    """ServiceGroup for {description}."""
    
    @automcp.operation
    def hello_world(self) -> str:
        """Return a simple greeting message."""
        return f"Hello from {group_name}!"
    
    
    class EchoInput(BaseModel):
        """Input schema for the echo operation."""
        text: str = Field(..., description="Text to echo back")
        
    @automcp.operation
    def echo(self, input: EchoInput) -> str:
        """Echo back the provided text."""
        return f"Echo: {{input.text}}"


    class CountToInput(BaseModel):
        """Input schema for the count_to operation."""
        number: int = Field(..., description="Number to count to", gt=0)
        
    @automcp.operation
    def count_to(self, input: CountToInput) -> str:
        """Count from 1 to the specified number."""
        numbers = list(range(1, input.number + 1))
        return ", ".join(str(n) for n in numbers)
'''

        # Write the group module
        with open(group_dir / f"{group_module_name}.py", "w") as f:
            f.write(group_module_content)

        # Create a basic config file
        config_content = f"""{{
  "name": "{group_name}",
  "description": "{description}",
  "packages": [],
  "config": {{}},
  "env_vars": {{}}
}}
"""

        # Write the config file
        with open(config_dir / f"{group_name}.json", "w") as f:
            f.write(config_content)

        # Create a basic test file
        test_content = f'''"""
Tests for the {group_class_name}.
"""

import pytest
from automcp.server import AutoMCPServer
from automcp.testing import create_connected_server_and_client
from automcp.utils import load_config
from pathlib import Path

from ..groups.{group_module_name} import {group_class_name}


@pytest.fixture
async def server_and_client():
    """Create a server and client for testing."""
    # Load the configuration file
    config_path = Path(__file__).parent.parent / "config" / "{group_name}.json"
    config = load_config(config_path)
    
    # Create the server with the loaded config
    server = AutoMCPServer("{group_name}-test-server", config)
    
    # Initialize the group
    group = {group_class_name}()
    group.config = config
    server.groups["{group_name}"] = group
    
    # Create connected server and client
    async with create_connected_server_and_client(server) as (server, client):
        yield server, client


@pytest.mark.asyncio
async def test_hello_world(server_and_client):
    """Test the hello_world operation."""
    server, client = server_and_client
    
    # Call the operation
    response = await client.call_tool("{group_name}.hello_world", {{}})
    
    # Get the text from the first content item
    response_text = response.content[0].text if response.content else ""
    
    # Check the response
    assert "Hello from {group_name}" in response_text


@pytest.mark.asyncio
async def test_echo(server_and_client):
    """Test the echo operation."""
    server, client = server_and_client
    
    # Call the operation
    test_text = "Testing AutoMCP"
    response = await client.call_tool("{group_name}.echo", {{"text": test_text}})
    
    # Get the text from the first content item
    response_text = response.content[0].text if response.content else ""
    
    # Check the response
    assert f"Echo: {{test_text}}" in response_text


@pytest.mark.asyncio
async def test_count_to(server_and_client):
    """Test the count_to operation."""
    server, client = server_and_client
    
    # Call the operation
    test_number = 5
    response = await client.call_tool("{group_name}.count_to", {{"number": test_number}})
    
    # Get the text from the first content item
    response_text = response.content[0].text if response.content else ""
    
    # Check the response
    expected = "1, 2, 3, 4, 5"
    assert expected in response_text
'''

        # Write the test file
        with open(tests_dir / f"test_{group_module_name}.py", "w") as f:
            f.write(test_content)

        # Create a server.py file
        server_content = f'''#!/usr/bin/env python3
"""
Standalone server script for {name}.

This script:
1. Loads the {group_class_name} configuration
2. Creates an AutoMCPServer instance with the {group_class_name}
3. Makes it accessible via MCP stdio protocol

Usage:
    python server.py
"""

import asyncio
import os
import sys
from pathlib import Path

from automcp.server import AutoMCPServer
from automcp.utils import load_config
from groups.{group_module_name} import {group_class_name}

# Configure server to use stdio for MCP communication
os.environ["AUTOMCP_SERVER_MODE"] = "stdio"


async def main():
    """Run the {group_class_name} server with stdio MCP protocol."""
    # Get the path to the config file
    config_path = Path(__file__).parent / "config" / "{group_name}.json"

    if not config_path.exists():
        print(f"Error: Configuration file {{config_path}} not found", file=sys.stderr)
        sys.exit(1)

    # Load the configuration from the file
    try:
        config = load_config(config_path)
        print(f"Loaded configuration from {{config_path}}", file=sys.stderr)
    except Exception as e:
        print(f"Error: Failed to load configuration: {{e}}", file=sys.stderr)
        sys.exit(1)

    # Create the server with the loaded config
    server = AutoMCPServer("{group_name}-mcp-server", config)

    # Ensure the group is registered
    group = {group_class_name}()
    group.config = config
    server.groups["{group_name}"] = group

    # Print available tools to stderr (not to interfere with stdio protocol)
    print(f"Starting {group_class_name} MCP server...", file=sys.stderr)
    print(f"Available tools:", file=sys.stderr)
    for op_name in group.registry.keys():
        print(f"  - {group_name}.{{op_name}}", file=sys.stderr)

    try:
        # Start the server using stdio protocol
        await server.start()
    except KeyboardInterrupt:
        print("\\nShutting down server...", file=sys.stderr)
        await server.stop()
        print("Server stopped", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\nServer stopped by user", file=sys.stderr)
'''

        # Write the server.py file
        with open(output_dir / "server.py", "w") as f:
            f.write(server_content)

        # Make the server.py file executable
        os.chmod(output_dir / "server.py", 0o755)

        # Create a README.md file
        readme_content = f"""# {name}

{description}

## Installation

```bash
pip install -e .
```

## Usage

### Running the Server

```bash
python server.py
```

### Testing

```bash
pytest
```

## API Documentation

### {group_class_name}

#### hello_world

Return a simple greeting message.

#### echo

Echo back the provided text.

Parameters:
- `text`: Text to echo back

#### count_to

Count from 1 to the specified number.

Parameters:
- `number`: Number to count to (must be greater than 0)
"""

        # Write the README.md file
        with open(output_dir / "README.md", "w") as f:
            f.write(readme_content)

        # Create a basic pyproject.toml file
        pyproject_content = f"""[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{name.lower().replace(' ', '-').replace('_', '-')}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.10"
dependencies = [
    "automcp>=0.1.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
"""

        # Write the pyproject.toml file
        with open(output_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        # Show success message
        console.print(
            f"\n[bold green]✓[/bold green] Created AutoMCP project at [cyan]{output_dir}[/cyan]"
        )

        # Show next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("1. Navigate to the project directory:")
        console.print(f"   cd {output_dir}")
        console.print("2. Install the project in development mode:")
        console.print("   pip install -e .")
        console.print("3. Run the tests:")
        console.print("   pytest")
        console.print("4. Start the server:")
        console.print("   python server.py")
        console.print("5. Generate an MCP configuration for Roo:")
        console.print(f"   automcp generate-config config/{group_name}.json")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def verify(
    test_type: str = typer.Option(
        "all", help="Test type: all, single-group, multi-group, timeout, schema"
    ),
    timeout: float = typer.Option(1.0, help="Timeout value in seconds"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """Verify AutoMCP installation and functionality."""
    from .verification import Verifier

    verifier = Verifier(verbose=verbose)
    asyncio.run(verifier.run(test_type, timeout))
    verifier.print_results()


@app.command()
def test(
    test_dir: str = typer.Option(
        "tests/", help="Directory containing the tests to run"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Generate coverage information"
    ),
    html_report: bool = typer.Option(
        False, "--html-report", help="Generate HTML coverage report"
    ),
    package: str = typer.Option("automcp", help="Package to measure coverage for"),
    report_path: Optional[Path] = typer.Option(
        None, "--report", "-r", help="Path to save the test report"
    ),
):
    """Run tests for the AutoMCP installation and generate a test report."""
    from .utils import generate_test_report, run_tests

    # Run the tests
    test_result = run_tests(
        test_dir=test_dir,
        verbose=verbose,
        coverage=coverage,
        html_report=html_report,
        package=package,
    )

    # Generate the test report
    report_file = generate_test_report(
        test_result=test_result,
        output_path=report_path,
        title="AutoMCP Test Report",
        include_coverage_info=coverage,
    )

    console.print(f"\n[bold green]Test report generated:[/bold green] {report_file}")

    # Return error code if tests failed
    if test_result != 0:
        raise typer.Exit(code=test_result)


@app.command()
def version():
    """Show the AutoMCP version."""
    console.print(f"AutoMCP version: [bold]{__version__}[/bold]")


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
