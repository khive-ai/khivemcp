# Simple Echo Example

This example demonstrates a basic Echo service that reflects back messages with
optional transformations. It shows the essential concepts of creating and
configuring a khivemcp service.

## Basic Implementation

Let's create a minimal Echo service:

```python
# file: echo_group.py
from khivemcp import ServiceGroup, operation
from pydantic import BaseModel, Field

class EchoRequest(BaseModel):
    """Schema for echo requests."""
    message: str = Field(..., description="The message to echo back")
    uppercase: bool = Field(False, description="Whether to convert the message to uppercase")

class EchoGroup(ServiceGroup):
    """A simple echo service group."""
    
    def __init__(self, config: dict = None):
        super().__init__(config=config)
        # Extract configuration values with defaults
        self.prefix = config.get("message_prefix", "") if config else ""
    
    @operation(name="echo", description="Echo a message back", schema=EchoRequest)
    async def echo_message(self, *, request: EchoRequest) -> dict:
        """Echo a message back, optionally in uppercase."""
        message = request.message
        
        if request.uppercase:
            message = message.upper()
            
        # Apply prefix if configured
        message = f"{self.prefix}{message}"
            
        return {
            "echoed_message": message,
            "original_message": request.message,
            "was_uppercased": request.uppercase
        }
```

The example above demonstrates:

1. **Define a Pydantic Model** (`EchoRequest`) for input validation
2. **Create a ServiceGroup** (`EchoGroup`) to organize related operations
3. **Extract configuration** in the constructor to customize behavior
4. **Decorate methods** with `@operation` to expose them as MCP tools

## Configuration

You can use either JSON or YAML to configure your service:

### JSON Configuration (echo_config.json)

```json
{
  "name": "echo",
  "class_path": "echo_group:EchoGroup",
  "description": "A simple echo service that reflects messages back.",
  "config": {
    "message_prefix": "[Echo] "
  }
}
```

### YAML Configuration (echo_config.yaml)

```yaml
name: echo
class_path: echo_group:EchoGroup
description: A simple echo service that reflects messages back.
config:
  message_prefix: "[Echo] "
```

The configuration specifies:

- `name`: The prefix for operations (resulting in `echo.echo`)
- `class_path`: The module and class to load (`module_name:ClassName`)
- `description`: A human-readable description of the service
- `config`: Custom configuration passed to the service constructor

## Running the Service

Run the service using the khivemcp CLI:

```bash
# With JSON config
khivemcp run path/to/echo_config.json

# Or with YAML config
khivemcp run path/to/echo_config.yaml
```

## Using with an MCP Client

To add this service to your MCP client configuration:

```json
{
  "mcpServers": {
    "echo-service": {
      "command": "python",
      "args": [
        "-m",
        "khivemcp.cli",
        "run",
        "/absolute/path/to/echo_config.json"
      ]
    }
  }
}
```

## Advanced Implementation

For more advanced use cases, we can extend our example:

```python
# file: advanced_echo_group.py
from khivemcp import ServiceGroup, operation
from pydantic import BaseModel, Field
import time
import asyncio

class EchoRequest(BaseModel):
    """Schema for echo requests."""
    message: str = Field(..., description="The message to echo back")
    uppercase: bool = Field(False, description="Whether to convert the message to uppercase")

class DelayedEchoRequest(EchoRequest):
    """Schema for delayed echo requests."""
    delay: float = Field(1.0, description="Delay in seconds before responding", ge=0, le=10)

class AdvancedEchoGroup(ServiceGroup):
    """An extended echo service group with additional operations."""
    
    def __init__(self, config: dict = None):
        super().__init__(config=config)
        self.prefix = config.get("message_prefix", "") if config else ""
    
    @operation(name="echo", description="Echo a message back", schema=EchoRequest)
    async def echo_message(self, *, request: EchoRequest) -> dict:
        """Echo a message back, optionally in uppercase."""
        message = request.message
        
        if request.uppercase:
            message = message.upper()
            
        # Apply prefix if configured
        message = f"{self.prefix}{message}"
            
        return {
            "echoed_message": message,
            "original_message": request.message,
            "was_uppercased": request.uppercase
        }
    
    @operation(name="echo_with_timestamp", description="Echo a message with timestamp")
    async def echo_with_timestamp(self, *, request=None) -> dict:
        """Echo a message back with the current timestamp."""
        message = request.get("message", "") if request else ""
        
        return {
            "echoed_message": f"{self.prefix}{message}",
            "timestamp": time.time(),
            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
    
    @operation(name="delayed_echo", description="Echo after delay", schema=DelayedEchoRequest)
    async def delayed_echo(self, *, request: DelayedEchoRequest) -> dict:
        """Echo a message back after a specified delay."""
        await asyncio.sleep(request.delay)
        
        message = request.message
        if request.uppercase:
            message = message.upper()
            
        message = f"{self.prefix}{message}"
            
        return {
            "echoed_message": message,
            "original_message": request.message,
            "delay": request.delay,
            "was_uppercased": request.uppercase
        }
```

This advanced example demonstrates additional features:

- **Inheritance** for request models (`DelayedEchoRequest` extends
  `EchoRequest`)
- **Multiple operations** within a single service group
- **Asynchronous operations** with `asyncio.sleep()`
- **Dictionary-based requests** for flexible inputs when a schema isn't required

## Testing

When using the Echo service, a request like:

```json
{
  "message": "Hello, world!",
  "uppercase": true
}
```

Would return:

```json
{
  "echoed_message": "[Echo] HELLO, WORLD!",
  "original_message": "Hello, world!",
  "was_uppercased": true
}
```
