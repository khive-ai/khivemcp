---
type: resource
title: "AutoMCP Server Implementation Guide"
created: 2024-12-22 18:46 EST
updated: 2024-12-22 18:46 EST
status: active
tags: [resource, guide, mcp, server]
aliases: [automcp-server-guide]
related: ["[[Project_AutoMCP]]", "[[AutoMCP_MCP_Implementation]]"]
sources: 
  - "GitHub: https://github.com/ohdearquant/automcp"
  - "GitHub: https://github.com/modelcontextprotocol/python-sdk"
confidence: certain
---

# AutoMCP Server Implementation Guide

## Core Concepts

AutoMCP server implementation follows these key principles:
1. **Group-Based Architecture**: Services are organized into groups
2. **Configuration-Driven**: Uses YAML/JSON for flexible service configuration
3. **Type Safety**: Extensive use of Pydantic models
4. **Async First**: Built on Python's asyncio and anyio primitives

## Quick Start

### 1. Define a Service Group

```python
from automcp import ServiceGroup, operation
from pydantic import BaseModel

class MathInput(BaseModel):
    x: float
    y: float

class MathGroup(ServiceGroup):
    @operation(schema=MathInput)
    async def add(self, input: MathInput) -> ExecutionResponse:
        """Add two numbers."""
        result = input.x + input.y
        return ExecutionResponse(
            content=types.TextContent(
                type="text",
                text=str(result)
            )
        )
```

### 2. Create Configuration

```yaml
# service.yaml
name: math-service
description: Mathematical operations

groups:
  "my_group:MathGroup":
    name: math-ops
    description: Basic math operations
    config:
      precision: 4
```

### 3. Run Server

```python
import asyncio
from automcp import AutoMCPServer

async def main():
    config = load_config("service.yaml")
    server = AutoMCPServer(
        name="math-service",
        config=config
    )
    
    async with server:
        await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration System

### 1. Service Configuration (YAML)

```yaml
name: my-service
description: Service description
groups:
  "module.path:GroupClass":
    name: group-name
    description: Group description
    packages:
      - package1
      - package2
    config:
      setting1: value1
      setting2: value2
    env_vars:
      ENV_VAR1: value1
```

### 2. Group Configuration (JSON)

```json
{
  "name": "group-name",
  "description": "Group description",
  "packages": ["package1"],
  "config": {
    "setting1": "value1",
    "setting2": "value2"
  },
  "env_vars": {
    "ENV_VAR1": "value1"
  }
}
```

## Group Implementations

### 1. Basic Group

```python
class BasicGroup(ServiceGroup):
    @operation()
    async def hello(self) -> ExecutionResponse:
        """Simple operation without input."""
        return ExecutionResponse(
            content=types.TextContent(
                type="text",
                text="Hello, world!"
            )
        )
```

### 2. Validated Group

```python
class UserInput(BaseModel):
    name: str
    age: int = Field(gt=0)

class ValidatedGroup(ServiceGroup):
    @operation(schema=UserInput)
    async def greet(self, input: UserInput) -> ExecutionResponse:
        """Operation with input validation."""
        return ExecutionResponse(
            content=types.TextContent(
                type="text",
                text=f"Hello {input.name}, you are {input.age} years old!"
            )
        )
```

### 3. Resource Group

```python
class ResourceGroup(ServiceGroup):
    @operation(schema=ReadInput)
    async def read_file(self, input: ReadInput) -> ExecutionResponse:
        """Read and return file contents."""
        try:
            content = await read_file(input.path)
            return ExecutionResponse(
                content=types.TextContent(
                    type="text",
                    text=content
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

## Error Handling

### 1. Operation Errors

```python
class DivideInput(BaseModel):
    x: float
    y: float

class MathGroup(ServiceGroup):
    @operation(schema=DivideInput)
    async def divide(self, input: DivideInput) -> ExecutionResponse:
        """Division with error handling."""
        try:
            if input.y == 0:
                raise ValueError("Division by zero")
            
            result = input.x / input.y
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

### 2. Group Errors

```python
class DatabaseGroup(ServiceGroup):
    def __init__(self):
        self.connection = None
    
    async def _ensure_connection(self):
        if not self.connection:
            raise RuntimeError("No database connection")

    @operation(schema=QueryInput)
    async def query(self, input: QueryInput) -> ExecutionResponse:
        try:
            await self._ensure_connection()
            # Query logic
        except Exception as e:
            return ExecutionResponse(
                content=types.TextContent(
                    type="text",
                    text=str(e)
                ),
                error=str(e)
            )
```

## Advanced Features

### 1. Progress Tracking

```python
class LongRunningGroup(ServiceGroup):
    @operation(schema=ProcessInput)
    async def process(self, input: ProcessInput) -> ExecutionResponse:
        total_steps = 100
        
        for i in range(total_steps):
            # Processing step
            await asyncio.sleep(0.1)
            
            # Send progress
            await self.server.send_progress(
                token="process-1",
                progress=i,
                total=total_steps
            )
        
        return ExecutionResponse(
            content=types.TextContent(
                type="text",
                text="Processing complete"
            )
        )
```

### 2. Resource Management

```python
class ResourceManager:
    async def __aenter__(self):
        self.resource = await acquire_resource()
        return self

    async def __aexit__(self, exc_type, exc_val, tb):
        await release_resource(self.resource)

class ManagedGroup(ServiceGroup):
    @operation()
    async def use_resource(self) -> ExecutionResponse:
        async with ResourceManager() as rm:
            result = await rm.process()
            return ExecutionResponse(
                content=types.TextContent(
                    type="text",
                    text=str(result)
                )
            )
```

## Testing

### 1. Group Testing

```python
async def test_math_group():
    group = MathGroup()
    
    # Test successful operation
    response = await group.add(
        MathInput(x=2, y=3)
    )
    assert response.content.text == "5"
    assert not response.error
    
    # Test validation
    with pytest.raises(ValidationError):
        await group.add(
            MathInput(x="invalid", y=3)
        )
```

### 2. Server Testing

```python
async def test_server():
    config = ServiceConfig(
        name="test-service",
        groups={
            "test.group:TestGroup": GroupConfig(
                name="test-group"
            )
        }
    )
    
    server = AutoMCPServer(
        name="test",
        config=config
    )
    
    async with server:
        # Test server capabilities
        assert server.groups
        assert "test-group" in server.groups
```

## Best Practices

1. **Group Design**
   - Keep groups focused
   - Use clear names
   - Document operations
   - Handle errors properly

2. **Configuration**
   - Use YAML for readability
   - Set reasonable defaults
   - Validate all inputs
   - Document options

3. **Resource Management**
   - Use context managers
   - Clean up resources
   - Handle timeouts
   - Monitor usage

4. **Testing**
   - Test validation
   - Test error cases
   - Mock external services
   - Use async fixtures

## Deployment

### 1. Using systemd

```ini
[Unit]
Description=AutoMCP Math Service
After=network.target

[Service]
ExecStart=/usr/local/bin/automcp run --config /etc/automcp/math-service.yaml
User=automcp
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Using Docker

```dockerfile
FROM python:3.11-slim

# Install automcp
RUN pip install automcp

# Copy configuration
COPY service.yaml /etc/automcp/service.yaml

# Run service
CMD ["automcp", "run", "--config", "/etc/automcp/service.yaml"]
```

## Related Concepts
- [[MCP Protocol Specification]]
- [[AutoMCP Configuration Guide]]
- [[Service Architecture Patterns]]
