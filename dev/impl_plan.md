Below is a **comprehensive, updated specification** that merges **all** relevant
ideas from the MCP SDK documentation, existing `automcp` design choices, and the
newer suggestions on `fastmcp` usage. This document will serve as an
authoritative reference for your team of LLM-based (or human) developers to
**plan, implement, and test** your updated `automcp` framework for various LLM
workflows. We’ll split it into **two main parts**:

1. **Modernizing `automcp`**: A formal spec describing how to transition from
   the old `mcp.server.Server` approach to `mcp.server.fastmcp.FastMCP`.
2. **Using MCP for LLMs**: A developer’s guide showing exactly how to define
   tools, prompts, and resources, plus how concurrency, context injection,
   logging, and more all come together in practice.

---

# Part 1: Modernizing `automcp`

## 1. Overview & Goals

1. **Objective**
   - **Retain** the config-driven approach to MCP server creation while
     **upgrading** from the old `mcp.server.Server` to the newer, more ergonomic
     `fastmcp` layer.
   - **Leverage** advanced features such as `Context`, logging, progress
     notifications, `Image` return types, concurrency controls, and optional
     lifespan management.

2. **Design Philosophy**
   - **Configuration-First**: End users should still supply a YAML/JSON config
     describing service groups, environment variables, or optional resources.
   - **Reflective Operation Discovery**: Keep the idea of `@operation` or
     equivalent decorators in `ServiceGroup` classes for “tools.”
   - **Separation of Concerns**: “Group” classes handle business logic;
     `AutoMCPServer` focuses on registration/orchestration.

---

## 2. Proposed Architecture Changes

1. **Replace** `mcp.server.Server` with `mcp.server.fastmcp.FastMCP` as the
   underlying server.
2. **Compose** a `FastMCP` instance inside `AutoMCPServer` (rather than
   inheriting from it) for clarity and to avoid naming collisions.
3. **Dynamically Register** discovered operations as “tools” using
   `fastmcp.add_tool()`.
4. **Support** the “context injection” mechanism of `fastmcp`: if a decorated
   method’s signature requests a `Context`, pass it in.
5. **Convert** operation return values into valid
   `mcp.types.TextContent | ImageContent | EmbeddedResource` using the same
   logic as `fastmcp.server._convert_to_content`.
6. **Optional**: Integrate a “lifespan” function from config to do asynchronous
   setup/teardown, hooking into `FastMCP`’s lifespan context.

---

## 3. Requirements & Features

### 3.1 Functional Requirements

1. **(FR1) Composition of `FastMCP`**
   - `AutoMCPServer.__init__` shall instantiate `self.fastmcp = FastMCP(...)`,
     passing the server name, instructions, optional dependencies, and an
     optional lifespan function.

2. **(FR2) Config Loading**
   - Unchanged from existing `automcp` approach: read YAML/JSON into
     `ServiceConfig | GroupConfig`.

3. **(FR3) Group Instantiation & Reflection**
   - For each group path (`my_module:MyGroup`) in the config, dynamically import
     the group class, instantiate it, and store it in `self.groups[group_name]`.
   - Reflect each group’s methods to discover any with `@operation` metadata.

4. **(FR4) Operation Decorator**
   - The `@operation` decorator must store the following info: `op_name`,
     optional Pydantic `schema`, possible policy, docstring, and a flag if the
     method expects a `Context`.

5. **(FR5) Register Tools**
   - For each discovered operation, create a wrapper function that calls the
     user’s method with optional context injection and argument validation.
   - Register it with
     `fastmcp.add_tool(name=f"{group_name}.{op_name}", inputSchema=..., description=...)`.

6. **(FR6) Timeout Logic**
   - If an operation times out (configurable `self.timeout`), wrap it in
     `asyncio.wait_for`. If it expires, return an error-like result.

7. **(FR7) Return Value Conversion**
   - The wrapper function must convert method returns from `str`, `int`,
     `Image`, `dict`, `list`, or custom objects into a final
     `list[TextContent | ImageContent | EmbeddedResource]`.

8. **(FR8) Logging & Progress**
   - By injecting `Context` into an operation, the developer can call
     `ctx.info(...)`, `ctx.report_progress(...)` and so on. Ensure no extra code
     is needed in `automcp` beyond the reflection logic.

9. **(FR9) Lifespan Management** (Optional)
   - If the config specifies a `lifespan` (e.g., a path to a function or a built
     function object), pass it to `fastmcp`. This yields a context that can be
     accessed via `ctx.request_context.lifespan_context`.

