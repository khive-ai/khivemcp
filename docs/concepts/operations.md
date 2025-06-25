# Operations

In khivemcp, **operations** are async methods on your `ServiceGroup` subclass
decorated with `@operation`. Each operation is registered as an MCP tool that
can be called by an MCP client.

---

## Defining an Operation

```python
from khivemcp import ServiceGroup, operation
from pydantic import BaseModel

class GreetRequest(BaseModel):
    name: str
    uppercase: bool = False

class GreeterGroup(ServiceGroup):
    @operation(name="hello", description="Says hello to a user", schema=GreetRequest)
    async def say_hello(self, *, request: GreetRequest) -> dict:
        """An MCP operation that returns a greeting."""
        greeting = request.name.upper() if request.uppercase else request.name
        return {"message": f"Hello, {greeting}!"}
```

**Key Points:**

- Must be an `async` method.
- Must take a keyword argument `request`, which will be validated (if `schema=`
  is provided).
- The final MCP tool name is `{group_name}.{local_operation_name}`.

---

## Local vs. Full Operation Names

If your group is configured with:

```yaml
name: "greeter"
class_path: "greeter:GreeterGroup"
```

And the operation is decorated with `name="hello"`, the **full** MCP operation
becomes `greeter.hello`. If `name=` is omitted, it defaults to the Python method
name, e.g. `greeter.say_hello`.

---

## Input Validation with Pydantic

By specifying `schema=...` in the decorator, khivemcp automatically:

- Expects the `request` argument to conform to that schema.
- Converts incoming dicts (or JSON strings) to that Pydantic model.
- Raises validation errors if the data is invalid.

```python
class MyRequest(BaseModel):
    text: str
    count: int = 1

@operation(schema=MyRequest)
async def repeat_text(self, *, request: MyRequest) -> dict:
    repeated = [request.text] * request.count
    return {"repeated": repeated}
```

---

## Return Types

Return **any** JSON-serializable data (dict, list, str, etc.) from an operation:

```python
@operation()
async def version(self, *, request=None):
    return {"version": "1.0.0"}
```

---

## Error Handling

In an operation, you can:

1. Raise Python exceptions, which `FastMCP` can wrap and return as an error
   response.
2. Return custom error structures if you prefer.

```python
@operation()
async def might_fail(self, *, request=None):
    if some_condition():
        raise ValueError("Invalid input!")
    return {"ok": True}
```

---

## Summary

- Use `@operation` to expose an async method.
- Optionally specify a Pydantic schema for validated request input.
- Return any JSON-serializable Python data structure.
- The name of the operation in MCP is `{group_config.name}.{operation_name}`.
