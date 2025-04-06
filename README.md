# HiveMCP

**HiveMCP** simplifies building complex, configuration-driven **MCP
(Model-Context Protocol)** services in Python. It acts as a smart wrapper around
the high-performance `FastMCP` server, enabling you to define your service's
tools and structure using simple Python classes, decorators, and configuration
files.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- TODO: Add badges for PyPI Version, Build Status, Test Coverage -->

## What is hiveMCP?

Building services that implement the **Model-Context Protocol (MCP)** often
requires handling server setup, tool registration according to the protocol,
configuration management, and context passing. hiveMCP streamlines this:

1. **Define Logic:** Implement your tools or model interactions as methods
   within standard Python classes (Service Groups).
2. **Decorate Tools:** Mark methods you want to expose as MCP tools using the
   simple `@hivemcp.operation` decorator. hiveMCP handles registering them
   correctly with the underlying server.
3. **Configure Structure:** Define which group classes to load and how to name
   their toolsets (operations in MCP terms) using YAML or JSON files.
4. **Run:** Use the `hivemcp` command-line tool to load your configuration and
   instantly run a fully featured FastMCP server implementing MCP, with all your
   tools registered and ready to interact.

hiveMCP manages the dynamic loading, instantiation, correct MCP tool
registration, and server lifecycle, letting you focus on implementing the
specific tools and logic your MCP service needs to provide.

## Features

- 🚀 **Configuration-Driven:** Define service structure, group instances, and
  MCP tool naming declaratively via YAML or JSON.
- ✨ **Decorator-Based Tools:** Expose `async` methods as MCP tools/operations
  using the intuitive `@hivemcp.operation` decorator.
- 📦 **Dynamic Loading:** Service group classes are loaded dynamically based on
  your configuration (`class_path`), promoting modularity for different
  toolsets.
- 🛡️ **Schema Validation:** Leverage Pydantic schemas (`@operation(schema=...)`)
  for automatic validation of MCP operation inputs and clearer tool interfaces.
- ⚙️ **FastMCP Integration:** Built directly on top of the efficient `FastMCP`
  library, which handles the core MCP server logic and protocol communication.
- 📄 **Stateful Tool Groups:** Group classes are instantiated, allowing tools
  (operations) within a group instance to maintain state across calls if needed.
- 🔧 **Configurable Instances:** Optionally pass custom configuration
  dictionaries from your config file to your group class instances during
  initialization.

## Installation

Ensure you have Python 3.10+ and `uv` (or `pip`) installed.

```bash
uv venv
source .venv/bin/activate
uv pip install hivemcp
```

## Quick Start

Let's create a very simple "Greeter" service and configure a client for it. An
operation decorated function must be `async` and must only take one parameter:
`request` (which can be `None` if no input is needed)

1. **Create a Service Group Class (`greeter.py`):**
   ```python
   # file: greeter.py
   from hivemcp import operation, ServiceGroup
   from pydantic import BaseModel

   # Optional: Define an input schema using Pydantic
   class GreetInput(BaseModel):
       name: str

   class GreeterGroup(ServiceGroup):
       """A very simple group that offers greetings."""

       @operation(name="hello", description="Says hello to the provided name.", schema=GreetInput)
       async def say_hello(self, *, request: GreetInput) -> dict:
           """Returns a personalized greeting."""
           return {"message": f"Hello, {request.name}!"}

       @operation(name="wave") # Takes no input
       async def wave_hand(self, *, request=None) -> dict:
            """Returns a simple wave message."""
            return {"action": "*waves*"}
   ```

2. **Create an hiveMCP Configuration File (`greeter.json`):**
   ```json
   {
     "name": "greeter",
     "class_path": "greeter:GreeterGroup",
     "description": "A simple greeting service."
   }
   ```
   _(This tells hiveMCP to load the `GreeterGroup` class from `greeter.py` and
   give its tools the prefix `greeter`.)_

3. **Add the hiveMCP Server to MCP client:**
   ```json
   {
   ```

"mcpServers": { "data-processor": { "command": "uv", "args": [ "run", "python",
"-m", "hivemcp.cli", "absolute/path/to/your_group.json" ] } } }

```
_(The server starts, listening via stdio by default, and makes the
`greeter.hello` and `greeter.wave` MCP operations available.)_



This quick start now shows the full loop: defining the service with hiveMCP,
running it, configuring a standard MCP client to connect to it, and interacting.

### Configuration

hiveMCP uses configuration files (YAML or JSON) to define services.

- **`GroupConfig`:** Defines a single group instance (like `greeter.json`
above). Requires `name` (MCP tool prefix) and `class_path`.
- **`ServiceConfig`:** Defines a service composed of multiple `GroupConfig`
instances (using YAML is often clearer for this). Allows building complex
services.

_(Refer to the `docs/` directory for detailed configuration options.)_

### Creating Service Groups

Implement logic in Python classes and use `@hivemcp.operation` on `async def`
methods to expose them as MCP tools (operations). Optionally use Pydantic
schemas for input validation.

_(Refer to the `docs/` directory for guides on creating groups, using schemas,
and accessing configuration.)_

## Contributing

Contributions to the core `hivemcp` library are welcome! Please read the
[**Development Style Guide (`dev_style.md`)**](./dev_style.md) before starting.
It contains essential information on coding standards, testing, and the
contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE)
file for details.
```