10. **(FR10) Additional Capabilities** (Future)

- Optionally define “resources” or “prompts” in config, calling
  `fastmcp.add_resource` or `fastmcp.add_prompt`. This is out of scope for the
  _initial_ migration but keep the design open to it.

### 3.2 Non-Functional Requirements

- **Maintainability**: Minimize code duplication by leaning on `fastmcp`’s
  built-in request/response logic.
- **Performance**: Rely on `anyio` concurrency from `fastmcp`; ensure no major
  overhead in reflection or timeouts.
- **Backward Compatibility**: The same config files and group classes that
  worked with the old approach should still function, though any new “context
  injection” usage is optional.
- **Testability**: Provide new tests verifying concurrency, logging, progress,
  image returns, etc.

---

## 4. Implementation Outline

Below is a step-by-step outline for your developers or orchestrating LLMs:

1. **Refactor `AutoMCPServer.__init__`**
   - Remove direct references to `Server`.
   - Initialize
     `FastMCP(name=config.name, instructions=..., dependencies=..., lifespan=...)`.
   - Store it in `self.fastmcp`.
   - Keep reading config into `self.groups`, just as before.

2. **Reflect & Register Tools**
   - After group instantiation, loop over `group.registry.items()`. For each
     `(op_name, operation_func)`:
     1. **Extract** docstring → use as the “description” argument to `add_tool`.
     2. **Build** an `async def wrapper(ctx: Context, **kwargs): ...` that:
        - Validates `kwargs` if a schema is present.
        - Checks if `Context` is required, inject `ctx` appropriately.
        - Awaits (or calls) `operation_func`.
        - Converts the return to `[TextContent|ImageContent|EmbeddedResource]`.
     3. **Register** the wrapper:
        `self.fastmcp.add_tool(tool_func=wrapper, name=f"{group_config.name}.{op_name}", ...)`.
   - (Optional) Wrap the entire invocation in
     `asyncio.wait_for(..., timeout=self.timeout)`.

3. **Start the Server**
   - In your CLI’s `run_server` or `app.command("run")`, call
     `await self.fastmcp.run("stdio")` (or `run_sse_async()`, etc.).

4. **(Optional) Lifespan**
   - If the config has something like `"lifespan": "my_module:my_lifespan"`,
     import that function and pass it to `FastMCP`.
   - Inside a user’s operation, they can do
     `ctx.request_context.lifespan_context` to access resources from that
     function.

5. **Testing**
   - Use `mcp dev your_script.py` or a custom test client to call `tools/list`,
     `tools/call`, etc. Confirm logs show up, progress notifications fire,
     concurrency is stable, etc.

---

## 5. Migration & QA

1. **Migration**
   - If your existing code used `Server`, remove or comment out all manual
     JSON-RPC handler registration.
   - Replace it with the new dynamic approach.
   - The rest of your `ServiceGroup` logic likely remains the same (just more
     capable now).

2. **QA**
   - Write tests that specifically check:
     - Tools returning various data types (strings, dicts, lists, images).
     - Tools that request `Context` for logging or progress calls.
     - Tools that run beyond the specified timeout → confirm an error is
       returned.
   - Possibly test SSE or WebSocket transport if you desire non-stdio usage.

3. **Future**
   - Once stable, you can add a user-friendly decorator for resources
     (`@resource_provider`) or prompts (`@prompt_provider`) if you want a
     symmetrical approach to `@operation`.

---

# Part 2: Using MCP for LLM Workflows

Below is a general “developer’s guide” your LLM team can follow when
implementing features on top of `automcp` with the new `fastmcp` core.

## 1. Creating a Basic MCP Server

> **Example** (Single-File)

```python
from mcp.server.fastmcp import FastMCP, Context

server = FastMCP(name="ExampleServer", instructions="A simple LLM server")

@server.tool(name="math.add")
def add(x: float, y: float) -> str:
    return str(x + y)

@server.tool(name="math.slow_add")
async def slow_add(x: float, y: float, ctx: Context) -> str:
    await ctx.info("Starting slow add")
    result = x + y
    await ctx.info(f"Finished, result={result}")
    return str(result)

if __name__ == "__main__":
    server.run("stdio")
```

Clients can discover these tools with `tools/list` and call them with
`tools/call`, passing e.g. `{"x": 3, "y": 5}`.

---

## 2. Handling More Complex Returns

