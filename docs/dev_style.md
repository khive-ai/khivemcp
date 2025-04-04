# AutoMCP Developer Guide

## 1. Introduction

Welcome to developing MCP servers with `automcp`! This guide outlines the
workflow, core concepts, and best practices for building robust and maintainable
servers using this framework.

`automcp` simplifies MCP server creation by leveraging:

- **Configuration Files:** Define your server's structure, dependencies, and
  environment in YAML or JSON.
- **`ServiceGroup` Classes:** Organize your server's logic into reusable Python
  classes.
- **`@operation` Decorator:** Easily expose methods as callable MCP Tools with
  built-in input validation.
- **`FastMCP` Backend:** Under the hood, `automcp` uses the powerful
  `mcp.server.fastmcp.FastMCP` library from the official MCP SDK, giving you
  access to modern MCP features like context injection, logging, progress
  reporting, and flexible transports.

This guide assumes you have a basic understanding of Python and the Model
Context Protocol (MCP).

## 2. Getting Started

### 2.1. Environment Setup

We use `uv` for environment and package management.

1. **Install `uv`:** Follow instructions at
   [astral.sh/uv](https://astral.sh/uv).
2. **Create Environment:** Navigate to your project root and run `uv venv`.
3. **Activate Environment:** Activate the created `.venv` (e.g.,
   `source .venv/bin/activate`).
4. **Install Dependencies:** Run `uv sync` (or `uv pip sync ...`) to install
   dependencies listed in your `pyproject.toml`, including `automcp` itself and
   any packages required by your `ServiceGroup`s.

[See ENV_SETUP.md for more details on `uv` usage.]

### 2.2. Project Structure

Organize your project logically. A recommended structure is:

```
your_server_project/
├── config/
│   └── server.yaml         # AutoMCP configuration file
├── src/
│   └── your_package_name/
│       ├── __init__.py
│       ├── groups/
│       │   ├── __init__.py
│       │   └── my_group.py     # Contains ServiceGroup classes
│       └── schemas.py        # Optional: Pydantic input schemas
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── test_my_group.py
│   └── integration/
│       └── test_server_flow.py
├── pyproject.toml          # uv dependencies, project metadata
└── .env                    # Optional: Environment variables (add to .gitignore)
```

[See PROJECT_SETUP.md for more details.]

## 3. Core Development Workflow (Adding a Tool)

Adding a new MCP Tool typically involves these steps:

1. **Define Requirement:** Clearly state what the new tool should do, its
   inputs, and expected outputs.
2. **Design:**
   - Choose an existing `ServiceGroup` class or create a new one in
     `src/.../groups/`.
   - Define the method signature for your operation within the `ServiceGroup`.
   - (Optional) If inputs are complex, define a Pydantic `BaseModel` schema in
     `schemas.py`.
   - Determine if the operation needs access to MCP capabilities via the
     `Context` object.
3. **Write Failing Test (TDD):**
   - Create a unit test file in `tests/unit/`.
   - Write a `pytest` test case for the new operation that initially fails
     (e.g., asserting the expected output or behavior). Mock dependencies and
     `Context` if needed.
   - [See TDD_SPEC.md and TESTING_STRATEGY.md]
4. **Implement Operation:**
   - Add the method to your `ServiceGroup` class.
   - Decorate it with `@automcp.operation()`.
   - If using an input schema, pass it:
     `@automcp.operation(schema=YourInputSchema)`. Your method will receive the
     validated Pydantic model instance.
   - If needing MCP context, add a parameter type-hinted `ctx: Context` (import
     `mcp.server.fastmcp.Context`). `automcp` will inject it.
   - Implement the core logic. Use `ctx.info()`, `ctx.report_progress()`, etc.,
     if applicable.
   - Return the result (e.g., `str`, `mcp.server.fastmcp.Image`, `list`,
     `None`).
5. **Pass Unit Tests:** Run `uv run pytest tests/unit/` until your new test (and
   others) pass. Refactor code and tests for clarity.
6. **Write Integration Test:**
   - Add a test to `tests/integration/`.
   - Use `mcp.shared.memory.create_connected_server_and_client_session` with a
     minimal test `automcp` config pointing to your group.
   - Use the `ClientSession` to call `call_tool` for your new operation,
     verifying the end-to-end flow and response.
   - [See TESTING_STRATEGY.md]
7. **Configure:**
   - Ensure your `ServiceGroup`'s class path (e.g.,
     `your_package_name.groups.my_group:MyGroupClass`) is correctly mapped in
     your `config/server.yaml` under the `groups` section.
   - Add any required `packages` or `env_vars` to the config.
8. **Verify All Tests:** Run the full test suite: `uv run pytest`. **All tests
   must pass.**
9. **Run/Debug:** Test locally using `automcp run config/server.yaml` or
   interactively with `mcp dev ...`.

## 4. Key `automcp` Concepts

