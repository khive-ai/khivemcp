# AutoMCP Verification ServiceGroups Design

This document outlines the design specifications for a set of ServiceGroup classes intended to verify AutoMCP's configuration-based system. These groups will be used to test both single-group and multi-group configurations.

## Purpose

The purpose of these ServiceGroups is to provide a comprehensive test suite for AutoMCP's core functionalities:
- Basic operation execution
- Schema-based input validation
- Timeout handling

## ServiceGroups Overview

We will implement three distinct ServiceGroups:

1. **ExampleGroup**: A minimal ServiceGroup with basic text operations
2. **SchemaGroup**: A ServiceGroup demonstrating Pydantic schema validation 
3. **TimeoutGroup**: A ServiceGroup with operations that can test timeout functionality

## File Structure

```
verification/
├── __init__.py
├── config/
│   ├── example_group.json      # Config for standalone ExampleGroup
│   ├── schema_group.json       # Config for standalone SchemaGroup
│   ├── timeout_group.json      # Config for standalone TimeoutGroup
│   └── multi_group.yaml        # Config for combined service with all groups
├── groups/
│   ├── __init__.py
│   ├── example_group.py        # ExampleGroup implementation
│   ├── schema_group.py         # SchemaGroup implementation
│   └── timeout_group.py        # TimeoutGroup implementation
└── schemas.py                  # Shared Pydantic schema definitions
```

## Detailed ServiceGroup Specifications

### 1. ExampleGroup

This is a minimal ServiceGroup with basic operations that return text.

```python
from automcp.group import ServiceGroup
from automcp.operation import operation

class ExampleGroup(ServiceGroup):
    """A basic example group with simple operations."""

    @operation()
    async def hello_world(self) -> str:
        """Return a simple hello world message."""
        return "Hello, World!"

    @operation()
    async def echo(self, text: str) -> str:
        """Echo the provided text back to the user."""
        return f"Echo: {text}"

    @operation()
    async def count_to(self, number: int) -> str:
        """Return a string with numbers from 1 to the provided number."""
        return ", ".join(str(i) for i in range(1, number + 1))
```

### 2. SchemaGroup

This group demonstrates the use of Pydantic schemas for input validation.

First, we need to define the schemas:

```python
# verification/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class PersonSchema(BaseModel):
    """Schema representing a person."""
    name: str = Field(..., description="Person's name")
    age: int = Field(..., description="Person's age")
    email: Optional[str] = Field(None, description="Person's email address")

class MessageSchema(BaseModel):
    """Schema for a message with repetition."""
    text: str = Field(..., description="Message text")
    repeat: int = Field(1, description="Number of times to repeat the message", ge=1, le=10)

class ListProcessingSchema(BaseModel):
    """Schema for processing a list of items."""
    items: List[str] = Field(..., description="List of items to process")
    prefix: Optional[str] = Field("Item:", description="Prefix to add to each item")
    uppercase: bool = Field(False, description="Whether to convert items to uppercase")
```

Then, the ServiceGroup implementation:

```python
# verification/groups/schema_group.py
from mcp.server.fastmcp import Context
from typing import List

from automcp.group import ServiceGroup
from automcp.operation import operation
from verification.schemas import PersonSchema, MessageSchema, ListProcessingSchema

class SchemaGroup(ServiceGroup):
    """Group demonstrating the use of Pydantic schemas for input validation."""

    @operation(schema=PersonSchema)
    async def greet_person(self, person: PersonSchema) -> str:
        """Greet a person based on their information."""
        greeting = f"Hello, {person.name}! "
        if person.age:
            greeting += f"You are {person.age} years old. "
        if person.email:
            greeting += f"Your email is {person.email}."
        return greeting

    @operation(schema=MessageSchema)
    async def repeat_message(self, message: MessageSchema, ctx: Context) -> str:
        """Repeat a message a specified number of times with progress reporting."""
        ctx.info(f"Repeating message {message.repeat} times")
        result = []
        for i in range(message.repeat):
            await ctx.report_progress(i+1, message.repeat)
            result.append(message.text)
        return " ".join(result)

    @operation(schema=ListProcessingSchema)
    async def process_list(self, data: ListProcessingSchema) -> List[str]:
        """Process a list of items according to the parameters."""
        result = []
        for item in data.items:
            processed = item
            if data.uppercase:
                processed = processed.upper()
            result.append(f"{data.prefix} {processed}")
        return result
```

