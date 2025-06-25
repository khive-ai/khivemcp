# Running a khivemcp Server

Once you have your config and your `ServiceGroup` classes ready, you can run
your khivemcp server using:

```bash
khivemcp run path/to/config.yaml
```

---

## How It Works

1. **Load Config**:
   - Reads the YAML or JSON file.
   - Differentiates between `ServiceConfig` (multi-group) and `GroupConfig`
     (single-group).
2. **Dynamic Import**:
   - Imports the module/class given by `class_path`.
3. **Instantiate Group(s)**:
   - Calls the group's constructor, passing `config=...` dict if supported.
4. **Register Operations**:
   - Finds methods decorated with `@khivemcp.operation`.
   - Registers each as an MCP tool named `groupName.operationName`.
5. **Start FastMCP**:
   - By default, runs an MCP server over stdio in an event loop.

---

## Example

```bash
khivemcp run service_config.yaml
```

If `service_config.yaml` has two groups (`echo` and `processor`), you get a
server with both sets of operations:

- `echo.echo_message`
- `processor.process_data`
- etc.

---

## Logging & Error Messages

- All server logs and error messages go to `stderr`.
- If any group fails to import or instantiate, the server logs an error but
  continues loading other groups.
- Duplicate operation names (e.g., `echo.echo_message` from two groups) cause
  errors and skip registration for the duplicate.

---

## Stopping the Server

- **Ctrl+C** in the console sends a KeyboardInterrupt, which stops the server.
- For production, consider running in a supervisor that restarts on crash.

---

## Advanced Transport Options

The default is `stdio` transport for MCP messages. `fastmcp` supports other
transports (like SSE), but khivemcp's CLI currently focuses on stdio. If you
need SSE or custom protocols, adapt or wrap `fastmcp` accordingly in your own
runner script.