### 2.1 Text & Image

- A tool that returns a **string** is automatically converted to
  `TextContent(type="text", text="...")`.
- If you return an instance of `mcp.server.fastmcp.Image`, you can embed that as
  `ImageContent`. For example:

```python
from mcp.server.fastmcp import Image

@server.tool()
def get_image() -> Image:
    # Read a local PNG or generate an in-memory byte array
    return Image(path="./images/sample.png")
```

The client sees an array with a single
`ImageContent { data=base64..., mimeType=... }`.

### 2.2 Lists & Embedded Resources

- If your tool returns a `list`, e.g. `["some text", Image(...)]`, each element
  is individually converted.
- For advanced usage, you can directly return an `EmbeddedResource(...)`, or you
  can read from a resource by URI.

---

## 3. Using `Context`: Logging, Progress, Resource Access

```python
@server.tool(name="long.job")
async def long_job(steps: int, ctx: Context) -> str:
    await ctx.info("long_job started")
    await ctx.report_progress(0, total=steps)

    for i in range(steps):
        # do work
        await ctx.report_progress(i + 1)
    return "Done"
```

- The client sees `notifications/progress` with the updated progress count and
  `notifications/message` for logs.

**Resource Reading**:

```python
@server.tool(name="resource.check")
async def resource_check(uri: str, ctx: Context) -> str:
    contents_list = await ctx.read_resource(uri)
    # contents_list is an iterable of text or binary data
    # For example, you might parse the text
    ...
    return "Resource read!"
```

---

## 4. Examples of Expanding with “Resources” & “Prompts”

1. **Static Resource** via `FileResource` or `FunctionResource`
   ```python
   from mcp.server.fastmcp.resources import FileResource

   server.add_resource(FileResource(
       uri="file://hello.txt",
       path="/path/to/hello.txt",
       name="GreetingFile"
   ))
   ```

2. **Prompt**
   ```python
   from mcp.server.fastmcp.prompts import Prompt

   async def greet_prompt_logic(name: str) -> list:
       return [
          {"role": "user", "content": {"type": "text", "text": f"Hello, {name}!"}}
       ]

   server.add_prompt(Prompt(
       name="greet-prompt",
       fn=greet_prompt_logic,
       description="Greets the user by name"
   ))
   ```

The client can do `prompts/get {"name":"Alice"}` → returns a user message,
“Hello, Alice!”.

---

## 5. Transport & Concurrency

1. **Transport**:
   - `server.run("stdio")` for a CLI-based approach.
   - `server.run("sse")` for an SSE-based approach using built-in SSE endpoints.
   - `server.run_sse_async()` or `server.sse_app()` if you want a Starlette/ASGI
     app.
2. **Concurrency**:
   - `fastmcp` uses `anyio`. Each tool call runs in a separate task. Your
     operations can be `async`.
   - If you have shared state, consider using concurrency primitives or
     `.run_sync_in_worker_thread()` for CPU-bound tasks.

---

## 6. Testing & QA

1. **Recommended Tools**
   - **`mcp dev server.py`**: Interactive dev environment that lists tools,
     resources, prompts.
   - **`mcp.client.session.ClientSession`**: For writing your own integration
     tests in code.
2. **Check**
   - Tools that return multiple content types (strings, images, etc.).
   - Tools with timeouts.
   - Tools with `ctx.progress(...)`.
   - Resource reading or prompts if you’re using them.

---

## 7. Next Steps for a Team of LLMs

1. **Implement “Modernizing `automcp`**:
   - Follow the Implementation Outline from Part 1 (Refactor, reflect,
     register).
2. **Add More Decorators** (If needed): e.g., `@resource_provider`,
   `@prompt_provider`.
3. **Extend the CLI**: Possibly add an `automcp install` or `automcp dev`
   command that wraps the standard MCP CLI calls.
4. **Perform Thorough Testing**: Local tests + `mcp dev` + SSE/WebSocket tests
   if relevant.

---

# Conclusion

With **this unified specification and usage guide**, your LLM-based or human
developers should have all the detail needed to:

1. **Overhaul `automcp`** to rely on `fastmcp` for advanced MCP features.
2. **Retain** the config-based, group-based, `@operation` approach while reaping
   the benefits of `Context`, concurrency, logging, progress, resources,
   prompts, etc.
3. **Confidently** develop and test any LLM workflows on top of MCP’s
   standardized protocol, ensuring both robust server logic and a smooth client
   experience.
