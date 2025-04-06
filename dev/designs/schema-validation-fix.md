# Design Document: Schema Validation Fix for AutoMCP Integration Tests

## 1. Problem Analysis

### 1.1 Issue Description

All 5 integration tests are failing with an error where the `inputSchema` field of a Tool object is expected to be a dictionary but is receiving `None` instead. This is happening during the schema conversion process from `@operation(schema=...)` decorator to the MCP server's tool registration.

### 1.2 Current Implementation

The current implementation has several components involved in the schema validation issue:

#### 1.2.1 Schema Definition in Operations

In `automcp/operation.py`, schemas are defined using the `@operation` decorator:

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
                # Extract schema parameters from kwargs
                schema_params = {}
                other_args = []
                other_kwargs = {}

                for key, value in kwargs.items():
                    if key in schema.__annotations__:
                        schema_params[key] = value
                    else:
                        other_kwargs[key] = value

                validated_input = schema(**schema_params)
                return await func(
                    self, validated_input, *args, *other_args, **other_kwargs
                )
            return await func(self, *args, **kwargs)

        wrapper.is_operation = True
        wrapper.op_name = name or func.__name__
        wrapper.schema = schema  # <- Schema class is stored directly
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        return wrapper

    return decorator
```

The key point here is that `wrapper.schema = schema` is storing the Pydantic model class itself, not an instance or its schema representation.

#### 1.2.2 Tool Registration in Server

In `automcp/server.py`, tools are registered with the MCP server via the `handle_list_tools` function:

```python
@self.server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools across groups."""
    tools = []
    for group in self.groups.values():
        for op_name, operation in group.registry.items():
            tools.append(
                types.Tool(
                    name=f"{group.config.name}.{op_name}",
                    description=operation.doc,
                    inputSchema=(
                        operation.schema.model_json_schema()  # <- This is the issue
                        if operation.schema
                        else None
                    ),
                )
            )
    return tools
```

The issue is in the `inputSchema` assignment. The code is trying to call `model_json_schema()` on `operation.schema`, but `operation.schema` is a class, not an instance, and doesn't have this method directly.

#### 1.2.3 Schema Implementation in SchemaGroup

In `verification/groups/schema_group.py`, operations with schemas are defined:

```python
@operation(schema=PersonSchema)
async def greet_person(self, person: PersonSchema) -> str:
    """Greet a person based on their information."""
    # ...

@operation(schema=MessageSchema)
async def repeat_message(self, message: MessageSchema, ctx: Context) -> str:
    """Repeat a message a specified number of times with progress reporting."""
    # ...

@operation(schema=ListProcessingSchema)
async def process_list(self, data: ListProcessingSchema) -> List[str]:
    """Process a list of items according to the parameters."""
    # ...
```

## 2. Root Cause Analysis

The root cause of the issue is that in `server.py`, there's an attempt to call `model_json_schema()` directly on the schema class (`operation.schema`). However, `model_json_schema()` is a class method of Pydantic's `BaseModel`, and it needs to be accessed appropriately.

The line that's causing the issue is:
```python
operation.schema.model_json_schema()
```

Since `operation.schema` is a class (e.g., `PersonSchema`), not an instance, this throws an error because `model_json_schema()` is expected to be called as a class method.

## 3. Proposed Solution

### 3.1 Solution Description

The solution is to correctly access the schema's JSON schema using the appropriate class method for the Pydantic model. 

### 3.2 Implementation Details

Modify the `handle_list_tools` function in `automcp/server.py` as follows:

```python
@self.server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools across groups."""
    tools = []
    for group in self.groups.values():
        for op_name, operation in group.registry.items():
            tools.append(
                types.Tool(
                    name=f"{group.config.name}.{op_name}",
                    description=operation.doc,
                    inputSchema=(
                        operation.schema.model_json_schema  # Access as class method
                        if operation.schema
                        else None
                    ),
                )
            )
    return tools
```

However, this still may not be the correct solution because `model_json_schema` may need to be properly called with parentheses. Let's consider a few alternatives:

#### Alternative 1: Call the Class Method Properly

```python
inputSchema=(
    operation.schema.model_json_schema()  # Call the class method directly
    if operation.schema
    else None
)
```

#### Alternative 2: Create an Instance (not recommended)

```python
inputSchema=(
    operation.schema().model_json_schema()  # Create an instance first
    if operation.schema
    else None
)
```

#### Alternative 3: Use Correct Class Method for Pydantic v2

For Pydantic v2, the correct way to get the JSON schema from a model class is:

```python
inputSchema=(
    operation.schema.model_json_schema()  # For Pydantic v2
    if operation.schema
    else None
)
```

After reviewing the Pydantic documentation, Alternative 3 is the recommended solution. This should correctly access the schema's JSON schema and provide it to the MCP tool.

## 4. Impact Analysis

### 4.1 Existing Functionality

This fix should have no negative impact on existing functionality. It correctly provides the schema information to the MCP tools, enabling proper validation of input parameters.

### 4.2 Compatibility

This solution is compatible with Pydantic v2, which is specified as a requirement in the schema_group.json file:

```json
"packages": ["pydantic>=2.0.0"]
```

## 5. Conclusion

The proposed fix addresses the root cause of the schema validation issue in the integration tests. By correctly accessing the schema's JSON schema using the appropriate class method, the `inputSchema` field of the Tool object will be properly populated, allowing the integration tests to pass.

This fix ensures that the schema information is properly converted into the expected format for MCP tools, maintaining the integrity of the validation process.