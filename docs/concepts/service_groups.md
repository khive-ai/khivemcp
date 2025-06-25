# Service Groups

A **Service Group** in khivemcp is a Python class that collects related MCP
operations. Each group is instantiated once per config entry, which allows:

- Shared state between operations
- Configuration injection via the group's constructor
- Modular grouping of functionalities

---

## Creating a ServiceGroup

```python
from khivemcp import ServiceGroup, operation

class EchoGroup(ServiceGroup):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.prefix = self.group_config.get("prefix", "")

    @operation(name="echo")
    async def echo_message(self, *, request=None):
        text = request.get("text") if request else "Hello"
        return {"echoed": f"{self.prefix}{text}"}
```

- In `__init__`, always call `super().__init__(config=config)` so that
  `self.group_config` is set.
- Each `@operation` method must be `async`.

---

## Configuration in `__init__`

```python
def __init__(self, config: dict = None):
    super().__init__(config)
    self.max_items = self.group_config.get("max_items", 100)
```

When the user defines:

```yaml
name: "my-group"
class_path: "my_package.my_group:MyGroupClass"
config:
  max_items: 50
```

This `config` dict is passed into your constructor automatically.

---

## Dynamic Loading

When you run:

```bash
khivemcp run group_config.yaml
```

khivemcp will:

1. Parse the YAML/JSON.
2. Import `my_package.my_group:MyGroupClass`.
3. Instantiate `MyGroupClass(config=...)`.
4. Find methods decorated with `@operation`.
5. Register them as MCP tools.

No more manual hooking or boilerplate needed.

---

## Multiple Groups in One Service

Use a `ServiceConfig` with a `groups:` mapping to load multiple groups in one
server. For example:

```yaml
name: "combined-service"
groups:
  echo:
    name: "echo"
    class_path: "echo_group:EchoGroup"
    config:
      prefix: "[ECHO] "
  data_processor:
    name: "processor"
    class_path: "data_processor:DataProcessorGroup"
    config:
      default_format: "json"
```

Both `echo.echo_message` and `processor.process_data` will be registered in one
MCP server instance.
