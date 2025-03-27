---
type: resource
title: "AutoMCP Operation System"
created: 2024-12-22 18:46 EST
updated: 2024-12-22 18:46 EST
status: active
tags: [resource, architecture, mcp, operations]
aliases: [automcp-operations]
related: ["[[Project_AutoMCP]]", "[[AutoMCP_CLI_Architecture]]"]
sources:
  - "GitHub: https://github.com/ohdearquant/automcp/blob/main/automcp/operation.py"
  - "GitHub: https://github.com/ohdearquant/automcp/blob/main/automcp/group.py"
confidence: certain
---

# AutoMCP Operation System

## Core Components

### Operation Decorator

```python
def operation(
    schema: type[BaseModel] | None = None,
    name: str | None = None,
    policy: str | None = None,
):
    """Decorator for service operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if schema:
                validated_input = schema(**kwargs)
                return await func(self, validated_input)
            return await func(self, *args, **kwargs)

        wrapper.is_operation = True
        wrapper.op_name = name or func.__name__
        wrapper.schema = schema
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        return wrapper
    return decorator
```

Key features:
1. **Schema Validation**: Optional Pydantic model for input validation
2. **Naming**: Custom operation names
3. **Policy Support**: Operation-specific policies
4. **Documentation**: Preserves function docstrings
5. **Async Support**: All operations are async by default

## Service Group System

### Base Group Implementation

```python
class ServiceGroup:
    """Service group containing operations."""

    registry: ClassVar[dict[str, Any]] = {}

    @property
    def _is_empty(self) -> bool:
        """Check if group has any registered operations."""
        return not bool(self.registry)

    async def _execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute an operation."""
        operation = self.registry.get(request.operation)
        if not operation:
            return ExecutionResponse(
                content=types.TextContent(
                    type="text",
                    text=f"Unknown operation: {request.operation}"
                ),
                error=f"Unknown operation: {request.operation}",
            )

        try:
            return await operation(self, **(request.arguments or {}))
        except Exception as e:
            return ExecutionResponse(
                content=types.TextContent(type="text", text=str(e)),
                error=str(e)
            )
```

## Usage Patterns

### 1. Basic Operation
```python
@operation()
async def simple_operation(self) -> ExecutionResponse:
    """A simple operation without input schema."""
    return ExecutionResponse(
        content=types.TextContent(
            type="text",
            text="Operation completed"
        )
    )
```

### 2. Validated Operation
```python
class MathInput(BaseModel):
    x: float
    y: float

@operation(schema=MathInput)
async def add_numbers(self, input: MathInput) -> ExecutionResponse:
    """Add two numbers with validated input."""
    result = input.x + input.y
    return ExecutionResponse(
        content=types.TextContent(
            type="text",
            text=str(result)
        )
    )
```

### 3. Named Operation
```python
@operation(name="custom_name")
async def internal_name(self) -> ExecutionResponse:
    """Operation with custom external name."""
    return ExecutionResponse(
        content=types.TextContent(
            type="text",
            text="Custom operation"
        )
    )
```

## Execution Flow

1. **Request Reception**
```python
request = ExecutionRequest(
    operation="operation_name",
    arguments={"x": 1, "y": 2}
)
```

2. **Operation Lookup**
```python
operation = self.registry.get(request.operation)
if not operation:
    return error_response
```

3. **Input Validation**
```python
if operation.schema:
    validated_input = operation.schema(**request.arguments)
```

4. **Execution**
```python
try:
    result = await operation(self, **request.arguments)
    return result
except Exception as e:
    return error_response
```

## Best Practices

1. **Operation Design**
   - Keep operations focused and single-purpose
   - Use clear, descriptive names
   - Document all parameters and behaviors
   - Handle errors gracefully

2. **Schema Usage**
   - Define clear input schemas
   - Use appropriate field types
   - Add field descriptions
   - Set reasonable constraints

3. **Error Handling**
   - Catch appropriate exceptions
   - Return meaningful error messages
   - Include context in errors
   - Maintain consistent error format

4. **Documentation**
   - Write clear docstrings
   - Document expected inputs
   - Describe error conditions
   - Include usage examples

## Testing Patterns

### 1. Schema Testing
```python
def test_operation_schema():
    # Test valid input
    input_data = {"x": 1, "y": 2}
    schema = MathInput(**input_data)
    assert schema.x == 1
    assert schema.y == 2

    # Test invalid input
    with pytest.raises(ValidationError):
        MathInput(x="invalid", y=2)
```

### 2. Operation Testing
```python
async def test_operation():
    group = TestGroup()
    request = ExecutionRequest(
        operation="add_numbers",
        arguments={"x": 1, "y": 2}
    )
    response = await group._execute(request)
    assert response.content.text == "3"
    assert not response.error
```

### 3. Error Testing
```python
async def test_operation_error():
    group = TestGroup()
    request = ExecutionRequest(
        operation="unknown_op",
        arguments={}
    )
    response = await group._execute(request)
    assert response.error
    assert "Unknown operation" in response.content.text
```

## Integration Example

Here's a complete example showing how to create and use a service group:

```python
from pydantic import BaseModel
from automcp import ServiceGroup, operation
from automcp.types import ExecutionResponse, types

class CalcInput(BaseModel):
    x: float
    y: float
    operation: str

class CalculatorGroup(ServiceGroup):
    @operation(schema=CalcInput)
    async def calculate(self, input: CalcInput) -> ExecutionResponse:
        """Perform basic arithmetic operations."""
        try:
            result = None
            if input.operation == "add":
                result = input.x + input.y
            elif input.operation == "subtract":
                result = input.x - input.y
            elif input.operation == "multiply":
                result = input.x * input.y
            elif input.operation == "divide":
                if input.y == 0:
                    raise ValueError("Division by zero")
                result = input.x / input.y
            else:
                raise ValueError(f"Unknown operation: {input.operation}")

            return ExecutionResponse(
                content=types.TextContent(
                    type="text",
                    text=str(result)
                )
            )
        except Exception as e:
            return ExecutionResponse(
                content=types.TextContent(
                    type="text",
                    text=str(e)
                ),
                error=str(e)
            )
```

## Related Concepts
- [[AsyncIO Patterns]]
- [[Pydantic Schema Design]]
- [[Error Handling Strategies]]
- [[Service Architecture]]
