# MCP Python SDK

<div align="center">

<strong>Python implementation of the Model Context Protocol (MCP)</strong>

[![PyPI][pypi-badge]][pypi-url] [![MIT licensed][mit-badge]][mit-url]
[![Python Version][python-badge]][python-url]
[![Documentation][docs-badge]][docs-url]
[![Specification][spec-badge]][spec-url]
[![GitHub Discussions][discussions-badge]][discussions-url]

</div>

<!-- omit in toc -->

## Table of Contents

- [MCP Python SDK](#mcp-python-sdk)
  - [Overview](#overview)
  - [Installation](#installation)
    - [Adding MCP to your python project](#adding-mcp-to-your-python-project)
    - [Running the standalone MCP development tools](#running-the-standalone-mcp-development-tools)
  - [Quickstart](#quickstart)
  - [What is MCP?](#what-is-mcp)
  - [Core Concepts](#core-concepts)
    - [Server](#server)
    - [Resources](#resources)
    - [Tools](#tools)
    - [Prompts](#prompts)
    - [Images](#images)
    - [Context](#context)
  - [Running Your Server](#running-your-server)
    - [Development Mode](#development-mode)
    - [Claude Desktop Integration](#claude-desktop-integration)
    - [Direct Execution](#direct-execution)
    - [Mounting to an Existing ASGI Server](#mounting-to-an-existing-asgi-server)
  - [Examples](#examples)
    - [Echo Server](#echo-server)
    - [SQLite Explorer](#sqlite-explorer)
  - [Advanced Usage](#advanced-usage)
    - [Low-Level Server](#low-level-server)
    - [Writing MCP Clients](#writing-mcp-clients)
    - [MCP Primitives](#mcp-primitives)
    - [Server Capabilities](#server-capabilities)
  - [Documentation](#documentation)
  - [Contributing](#contributing)
  - [License](#license)

[pypi-badge]: https://img.shields.io/pypi/v/mcp.svg
[pypi-url]: https://pypi.org/project/mcp/
[mit-badge]: https://img.shields.io/pypi/l/mcp.svg
[mit-url]: https://github.com/modelcontextprotocol/python-sdk/blob/main/LICENSE
[python-badge]: https://img.shields.io/pypi/pyversions/mcp.svg
[python-url]: https://www.python.org/downloads/
[docs-badge]: https://img.shields.io/badge/docs-modelcontextprotocol.io-blue.svg
[docs-url]: https://modelcontextprotocol.io
[spec-badge]: https://img.shields.io/badge/spec-spec.modelcontextprotocol.io-blue.svg
[spec-url]: https://spec.modelcontextprotocol.io
[discussions-badge]: https://img.shields.io/github/discussions/modelcontextprotocol/python-sdk
[discussions-url]: https://github.com/modelcontextprotocol/python-sdk/discussions

## Overview

The Model Context Protocol allows applications to provide context for LLMs in a
standardized way, separating the concerns of providing context from the actual
LLM interaction. This Python SDK implements the full MCP specification, making
it easy to:

- Build MCP clients that can connect to any MCP server
- Create MCP servers that expose resources, prompts and tools
- Use standard transports like stdio and SSE
- Handle all MCP protocol messages and lifecycle events

## Installation

### Adding MCP to your python project

We recommend using [uv](https://docs.astral.sh/uv/) to manage your Python
projects.

If you haven't created a uv-managed project yet, create one:

```bash
uv init mcp-server-demo
cd mcp-server-demo
```

Then add MCP to your project dependencies:

```bash
uv add "mcp[cli]"
```

Alternatively, for projects using pip for dependencies:

```bash
pip install "mcp[cli]"
```

### Running the standalone MCP development tools

To run the mcp command with uv:

```bash
uv run mcp
```

## Quickstart

Let's create a simple MCP server that exposes a calculator tool and some data:

```python
# server.py
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
```

You can install this server in [Claude Desktop](https://claude.ai/download) and
interact with it right away by running:

```bash
mcp install server.py
```

Alternatively, you can test it with the MCP Inspector:

```bash
mcp dev server.py
```

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets you
build servers that expose data and functionality to LLM applications in a
secure, standardized way. Think of it like a web API, but specifically designed
for LLM interactions. MCP servers can:

- Expose data through **Resources** (think of these sort of like GET endpoints;
  they are used to load information into the LLM's context)
- Provide functionality through **Tools** (sort of like POST endpoints; they are
  used to execute code or otherwise produce a side effect)
- Define interaction patterns through **Prompts** (reusable templates for LLM
  interactions)
- And more!

## Core Concepts

### Server

The FastMCP server is your core interface to the MCP protocol. It handles
connection management, protocol compliance, and message routing:

```python
# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fake_database import Database  # Replace with your actual DB type

from mcp.server.fastmcp import Context, FastMCP

# Create a named server
mcp = FastMCP("My App")

# Specify dependencies for deployment and development
mcp = FastMCP("My App", dependencies=["pandas", "numpy"])


@dataclass
class AppContext:
    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        # Cleanup on shutdown
        await db.disconnect()


# Pass lifespan to server
mcp = FastMCP("My App", lifespan=app_lifespan)


# Access type-safe lifespan context in tools
@mcp.tool()
def query_db(ctx: Context) -> str:
    """Tool that uses initialized resources"""
    db = ctx.request_context.lifespan_context["db"]
    return db.query()
```

### Resources

Resources are how you expose data to LLMs. They're similar to GET endpoints in a
REST API - they provide data but shouldn't perform significant computation or
have side effects:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")


@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"


@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """Dynamic user data"""
    return f"Profile data for user {user_id}"
```

### Tools

Tools let LLMs take actions through your server. Unlike resources, tools are
expected to perform computation and have side effects:

```python
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")


@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI given weight in kg and height in meters"""
    return weight_kg / (height_m**2)


@mcp.tool()
async def fetch_weather(city: str) -> str:
    """Fetch current weather for a city"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.text
```

### Prompts

Prompts are reusable templates that help LLMs interact with your server
effectively:

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("My App")


@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]
```

### Images

FastMCP provides an `Image` class that automatically handles image data:

```python
from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

mcp = FastMCP("My App")


@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")
```

### Context

The Context object gives your tools and resources access to MCP capabilities:

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("My App")


@mcp.tool()
async def long_task(files: list[str], ctx: Context) -> str:
    """Process multiple files with progress tracking"""
    for i, file in enumerate(files):
        ctx.info(f"Processing {file}")
        await ctx.report_progress(i, len(files))
        data, mime_type = await ctx.read_resource(f"file://{file}")
    return "Processing complete"
```

## Running Your Server

### Development Mode

The fastest way to test and debug your server is with the MCP Inspector:

```bash
mcp dev server.py

# Add dependencies
mcp dev server.py --with pandas --with numpy

# Mount local code
mcp dev server.py --with-editable .
```

### Claude Desktop Integration

Once your server is ready, install it in Claude Desktop:

```bash
mcp install server.py

# Custom name
mcp install server.py --name "My Analytics Server"

# Environment variables
mcp install server.py -v API_KEY=abc123 -v DB_URL=postgres://...
mcp install server.py -f .env
```

### Direct Execution

For advanced scenarios like custom deployments:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")

if __name__ == "__main__":
    mcp.run()
```

Run it with:

```bash
python server.py
# or
mcp run server.py
```

### Mounting to an Existing ASGI Server

You can mount the SSE server to an existing ASGI server using the `sse_app`
method. This allows you to integrate the SSE server with other ASGI
applications.

```python
from starlette.applications import Starlette
from starlette.routing import Mount, Host
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("My App")

# Mount the SSE server to the existing ASGI server
app = Starlette(
    routes=[
        Mount('/', app=mcp.sse_app()),
    ]
)

# or dynamically mount as host
app.router.routes.append(Host('mcp.acme.corp', app=mcp.sse_app()))
```

For more information on mounting applications in Starlette, see the
[Starlette documentation](https://www.starlette.io/routing/#submounting-routes).

## Examples

### Echo Server

A simple server demonstrating resources, tools, and prompts:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Echo")


@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """Echo a message as a resource"""
    return f"Resource echo: {message}"


@mcp.tool()
def echo_tool(message: str) -> str:
    """Echo a message as a tool"""
    return f"Tool echo: {message}"


@mcp.prompt()
def echo_prompt(message: str) -> str:
    """Create an echo prompt"""
    return f"Please process this message: {message}"
```

### SQLite Explorer

A more complex example showing database integration:

```python
import sqlite3

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQLite Explorer")


@mcp.resource("schema://main")
def get_schema() -> str:
    """Provide the database schema as a resource"""
    conn = sqlite3.connect("database.db")
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall()
    return "\n".join(sql[0] for sql in schema if sql[0])


@mcp.tool()
def query_data(sql: str) -> str:
    """Execute SQL queries safely"""
    conn = sqlite3.connect("database.db")
    try:
        result = conn.execute(sql).fetchall()
        return "\n".join(str(row) for row in result)
    except Exception as e:
        return f"Error: {str(e)}"
```

## Advanced Usage

### Low-Level Server

For more control, you can use the low-level server implementation directly. This
gives you full access to the protocol and allows you to customize every aspect
of your server, including lifecycle management through the lifespan API:

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fake_database import Database  # Replace with your actual DB type

from mcp.server import Server


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """Manage server startup and shutdown lifecycle."""
    # Initialize resources on startup
    db = await Database.connect()
    try:
        yield {"db": db}
    finally:
        # Clean up on shutdown
        await db.disconnect()


# Pass lifespan to server
server = Server("example-server", lifespan=server_lifespan)


# Access lifespan context in handlers
@server.call_tool()
async def query_db(name: str, arguments: dict) -> list:
    ctx = server.request_context
    db = ctx.lifespan_context["db"]
    return await db.query(arguments["query"])
```

The lifespan API provides:

- A way to initialize resources when the server starts and clean them up when it
  stops
- Access to initialized resources through the request context in handlers
- Type-safe context passing between lifespan and request handlers

```python
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Create a server instance
server = Server("example-server")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="example-prompt",
            description="An example prompt template",
            arguments=[
                types.PromptArgument(
                    name="arg1", description="Example argument", required=True
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name != "example-prompt":
        raise ValueError(f"Unknown prompt: {name}")

    return types.GetPromptResult(
        description="Example prompt",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text="Example prompt text"),
            )
        ],
    )


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="example",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

### Writing MCP Clients

The SDK provides a high-level client interface for connecting to MCP servers:

```python
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["example_server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)


# Optional: create a sampling callback
async def handle_sampling_message(
    message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-3.5-turbo",
        stopReason="endTurn",
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=handle_sampling_message
        ) as session:
            # Initialize the connection
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()

            # Get a prompt
            prompt = await session.get_prompt(
                "example-prompt", arguments={"arg1": "value"}
            )

            # List available resources
            resources = await session.list_resources()

            # List available tools
            tools = await session.list_tools()

            # Read a resource
            content, mime_type = await session.read_resource("file://some/path")

            # Call a tool
            result = await session.call_tool("tool-name", arguments={"arg1": "value"})


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

### MCP Primitives

The MCP protocol defines three core primitives that servers can implement:

| Primitive | Control                | Description                                       | Example Use                  |
| --------- | ---------------------- | ------------------------------------------------- | ---------------------------- |
| Prompts   | User-controlled        | Interactive templates invoked by user choice      | Slash commands, menu options |
| Resources | Application-controlled | Contextual data managed by the client application | File contents, API responses |
| Tools     | Model-controlled       | Functions exposed to the LLM to take actions      | API calls, data updates      |

### Server Capabilities

MCP servers declare capabilities during initialization:

| Capability   | Feature Flag                  | Description                     |
| ------------ | ----------------------------- | ------------------------------- |
| `prompts`    | `listChanged`                 | Prompt template management      |
| `resources`  | `subscribe`<br/>`listChanged` | Resource exposure and updates   |
| `tools`      | `listChanged`                 | Tool discovery and execution    |
| `logging`    | -                             | Server logging configuration    |
| `completion` | -                             | Argument completion suggestions |

## Documentation

- [Model Context Protocol documentation](https://modelcontextprotocol.io)
- [Model Context Protocol specification](https://spec.modelcontextprotocol.io)
- [Officially supported servers](https://github.com/modelcontextprotocol/servers)

## Contributing

We are passionate about supporting contributors of all levels of experience and
would love to see you get involved in the project. See the
[contributing guide](CONTRIBUTING.md) to get started.

## License

This project is licensed under the MIT License - see the LICENSE file for
details.



# Model Context Protocol (MCP) Usage Guide

## 1. **High-Level Overview of MCP**

1. **What MCP Is**
   - MCP (Model Context Protocol) is a standardized, JSON-RPC 2.0–based protocol
     for interacting with large language models and related operations (aka
     “tools”), resources (files/data), or prompt templates.
   - It allows a client and server to communicate with well-defined methods
     like:
     - `tools/call` – to invoke a server-defined function or action
     - `prompts/get` – to retrieve or render a particular prompt template
     - `resources/read` – to access data from a server-managed resource

2. **Why MCP for LLMs**
   - Instead of coding ad-hoc endpoints or complicated client–server logic, MCP
     enforces a consistent request–response structure.
   - The **server** can easily advertise tools, resources, or prompts it
     provides.
   - The **client** can discover and invoke these features without needing
     custom endpoints for each new function.

3. **Key MCP Operations**
   - **Initialization**: The client calls `initialize`, the server responds with
     version/capabilities.
   - **Tools**: The client calls `tools/list` to see available actions,
     `tools/call` to run them.
   - **Prompts**: The client calls `prompts/list` or `prompts/get` to get or
     render prompt templates.
   - **Resources**: The client calls `resources/list` or `resources/read` to
     find data or read it.
   - **Logging / Progress**: The server can send logs or progress notifications
     to the client.

---

## 2. **MCP: Installation & Basic Setup**

1. **Install the Python SDK**
   ```bash
   pip install mcp
   # or
   pip install mcp[cli]
   ```
   - If you also want SSE or WebSocket features, ensure you have the relevant
     extras installed (e.g. `pip install httpx_sse websockets`).

2. **Directory Layout** (example)
   ```
   my_project/
   ├── server.py
   ├── group_logic.py  (optional if you’re using the 'group+operation' pattern)
   ├── prompts/        (if you store prompt templates)
   └── ...
   ```

3. **Core Modules**
   - `mcp.server.fastmcp.FastMCP` → The high-level server class for building an
     MCP server.
   - `mcp.client.session.ClientSession` → The main client session for calling
     the server.
   - `mcp.types` → Defines the Pydantic models for requests, notifications, etc.

---

## 3. **Building an MCP Server with `fastmcp`**

### 3.1 **Minimal Example**

```python
# server.py

from mcp.server.fastmcp import FastMCP, Context

# Step 1: Create the server
server = FastMCP(name="MyLLMServer", instructions="This server offers LLM tools and resources")

# Step 2: Define a simple tool
@server.tool(name="math.add")
def add_numbers(x: float, y: float) -> str:
    """Adds two numbers and returns the result as a string."""
    return str(x + y)

# Step 3: Define a more advanced tool with Context injection
@server.tool(name="math.slow_add")
async def slow_add(x: float, y: float, ctx: Context) -> str:
    """Slowly adds two numbers and logs progress."""
    await ctx.info("Starting slow_add operation...")
    await ctx.report_progress(0, total=100)

    # Simulate chunking
    for i in range(0, 101, 20):
        await ctx.report_progress(i)
        # do some partial work here
    result = x + y

    await ctx.info(f"Done. The result is {result}")
    return str(result)

# Step 4: Run the server using stdio
if __name__ == "__main__":
    server.run("stdio")
```

**What this does**:

- Exports two “tools” named `"math.add"` and `"math.slow_add"`. Clients can
  discover them with `tools/list` and invoke them with `tools/call`.
- The `slow_add` function uses an **async** approach with logging/progress
  (`ctx.info`, `ctx.report_progress`) to illustrate concurrency and
  notifications.

### 3.2 **Using “Groups” & “Operations” (AutoMCP-Style)**

If you want to maintain a bigger codebase with the concept of groups and
decorated operations, you typically:

1. **Create a “group” class**:
   ```python
   # group_logic.py
   from mcp.server.fastmcp import Context

   class MathGroup:
       def __init__(self, config):
           self.config = config

       async def add(self, x: float, y: float) -> str:
           return str(x + y)

       async def slow_add(self, x: float, y: float, ctx: Context) -> str:
           # same logic as above
           ...
   ```

2. **Reflect & Register** (pseudocode):
   ```python
   # server.py
   from mcp.server.fastmcp import FastMCP, Context
   from group_logic import MathGroup

   server = FastMCP(name="MyLLMServer")
   math_group = MathGroup(config={...})

   # Register dynamic tools
   for method_name in ("add", "slow_add"):
       async def dynamic_tool_wrapper(ctx: Context, **kwargs):
           # forward the call to the group
           method = getattr(math_group, method_name)
           return await method(**kwargs, ctx=ctx)  # if it expects ctx

       server.add_tool(dynamic_tool_wrapper, name=f"math.{method_name}")

   # Then run
   if __name__ == "__main__":
       server.run("stdio")
   ```

**This approach**:

- Leaves you free to define large code structures for “group logic,” then
  automatically register them as tools.
- You still rely on the built-in tool-handling from `fastmcp`.

---

## 4. **Client Usage: Invoking Your MCP Server**

### 4.1 **Python Client Example**

```python
# client_example.py
import anyio
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

async def main():
    # Suppose we run your server as a subprocess
    # We'll connect via stdio (like an embedded client)
    command_or_url = "python server.py"

    async with stdio_client(command=command_or_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Step 1: Initialize
            await session.initialize()

            # Step 2: List Tools
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])

            # Step 3: Call the 'math.add' tool
            resp = await session.call_tool("math.add", arguments={"x": 3.14, "y": 2.71})
            print("math.add result:", resp.content[0].text)

anyio.run(main)
```

**Key steps**:

1. Connect via `stdio_client` (or `sse_client`, `websocket_client` if your
   server runs SSE/WebSocket).
2. Create a `ClientSession`.
3. Call `initialize()` to handshake with the server.
4. Use standard client methods like `list_tools()`, `call_tool()`,
   `list_resources()`, etc.

### 4.2 **CLI Integration**

- If you installed `mcp[cli]`, you can do `mcp dev server.py` to spawn a dev
  inspector interface.
- Or `mcp run server.py` to run a server directly.

---

## 5. **Resources & Prompts**

### 5.1 **Defining Resources**

**In `fastmcp`** you can do:

```python
from mcp.server.fastmcp.resources import FileResource, FunctionResource
from pathlib import Path

# Example 1: static file resource
server.add_resource(
    FileResource(
        uri="file://mydata.txt",    # A unique URI
        path=Path("/absolute/path/to/data.txt"),
        name="mydata",
        description="Some text file",
        is_binary=False
    )
)

# Example 2: dynamic resource from function
async def dynamic_data():
    # Possibly fetch data from a DB or do some computation
    return "Hello from dynamic_data"

server.add_resource(
    FunctionResource(
        uri="resource://dynamic",
        name="dynamic_data_resource",
        fn=dynamic_data
    )
)
```

Clients can now call:

- `resources/list` → sees `file://mydata.txt` and `resource://dynamic`.
- `resources/read` (with the URI) → gets the file or dynamic content.

### 5.2 **Defining Prompts**

**In `fastmcp`**:

```python
from mcp.server.fastmcp.prompts.base import Prompt

async def my_prompt_logic(**kwargs):
    # Return list of messages
    return [
        {"role": "user", "content": {"type": "text", "text": f"Hello {kwargs['name']}" }}
    ]

server.add_prompt(
    Prompt(
        name="greeting-prompt",
        description="Greets the user by name",
        fn=my_prompt_logic
    )
)
```

Now a client can do:

- `prompts/list` → sees “greeting-prompt.”
- `prompts/get` with arguments `{ "name": "Alice" }` → obtains the rendered
  message.

---

## 6. **Logging & Progress Notifications**

1. **Context Logging**
   - If your tool function includes a `Context` parameter, you can do:
     ```python
     async def some_tool(x: int, ctx: Context) -> str:
         await ctx.debug(f"Starting with x={x}")
         # ...
         await ctx.info("Halfway done!")
         return "Done"
     ```
   - On the client side, you might see these logs as `notifications/message`.

2. **Progress**
   - Similarly, if a request has `_meta.progressToken`, you can do:
     ```python
     async def some_long_task(ctx: Context):
         await ctx.report_progress(0, total=100)
         for i in range(1, 101):
             # do a chunk of work
             await ctx.report_progress(i)
     ```
   - The client sees these as `notifications/progress`.

---

## 7. **Concurrency, SSE, and WebSockets**

1. **Async Concurrency**
   - `fastmcp` uses `anyio`. Each incoming request is handled in a separate
     task, so your server can process multiple tools in parallel.
   - Make sure your code is thread-safe or do concurrency checks.

2. **Using SSE**
   - Instead of `server.run("stdio")`, do `server.run("sse")`.
   - This stands up an HTTP SSE endpoint (default `localhost:8000/sse` and a
     “post” endpoint for messages).
   - The client side can connect with `sse_client("http://localhost:8000/sse")`.

3. **Using WebSockets**
   - `fastmcp` also has a `websocket()` approach in `mcp.client.websocket`.
   - To create a server with WebSocket endpoints, do `server.run("websocket")`
     or define your own Starlette routes.

---

## 8. **Extended Example: Tool + Resource + Prompt**

Here’s a code snippet that shows everything:

```python
# server_extended.py
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.resources import FileResource, FunctionResource
from mcp.server.fastmcp.prompts import Prompt

server = FastMCP(name="LLMServerExtended", instructions="Demo server with tools, resources, prompts")

# 1) Tools
@server.tool(name="math.add")
def add_nums(a: float, b: float) -> str:
    return str(a + b)

@server.tool()
async def advanced_tool(x: int, ctx: Context) -> str:
    await ctx.info("In advanced_tool")
    # do something
    return f"Processed {x}"

# 2) Resources
server.add_resource(FileResource(
    uri="file://demo.txt",
    path="/absolute/path/demo.txt",
    name="Demo Text"
))

async def random_resource():
    # Some dynamic logic
    return "Randomly generated data"

server.add_resource(FunctionResource(
    uri="resource://random",
    fn=random_resource,
    name="Random Data"
))

# 3) Prompts
async def greet_prompt_logic(name: str) -> list:
    return [
       {"role": "user", "content": { "type": "text", "text": f"Hello {name}!"}}
    ]

server.add_prompt(Prompt(
    name="greet-user",
    description="Greets user by name",
    fn=greet_prompt_logic
))

if __name__ == "__main__":
    # 4) Start the server over stdio or SSE:
    server.run("stdio")
    # or
    # server.run("sse")
```

---

## 9. **Automating with a Team of LLMs**

If you plan to have multiple “LLMs” or developer assistants manage different
pieces of your code:

1. **Tool Definition** (LLM #1, the “Tool Author”):
   - Writes the Python methods, docstrings, logic for each operation.
   - Decorates them with `@server.tool(...)`.

2. **Resource Manager** (LLM #2, the “Resource Curator”):
   - Identifies data sources and decides which resources to define
     (`FileResource`, `FunctionResource`).
   - Possibly sets up dynamic resource loading.

3. **Prompt Designer** (LLM #3):
   - Writes or merges prompt templates, hooking them up as `Prompt` objects or
     using a dynamic approach.
   - Ensures any arguments are documented.

4. **Infra & DevOps** (LLM #4):
   - Chooses how to launch the server (`stdio`, `sse`, or `websocket`).
   - Possibly adds CLI usage or integrates with `mcp install` for Claude Desktop
     config.
   - Tests concurrency, logging, progress notifications, etc.

5. **QA & Testing** (LLM #5):
   - Writes test scripts that do `tools/list`, `tools/call`, `resources/read`,
     etc.
   - Verifies logging & progress via a test client.

---

## 10. **Summary / Best Practices**

1. **Keep It Modular**: If your codebase is large, use the “group + reflection”
   approach, or a “decorator per operation” approach, to keep your server’s main
   code from being cluttered.
2. **Test with a Real MCP Client**: E.g., `mcp dev server.py` or a custom
   `ClientSession`.
3. **Use Asynchronous Tools**: Where possible, define async tool functions so
   you can do long-running tasks with progress updates.
4. **Leverage Prompts & Resources**: This is a big advantage over simpler
   JSON-RPC or HTTP setups. You can dynamically generate or serve data/prompt
   templates.
5. **Logging & Progress**: Provide a richer user experience by sending info logs
   and progress notifications.
6. **Transport**: Choose `stdio` if your environment is typical CLI-based. If
   you want browser-based or network-based usage, go for SSE or WebSockets.

---

### **References & Useful Links**

- **MCP Spec**:
  [ModelContextProtocol/specification](https://github.com/modelcontextprotocol/specification)
- **MCP Python SDK**: [mcp on PyPI](https://pypi.org/project/mcp/)
- **`fastmcp` Docs**: Check source code in `mcp.server.fastmcp` package.
