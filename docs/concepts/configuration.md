# Configuration

khivemcp reads YAML/JSON configuration to determine how to load and run your MCP
service. This can be a **single group** config or a **multi-group** service
config.

---

## `GroupConfig`

**Single-group** definition:

```yaml
name: "my-group"
class_path: "my_package.my_group:MyGroupClass"
description: "An example single group"
config:
  message_prefix: "[Echo] "
env_vars:
  MY_SECRET: "123"
```

Where:

- `name`: The MCP prefix for operations in this group (e.g. `my-group.echo`).
- `class_path`: `module_path:ClassName` from which to load the `ServiceGroup`
  subclass.
- `config`: Arbitrary dict, passed into your group's constructor.

---

## `ServiceConfig`

**Multi-group** service definition:

```yaml
name: "multi-service"
description: "Demo service"
groups:
  group1:
    name: "my-group"
    class_path: "my_package.my_group:MyGroupClass"
    config:
      setting1: 123
  group2:
    name: "other-group"
    class_path: "my_package.other:OtherGroupClass"
    config:
      debug: true
```

- Each entry in `groups` is a `GroupConfig` object.
- The `name` field in each group's config is used as the prefix for that group's
  operations.

---

## JSON vs. YAML

khivemcp can load either JSON (`.json`) or YAML (`.yaml/.yml`). The library
automatically detects the file type based on the extension.

For example, a single-group JSON config:

```json
{
  "name": "echo",
  "class_path": "echo_group:EchoGroup",
  "config": {
    "message_prefix": "Hi!"
  }
}
```

---

## Loading Configuration

When you run:

```bash
khivemcp run path/to/config.yaml
```

khivemcp:

1. Reads and parses the file (JSON or YAML).
2. Distinguishes `ServiceConfig` vs. `GroupConfig`.
3. Validates fields via Pydantic.
4. Dynamically loads modules/classes from `class_path`.
5. Instantiates the service group(s) with the specified `config`.

That's it! The server then starts with all the operations registered.
