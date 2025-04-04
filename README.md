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
import mcp.types as types
from automcp.types import ExecutionResponse

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

## Using MCP Clients with AutoMCP

AutoMCP servers implement the Model Context Protocol, allowing any MCP client to
connect and interact with your services.

### Connecting to an AutoMCP Server

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    # Connect to an AutoMCP server running on stdio
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "automcp.run", "--config", "service.yaml"]
    )
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            
            # List available tools
            tools = await client.list_tools()
            for tool in tools:
                print(f"Tool: {tool.name} - {tool.description}")
            
            # Call a tool
            response = await client.call_tool(
                "math-ops.add", 
                {"x": 5, "y": 3}
            )
            print(f"Result: {response.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Memory Streams for Testing

For testing purposes, you can use memory streams to connect to an AutoMCP
server:

```python
import asyncio
import anyio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams
from automcp.server import AutoMCPServer
from automcp.types import ServiceConfig

async def test_with_memory_streams():
    # Load your configuration
    config = ServiceConfig(...)
    
    # Create server and client streams
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        client_read, client_write = client_streams
        server_read, server_write = server_streams
        
        # Create the server
        server = AutoMCPServer("test-server", config)
        
        # Start server in background
        async with anyio.create_task_group() as tg:
            tg.start_soon(lambda: server.run_with_streams(server_read, server_write))
            
            # Create and initialize client
            client = ClientSession(read_stream=client_read, write_stream=client_write)
            async with client:
                await client.initialize()
                
                # Use the client
                tools = await client.list_tools()
                print(f"Found {len(tools)} tools")
                
                # Call a tool
                response = await client.call_tool("group-name.operation", {"param": "value"})
                print(f"Response: {response.content[0].text}")
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

## MCP Protocol Interaction

AutoMCP servers support standard MCP protocol operations:

### List Tools

Lists all available tools (operations) across all service groups:

```python
tools = await client.list_tools()
```

### Call Tool

Execute an operation with parameters:

```python
response = await client.call_tool("group-name.operation-name", {"param1": "value1"})
# Access the response content
result_text = response.content[0].text
```

### Handling Timeouts

AutoMCP supports operation timeouts:

```python
# Server with custom timeout
server = AutoMCPServer("my-server", config, timeout=5.0)  # 5 second timeout

# Client with custom timeout
client = ClientSession(
    read_stream=read_stream,
    write_stream=write_stream,
    read_timeout_seconds=10.0  # 10 second timeout
)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Running Verification

AutoMCP includes a comprehensive verification script that tests the MCP protocol
integration through actual client-server interactions:

```bash
# Run all verification tests
python -m verification.verify_automcp --verbose

# Run specific test types
python -m verification.verify_automcp --test-type single    # Test single-group configurations
python -m verification.verify_automcp --test-type multi     # Test multi-group configurations
python -m verification.verify_automcp --test-type timeout   # Test timeout functionality
python -m verification.verify_automcp --test-type concurrent # Test concurrent requests
```

The verification script performs the following tests:

1. **Environment Verification**: Checks Python version and required packages
2. **Single-Group Tests**: Tests operations in individual service groups
3. **Timeout Functionality**: Verifies that operations respect timeout settings
4. **Multi-Group Configuration**: Tests loading and using multiple service
   groups
5. **Concurrent Requests**: Tests handling of concurrent operation calls

Each test starts an actual MCP server with the appropriate configuration and
connects to it using the MCP client, ensuring that the entire protocol stack
works correctly.

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