### 3. TimeoutGroup

This group contains operations that can take a long time to complete, useful for testing timeout functionality.

```python
# verification/groups/timeout_group.py
import asyncio
import time
from mcp.server.fastmcp import Context

from automcp.group import ServiceGroup
from automcp.operation import operation

class TimeoutGroup(ServiceGroup):
    """Group with operations for testing timeout functionality."""

    @operation()
    async def sleep(self, seconds: float) -> str:
        """Sleep for the specified number of seconds.
        
        This operation simply waits for the specified duration and returns.
        Useful for basic timeout testing.
        """
        await asyncio.sleep(seconds)
        return f"Slept for {seconds} seconds"

    @operation()
    async def slow_counter(self, limit: int, delay: float, ctx: Context) -> str:
        """Count up to a limit with delay between each number and progress reporting.
        
        Args:
            limit: The number to count up to
            delay: Seconds to wait between counts
            ctx: MCP context for progress reporting
            
        Returns:
            A string with the counting results and timing information
        """
        result = []
        start_time = time.time()
        
        for i in range(1, limit + 1):
            await ctx.report_progress(i, limit)
            ctx.info(f"Counter: {i}/{limit}")
            result.append(str(i))
            await asyncio.sleep(delay)
            
        total_time = time.time() - start_time
        return f"Counted to {limit} in {total_time:.2f} seconds: {', '.join(result)}"

    @operation()
    async def cpu_intensive(self, iterations: int, ctx: Context) -> str:
        """Perform a CPU-intensive operation for testing timeout.
        
        This operation does meaningless but CPU-intensive work to test
        how the timeout handling works with CPU-bound operations.
        
        Args:
            iterations: Number of calculation iterations to perform
            ctx: MCP context for progress reporting
            
        Returns:
            A string with timing information and result
        """
        ctx.info(f"Starting CPU-intensive operation with {iterations} iterations")
        start_time = time.time()
        
        result = 0
        for i in range(iterations):
            if i % (iterations // 10) == 0:
                progress = (i / iterations) * 100
                await ctx.report_progress(i, iterations)
                ctx.info(f"Progress: {progress:.1f}%")
            
            # CPU-intensive work
            result += sum(j * j for j in range(10000))
            
        total_time = time.time() - start_time
        return f"Completed {iterations} iterations in {total_time:.2f} seconds with result: {result}"
```

## Configuration Files

### 1. Example Group (JSON)

```json
{
  "name": "example",
  "description": "Basic example group for AutoMCP verification",
  "packages": []
}
```

### 2. Schema Group (JSON)

```json
{
  "name": "schema",
  "description": "Schema validation group for AutoMCP verification",
  "packages": ["pydantic>=2.0.0"]
}
```

### 3. Timeout Group (JSON)

```json
{
  "name": "timeout",
  "description": "Timeout testing group for AutoMCP verification",
  "packages": [],
  "config": {
    "default_delay": 0.5
  }
}
```

### 4. Multi-Group Service (YAML)

```yaml
name: verification-service
description: AutoMCP verification service with multiple groups
packages:
  - pydantic>=2.0.0
groups:
  "verification.groups.example_group:ExampleGroup":
    name: example
    description: Basic example group for AutoMCP verification
  "verification.groups.schema_group:SchemaGroup":
    name: schema
    description: Schema validation group for AutoMCP verification
  "verification.groups.timeout_group:TimeoutGroup":
    name: timeout
    description: Timeout testing group for AutoMCP verification
    config:
      default_delay: 0.5
```

## Usage

These ServiceGroups can be used to verify both single-group and multi-group configurations:

1. **Single Group Testing**:
   ```bash
   automcp run --config verification/config/example_group.json
   automcp run --config verification/config/schema_group.json
   automcp run --config verification/config/timeout_group.json
   ```

2. **Multi-Group Service**:
   ```bash
   automcp run --config verification/config/multi_group.yaml
   ```

3. **Testing with Different Timeouts**:
   ```bash
   automcp run --config verification/config/timeout_group.json --timeout 5.0
   ```

## Conclusion

This design provides a comprehensive set of ServiceGroups for verifying AutoMCP's configuration-based system. The groups cover basic functionality, schema validation, and timeout handling, making them suitable for testing both single-group and multi-group setups.