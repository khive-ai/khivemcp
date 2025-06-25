# khivemcp

**khivemcp** simplifies building complex, configuration-driven **MCP
(Model-Context Protocol)** services in Python. It acts as a smart wrapper around
the high-performance `FastMCP` server, enabling you to define your service's
tools and structure using simple Python classes, decorators, and configuration
files.

## What is khivemcp?

Building services that implement the **Model-Context Protocol (MCP)** often
requires handling server setup, tool registration according to the protocol,
configuration management, and input validation. khivemcp streamlines this:

1. **Define Logic:** Implement your tools (model interactions, data processors,
   etc.) in Python classes called _Service Groups_.
2. **Decorate Tools:** Mark the methods you want to expose as MCP operations
   (tools) via the simple `@khivemcp.operation` decorator. khivemcp handles
   registering them with the underlying server.
3. **Configure Structure:** Define which service group classes to load, how to
   name them, and pass any custom config using YAML or JSON files.
4. **Run:** Use the `khivemcp` command-line tool to load your configuration and
   instantly run a fully featured FastMCP server implementing MCP, with all your
   tools registered.

khivemcp manages dynamic loading, instantiation, correct MCP operation
registration, and server lifecycle, letting you focus on implementing your
tools' logic.

## Features

- 🚀 **Configuration-Driven:** Define service structure, group instances, and
  MCP tool naming declaratively (YAML or JSON).
- ✨ **Decorator-Based Tools:** Expose `async` methods as MCP operations with
  `@khivemcp.operation`.
- 📦 **Dynamic Loading:** Service group classes are loaded dynamically from
  `class_path`, promoting modular, composable toolsets.
- 🛡️ **Schema Validation:** Leverage Pydantic models for automatic validation of
  MCP operation inputs.
- ⚙️ **FastMCP Integration:** Built on top of `FastMCP`, which handles core MCP
  server logic.
- 📄 **Stateful Tool Groups:** Each service group class is instantiated once,
  allowing operations (methods) to share internal state.
- 🔧 **Configurable Instances:** Pass config dicts from your config file
  directly to the group constructor.

For usage details, see the [Quickstart](./getting-started/quickstart.md).
