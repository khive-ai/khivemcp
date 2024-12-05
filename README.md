# AutoMCP

A lightweight, configurable Model Context Protocol (MCP) server implementation.

## Features

- Simple service group creation
- Configuration-based deployment
- Support for single and multi-group services
- Seamless Claude integration
- Concurrent request handling
- Strong input validation

## Installation

```bash
# Using uv (recommended)
uv pip install automcp

# Using pip
pip install automcp
```

## Quick Start

1. Create a service group:
```python
# my_group.py
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

2. Create configuration:
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

3. Run the server:
```bash
automcp run --config service.yaml
```

## Configuration

### Service Configuration (YAML)
```yaml
name: my-service
description: Service description
groups:
  "module.path:GroupClass":
    name: group-name
    packages:
      - package1
      - package2
    config:
      custom_setting: value
```

### Group Configuration (JSON)
```json
{
  "name": "group-name",
  "description": "Group description",
  "packages": ["package1"],
  "config": {
    "custom_setting": "value"
  }
}
```

## CLI Usage

```bash
# Run service
automcp run --config service.yaml

# Run specific group
automcp run --config service.yaml --group group-name

# Run single group
automcp run --config group.json
```

## Development

### Running Tests
```bash
pytest tests/
```

### Creating New Operations
1. Define input schema using Pydantic
2. Create operation with @operation decorator
3. Add operation documentation
4. Add tests

## Contributing

1. Fork the repository
2. Create your feature branch
3. Write tests
4. Submit pull request

## License

MIT

## Credits

Built with [Model Context Protocol](https://github.com/anthropics/mcp)
