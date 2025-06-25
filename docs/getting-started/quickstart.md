# Quickstart Guide

Let's build a **simple Echo service** to illustrate the basics of khivemcp:

1. Create a **ServiceGroup** with an operation
2. Create a **config file**
3. Run the server with `khivemcp`

---

## Step 1: Write an Echo Group

```python
# echo_group.py
from khivemcp import ServiceGroup, operation
from pydantic import BaseModel

class EchoRequest(BaseModel):
    message: str
    uppercase: bool = False

class EchoGroup(ServiceGroup):
    def __init__(self, config=None):
        super().__init__(config)
        self.prefix = self.group_config.get("message_prefix", "")

    @operation(schema=EchoRequest)
    async def echo_message(self, *, request: EchoRequest) -> dict:
        """Echo a message back, optionally in uppercase."""
        msg = request.message.upper() if request.uppercase else request.message
        return {"echoed": f"{self.prefix}{msg}"}
```

---

## Step 2: Create a Config File

For a single group, you can use JSON or YAML. Example YAML:

```yaml
name: "echo-service"
class_path: "echo_group:EchoGroup"
description: "A simple echo service"
config:
  message_prefix: "[Echo] "
```

---

## Step 3: Run the Server

```bash
khivemcp run echo_config.yaml
```

- The server starts, listening via stdin/stdout by default.
- The operation is available as `echo-service.echo_message`.

---

## Testing

Use any MCP-compatible client (like a local test script or your own client) to
send a call:

```json
{
  "tool": "echo-service.echo_message",
  "params": {
    "message": "Hello, World!",
    "uppercase": true
  }
}
```

Expect a response like:

```json
{
  "echoed": "[Echo] HELLO, WORLD!"
}
```

---

## Multi-Operation Example

You can add more operations:

```python
@operation()
async def ping(self, *, request=None):
    return {"pong": True}
```

They'll be registered automatically, e.g. `echo-service.ping`.

---

## Next Steps

- See [Configuration](../concepts/configuration.md) for multi-group services.
- See [Operations](../concepts/operations.md) for advanced usage with Pydantic.
- See [Running a khivemcp Server](../guides/running_server.md) for more details.
