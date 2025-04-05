---
title: Technical Specifications
created_at: 2024-12-04
updated_at: 2025-04-05
tools: ["ChatGPT O1-pro", "ChatGPT DeepResearch"]
by: Ocean
version: 1.0
description: |
    The technical specification of the AutoMCP project.
---


# AutoMCP Technical Documentation

## Overview

AutoMCP is a Model Context Protocol (MCP) server implementation that enables
easy creation and deployment of MCP-compatible services. It supports both
single-group and multi-group service configurations.

## Architecture

### Core Components

#### ServiceGroup

The basic unit of functionality. Each group provides a set of operations
decorated with `@operation`:

```python
class MyGroup(ServiceGroup):
    @operation(schema=MySchema)
    async def my_operation(self, input: MySchema) -> ExecutionResponse:
        """Operation documentation."""
        pass
```

#### Server

Handles MCP protocol integration and request routing:

- Single entry point for all operations
- Concurrent request execution
- Timeout handling
- Error management

#### Configuration System

Two levels of configuration:

1. Service Configuration (YAML)
   ```yaml
   name: my-service
   groups:
     "module.path:GroupClass":
       name: group-name
       config:
         setting: value
   ```

2. Group Configuration (JSON)
   ```json
   {
     "name": "group-name",
     "config": {
       "setting": "value"
     }
   }
   ```

## Deployment

### Command Line Interface

```bash
# Run service with multiple groups
automcp run --config service.yaml

# Run specific group from service
automcp run --config service.yaml --group group-name

# Run single group
automcp run --config group.json
```

### Integration with Claude

AutoMCP servers integrate seamlessly with Claude's MCP client through stdio
transport.

## Development

### Creating New Groups

1. Create group class inheriting from ServiceGroup
2. Define operations using @operation decorator
3. Specify input schemas using Pydantic models
4. Create configuration file

### Testing

Comprehensive test suite available:

- Group operation testing
- Service configuration testing
- Concurrent execution testing
- Timeout handling testing

## Best Practices

### Configuration

- Use YAML for service configs (multiple groups)
- Use JSON for single group configs
- Keep configurations version controlled
- Document custom configuration options

### Operations

- Clear operation documentation
- Input validation via schemas
- Proper error handling
- Reasonable timeouts

### Deployment

- Use uv for package management
- Monitor operation timeouts
- Consider resource limitations
- Handle errors gracefully

## Security Considerations

- Input validation through schemas
- Operation timeouts
- Resource limits
- Error handling
- Clean environment separation

## Performance

- Concurrent request execution
- Efficient request routing
- Minimal overhead
- Clean resource cleanup