- **Configuration (`config/*.yaml` or `*.json`):**
  - Defines the server `name`, maps group identifiers to Python class paths
    (`module:ClassName`), lists `packages`, and sets `env_vars`.
  - Can define settings globally (`ServiceConfig`) or for specific groups
    (`GroupConfig`).
  - Optionally specifies a `lifespan` function path for setup/teardown.
- **`ServiceGroup` (`automcp.ServiceGroup`):**
  - Your primary container for related logic. Subclass it.
  - Can hold state in instance variables.
  - `automcp` instantiates these based on the config file.
- **`@operation` (`automcp.operation`):**
  - Decorator applied to methods within a `ServiceGroup`.
  - Exposes the method as an MCP Tool. Tool name defaults to
    `{group_name}.{method_name}`.
  - `schema=YourPydanticModel`: Enables automatic validation of arguments passed
    via `call_tool`. The validated model instance is passed to your method.
  - Docstrings become the tool's description in `list_tools`.
- **`Context` (`mcp.server.fastmcp.Context`):**
  - Request this via type hinting in your `@operation` method signature:
    `async def my_op(self, ..., ctx: Context):`.
  - Use `ctx.info()`, `ctx.debug()`, `ctx.warning()`, `ctx.error()` for logging
    to the client.
  - Use `await ctx.report_progress(current, total)` for long-running tasks.
  - Use `await ctx.read_resource("uri")` to access data exposed by this or other
    servers (if configured).
  - Use `await ctx.create_message(...)` to request LLM sampling from the client.
  - Access lifespan data via `ctx.request_context.lifespan_context`.
- **Operation Return Types:**
  - Return `str`, `None`, `mcp.server.fastmcp.Image`, Pydantic models, or
    lists/tuples thereof.
  - `automcp` automatically converts these into the appropriate
    `mcp.types.TextContent`, `mcp.types.ImageContent`, etc., for the `call_tool`
    response.
- **Testing:**
  - **Unit:** `pytest` with mocking. Test `ServiceGroup` method logic.
  - **Integration:** `pytest` with
    `mcp.shared.memory.create_connected_server_and_client_session`. Test
    end-to-end MCP `call_tool` flow.
  - **Requirement:** Tests are mandatory. `uv run pytest` must pass.

## 5. Running and Debugging

- **Direct Run (stdio):**
  ```bash
  automcp run config/server.yaml [--timeout 60]
  ```
- **Interactive Debugging (MCP Inspector):** You often need a small runner
  script to use `mcp dev`.
  ```python
  # run_dev.py
  import asyncio
  from pathlib import Path
  from automcp.server import AutoMCPServer
  from automcp.cli import load_config # Reuse config loading

  config_path = Path("config/server.yaml")
  cfg = load_config(config_path)
  server = AutoMCPServer(name=cfg.name, config=cfg)

  if __name__ == "__main__":
      asyncio.run(server.start()) # Assuming start is async
  ```
  Then run:
  ```bash
  # Make sure dependencies for your server are in pyproject.toml
  mcp dev run_dev.py [--with-editable src] [--with <package>]
  ```
- **Claude Desktop Integration:** Use the official `mcp` CLI to install your
  server runner script. `mcp install` uses the `dependencies` listed in
  `FastMCP` (which `automcp` populates from your config's `packages`).
  ```bash
  # Installs using the runner script and gets packages from config
  mcp install run_dev.py --name "My Cool Server" [-f .env]
  ```

## 6. Standards and Best Practices

- **Code Style:** Follow standard Python conventions (PEP 8, typing). Use tools
  like `ruff` or `black`.
- **Testing:** Adhere strictly to the TDD/Test-Augmented approach. Ensure
  comprehensive test coverage. [See TDD_SPEC.md, TESTING_STRATEGY.md].
- **Commits:** Follow standard commit message guidelines [See COMMIT_GUIDE.md if
  available].
- **Error Handling:** Catch expected exceptions within your `@operation` methods
  and return informative error messages (which `automcp` will package
  correctly). Unhandled exceptions will also be caught and reported as errors.
- **Async:** Use `async def` for operations involving I/O (file access, network
  calls, using `await ctx.read_resource`, etc.) or long computations to avoid
  blocking the server.

## 7. Advanced Topics

- **Lifespan Management:** For setup/teardown logic (like database connections),
  define an `asynccontextmanager` function and specify its path in your
  `automcp` config. The yielded value(s) are accessible via
  `ctx.request_context.lifespan_context`.
- **Complex State:** Manage state within `ServiceGroup` instances. Be mindful of
  potential concurrency issues if multiple operations modify shared state
  (standard Python async considerations apply).

## 8. Further Information

- [MCP SDK README](link/to/mcp/sdk/readme)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [Your Project's Specific Docs] (e.g., config schemas, internal guides)
- Other spec files: `TDD_SPEC.md`, `QA_PROTOCOLS.md`, `TESTING_STRATEGY.md`,
  etc.
