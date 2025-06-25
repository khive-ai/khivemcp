# API Reference

This section provides an overview of the main khivemcp exports and how they
interact with your code.

---

## Core Components

### `ServiceGroup`

```python
from khivemcp import ServiceGroup

class MyServiceGroup(ServiceGroup):
    """A custom service group for MCP operations."""
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialization logic here
```

**Key Points:**

- Subclass `ServiceGroup` to define your own group of MCP operations.
- The optional `config` dict can store custom settings for that group.

---

### `operation` Decorator

The decorator for marking methods as MCP operations:

```python
from khivemcp import operation
from pydantic import BaseModel

class MySchema(BaseModel):
    field: str

@operation(
    name="my_tool",
    description="Does something interesting",
    schema=MySchema
)
async def my_method(self, *, request: MySchema) -> dict:
    """The logic that will be exposed as an MCP operation."""
    return {"result": "value"}
```

**Parameters:**

- `name` (optional): The operation's local name within the group. Defaults to
  the method name.
- `description` (optional): A description for the MCP operation. Defaults to the
  method's docstring if not specified.
- `schema` (optional): A Pydantic model class used to validate the incoming
  request.

---

### `GroupConfig` and `ServiceConfig` (from `khivemcp.types`)

`khivemcp.types.GroupConfig` and `khivemcp.types.ServiceConfig` define how you
specify group(s) and their configs in YAML/JSON:

```python
from khivemcp.types import GroupConfig, ServiceConfig

# Single-group config example
gc = GroupConfig(
    name="my_group",
    class_path="my_module:MyGroupClass",
    config={"setting": 1},
)

# Multi-group config example
sc = ServiceConfig(
    name="my_service",
    groups={
      "group_key": gc,
    },
)
```

---

### CLI Commands

khivemcp provides a CLI via `khivemcp run`. For example:

```bash
khivemcp run my_service_config.yaml
```

- Dynamically loads the configuration (YAML or JSON).
- Instantiates the specified group(s).
- Registers all `@operation`-decorated async methods with a `FastMCP` server.
- Listens over `stdin`/`stdout` by default.

See [Running a khivemcp Server](../guides/running_server.md) for details.
