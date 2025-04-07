# khivemcp

**khivemcp** simplifies building complex, configuration-driven **MCP
(Model-Context Protocol)** services in Python. It acts as a smart wrapper around
the high-performance `FastMCP` server, enabling you to define your service's
tools and structure using simple Python classes, decorators, and configuration
files.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![PyPI - Version](https://img.shields.io/pypi/v/khivemcp?labelColor=233476aa&color=231fc935)
![PyPI - Downloads](https://img.shields.io/pypi/dm/khivemcp?color=blue)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)

## Note:

This project is in its early stages. Currently,

- it can only be used in a virtual environment, for example if you are using
  `uv venv` in a VSCode environment, (e.g.
  [`roo`](https://github.com/RooVetGit/Roo-Code),
  [`cursor`](https://www.cursor.com/en),
  [`Github CodeSpace`](https://github.com/features/codespaces) etc.)
- it does **NOT** support [`Claude Desktop`](https://claude.ai/download) due to
  python path issues. If you figure out how to make it work, please open an
  issue or PR.

## What is khivemcp?

Building services that implement the **Model-Context Protocol (MCP)** often
requires handling server setup, tool registration according to the protocol,
configuration management, and context passing. khivemcp streamlines this:

1. **Define Logic:** Implement your tools or model interactions as methods
   within standard Python classes (Service Groups).
2. **Decorate Tools:** Mark methods you want to expose as MCP tools using the
   simple `@khivemcp.operation` decorator. khivemcp handles registering them
   correctly with the underlying server.
3. **Configure Structure:** Define which group classes to load and how to name
   their toolsets (operations in MCP terms) using YAML or JSON files.
4. **Run:** Use the `khivemcp` command-line tool to load your configuration and
   instantly run a fully featured FastMCP server implementing MCP, with all your
   tools registered and ready to interact.

khivemcp manages the dynamic loading, instantiation, correct MCP tool
registration, and server lifecycle, letting you focus on implementing the
specific tools and logic your MCP service needs to provide.

## Features

- 🚀 **Configuration-Driven:** Define service structure, group instances, and
  MCP tool naming declaratively via YAML or JSON.
- ✨ **Decorator-Based Tools:** Expose `async` methods as MCP tools/operations
  using the intuitive `@khivemcp.operation` decorator.
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
uv pip install khivemcp
```

## Quick Start

Let's create a very simple "Greeter" service and configure a client for it. An
operation decorated function must be `async` and must only take one parameter:
`request` (which can be `None` if no input is needed)

1. **Create a Service Group Class (`greeter.py`):**
   ```python
   # file: greeter.py
   from khivemcp import operation, ServiceGroup
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

2. **Create an khivemcp Configuration File (`greeter.json`):**
   ```json
   {
     "name": "greeter",
     "class_path": "greeter:GreeterGroup",
     "description": "A simple greeting service."
   }
   ```
   _(This tells khivemcp to load the `GreeterGroup` class from `greeter.py` and
   give its tools the prefix `greeter`.)_

3. **Add the khivemcp Server to MCP client:**
   ```json
   {
     "mcpServers": {
       "data-processor": {
         "command": "uv",
         "args": [
           "run",
           "python",
           "-m",
           "khivemcp.cli",
           "absolute/path/to/your_group.json"
         ]
       }
     }
   }
   ```

_(The server starts, listening via stdio by default, and makes the
`greeter.hello` and `greeter.wave` MCP operations available.)_

This quick start now shows the full loop: defining the service with khivemcp,
running it, configuring a standard MCP client to connect to it, and interacting.

### Configuration

khivemcp uses configuration files (YAML or JSON) to define services.

- **`GroupConfig`:** Defines a single group instance (like `greeter.json`
  above). Requires `name` (MCP tool prefix) and `class_path`.
- **`ServiceConfig`:** Defines a service composed of multiple `GroupConfig`
  instances (using YAML is often clearer for this). Allows building complex
  services.

_(Refer to the `docs/` directory for detailed configuration options.)_

### Creating Service Groups

Implement logic in Python classes and use `@khivemcp.operation` on `async def`
methods to expose them as MCP tools (operations). Optionally use Pydantic
schemas for input validation.

_(Refer to the `docs/` directory for guides on creating groups, using schemas,
and accessing configuration.)_

## Examples

_Under `examples`_

### Search Group Example

To use the search group example, you must have `EXA_API_KEY` and
`PERPLEXITY_API_KEY` environment variables set, in your `.env` file or in your
environment.

_DO NOT EVER SAVE API KEY IN CONFIG FILE_

if you haven't already, install the required dependencies

```bash
uv pip install "khivemcp[examples]"
```

then add the following to your `mcpServers` in your MCP client configuration:

```json
{
  "mcpServers": {
    "search-service": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "khivemcp.cli",
        "absolute_path_to/examples/config/search_group_config.json"
      ],
      "timeout": 300,
      "alwaysAllow": []
    }
  }
}
```

## Contributing

Contributions to the core `khivemcp` library are welcome! Please read the
[**Development Style Guide (`dev_style.md`)**](./dev_style.md) before starting.
It contains essential information on coding standards, testing, and the
contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE)
file for details.

## Acknowledgements

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/introduction)
- [FastMCP](https://github.com/jlowin/fastmcp)
