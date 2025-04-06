# Phase 1: Core FastMCP Integration Design

## 1. Introduction

This document details the architectural changes needed for Phase 1 of the AutoMCP modernization plan: integrating the FastMCP backend to replace the current MCP Server implementation. This phase focuses on refactoring the core `AutoMCPServer` class to use composition with `FastMCP` instead of inheritance from `mcp.server.Server`, while maintaining backward compatibility with existing ServiceGroup implementations.

### Objectives

1. **Architectural Shift**: Replace inheritance with composition by integrating FastMCP
2. **Tool Registration**: Create a system to wrap existing operations as FastMCP tools
3. **Context Injection**: Enable operations to request and use the FastMCP Context object
4. **Backward Compatibility**: Ensure existing ServiceGroup implementations continue to function
5. **Enhanced Return Types**: Support for various return types (text, images, mixed content)

## 2. Core Class Modifications

### 2.1 AutoMCPServer Class

The `AutoMCPServer` class will be refactored to use composition with FastMCP instead of inheritance from `mcp.server.Server`.

#### Current Implementation

```python
class AutoMCPServer:
    def __init__(self, name: str, config: ServiceConfig | GroupConfig, timeout: float = 30.0):
        self.name = name
        self.config = config
        self.timeout = timeout
        self.server = Server(name)  # Uses Server directly
        self.groups: dict[str, ServiceGroup] = {}
        # ...
```

#### New Implementation

```python
from mcp.server.fastmcp import FastMCP, Context

class AutoMCPServer:
    def __init__(self, name: str, config: ServiceConfig | GroupConfig, timeout: float = 30.0):
        self.name = name
        self.config = config
        self.timeout = timeout
        self.groups: dict[str, ServiceGroup] = {}
        
        # Extract dependencies from config
        packages = []
        if isinstance(config, ServiceConfig):
            packages.extend(config.packages)
        else:
            packages.extend(config.packages)
            
        # Initialize lifespan function if provided
        lifespan_func = None
        if hasattr(config, "lifespan") and config.lifespan:
            try:
                module_path, func_name = config.lifespan.split(":")
                module = __import__(module_path, fromlist=[func_name])
                lifespan_func = getattr(module, func_name)
            except Exception as e:
                raise RuntimeError(f"Failed to load lifespan function: {e}")
        
        # Initialize FastMCP instance
        self.fastmcp = FastMCP(
            name=name,
            instructions=getattr(config, "description", None) or f"{name} MCP Server",
            dependencies=packages,
            lifespan=lifespan_func
        )
        
        # Initialize groups based on config type
        if isinstance(config, ServiceConfig):
            self._init_service_groups()
        else:
            self._init_single_group()
            
        # Register all operations as tools
        self._register_tools()
```

### 2.2 Tool Registration System

The `AutoMCPServer` class will include methods to register all ServiceGroup operations as FastMCP tools:

```python
def _register_tools(self) -> None:
    """Register all group operations as FastMCP tools."""
    for group_name, group in self.groups.items():
        for op_name, operation in group.registry.items():
            tool_name = f"{group_name}.{op_name}"
            self._register_tool(group, tool_name, op_name, operation)

def _register_tool(
    self, 
    group: ServiceGroup, 
    tool_name: str, 
    op_name: str, 
    operation: Any
) -> None:
    """Register a single operation as a FastMCP tool."""
    
    # Create wrapper function for the operation
    async def tool_wrapper(ctx: Context, **kwargs):
        """Wrapper function to handle execution of the operation."""
        try:
            # Validate input if schema is provided
            validated_args = kwargs
            if operation.schema:
                validated_args = operation.schema(**kwargs)
                # If schema is a model, convert to dict for regular operations
                # or pass directly for new context-aware operations
            
            # Check if operation expects a Context parameter
            if hasattr(operation, "requires_context") and operation.requires_context:
                # Pass context to the operation
                if isinstance(validated_args, dict):
                    result = await operation(group, ctx=ctx, **validated_args)
                else:
                    result = await operation(group, validated_args, ctx=ctx)
            else:
                # Call without context (backward compatibility)
                if isinstance(validated_args, dict):
                    result = await operation(group, **validated_args)
                else:
                    result = await operation(group, validated_args)
            
            return result
            
        except asyncio.TimeoutError:
            return "Operation timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Add tool to FastMCP
    self.fastmcp.add_tool(
        tool_func=tool_wrapper,
        name=tool_name,
        description=operation.doc,
        inputSchema=(
            operation.schema.model_json_schema()
            if operation.schema
            else None
        ),
    )
```

### 2.3 Updated Server Start/Run Methods

The `start()` method will be simplified to leverage FastMCP's built-in transport handling:

```python
async def start(self) -> None:
    """Start the MCP server using stdio transport."""
    self.fastmcp.run("stdio")
    
async def __aenter__(self):
    """Async context manager entry."""
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Async context manager exit."""
    # Cleanup handled by FastMCP
    pass
```

## 3. Operation Decorator Enhancement

The `@operation` decorator needs enhancement to detect and support Context injection:

### 3.1 Current Implementation

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

### 3.2 Enhanced Implementation

```python
import inspect
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from mcp.server.fastmcp import Context
from pydantic import BaseModel

def operation(
    schema: type[BaseModel] | None = None,
    name: str | None = None,
    policy: str | None = None,
):
    """Decorator for service operations with optional Context injection."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract context if present in kwargs
            ctx = kwargs.pop("ctx", None)
            
            # Validate input if schema is provided
            if schema and len(args) == 0:
                validated_input = schema(**kwargs)
                # Pass context if the function expects it
                if "ctx" in func.__code__.co_varnames:
                    return await func(self, validated_input, ctx=ctx)
                return await func(self, validated_input)
            
            # Pass context if the function expects it
            if "ctx" in func.__code__.co_varnames:
                return await func(self, *args, ctx=ctx, **kwargs)
            return await func(self, *args, **kwargs)

        # Store operation metadata
        wrapper.is_operation = True
        wrapper.op_name = name or func.__name__
        wrapper.schema = schema
        wrapper.policy = policy
        wrapper.doc = func.__doc__
        
        # Detect if the function requires Context
        sig = inspect.signature(func)
        wrapper.requires_context = any(
            param.name == "ctx" and param.annotation == Context
            for param in sig.parameters.values()
        )
        
        return wrapper

    return decorator
```

## 4. Class Diagrams

### 4.1 AutoMCPServer Class

```
┌───────────────────────────────────────────────────┐
│                  AutoMCPServer                     │
├───────────────────────────────────────────────────┤
│ - name: str                                        │
│ - config: ServiceConfig | GroupConfig              │
│ - timeout: float                                   │
│ - fastmcp: FastMCP                                 │
│ - groups: dict[str, ServiceGroup]                  │
├───────────────────────────────────────────────────┤
│ + __init__(name, config, timeout)                  │
│ + start() -> None                                  │
│ + __aenter__() -> Self                             │
│ + __aexit__(exc_type, exc_val, exc_tb) -> None    │
│ - _init_service_groups() -> None                   │
│ - _init_single_group() -> None                     │
│ - _register_tools() -> None                        │
│ - _register_tool(group, tool_name, op_name, op)    │
└───────────────────────────────────────────────────┘
          │
          │ composed of
          ▼
┌─────────────────────┐      ┌─────────────────────┐
│      FastMCP         │      │    ServiceGroup     │
├─────────────────────┤      ├─────────────────────┤
│ + add_tool()         │      │ + registry          │
│ + run()              │      │ + _execute()        │
└─────────────────────┘      └─────────────────────┘
```

### 4.2 Operation Decorator

```
┌───────────────────────────────────────────────────┐
│                @operation decorator                │
├───────────────────────────────────────────────────┤
│ + parameters:                                      │
│   - schema: Optional[type[BaseModel]]              │
│   - name: Optional[str]                            │
│   - policy: Optional[str]                          │
├───────────────────────────────────────────────────┤
│ + decorated function properties:                   │
│   - is_operation: bool                             │
│   - op_name: str                                   │
│   - schema: Optional[type[BaseModel]]              │
│   - policy: Optional[str]                          │
│   - doc: Optional[str]                             │
│   - requires_context: bool                         │
└───────────────────────────────────────────────────┘
```

## 5. Sequence Diagrams

### 5.1 Server Initialization and Tool Registration

```
┌────────────┐  ┌──────────────┐  ┌─────────┐  ┌────────────┐
│Application │  │AutoMCPServer │  │FastMCP  │  │ServiceGroup│
└─────┬──────┘  └──────┬───────┘  └────┬────┘  └─────┬──────┘
      │                 │               │            │
      │ initialize      │               │            │
      │────────────────>│               │            │
      │                 │  create       │            │
      │                 │──────────────>│            │
      │                 │               │            │
      │                 │  load groups  │            │
      │                 │───────────────────────────>│
      │                 │               │            │
      │                 │  register     │            │
      │                 │  operations   │            │
      │                 │──────────────>│            │
      │                 │               │            │
      │                 │  wrap each    │            │
      │                 │  operation    │            │
      │                 │──────────────>│            │
      │                 │               │            │
      │                 │  add_tool()   │            │
      │                 │──────────────>│            │
      │                 │               │            │
```

### 5.2 Tool Execution Flow

```
┌──────┐  ┌──────────────┐  ┌─────────┐  ┌────────────┐  ┌───────────┐
│Client│  │AutoMCPServer │  │FastMCP  │  │ToolWrapper │  │Operation  │
└──┬───┘  └──────┬───────┘  └────┬────┘  └─────┬──────┘  └────┬──────┘
   │             │               │             │              │
   │ call_tool() │               │             │              │
   │────────────────────────────>│             │              │
   │             │               │             │              │
   │             │               │  invoke     │              │
   │             │               │  wrapper    │              │
   │             │               │────────────>│              │
   │             │               │             │              │
   │             │               │             │  validate    │
   │             │               │             │  input       │
   │             │               │             │─────────────>│
   │             │               │             │              │
   │             │               │             │  check for   │
   │             │               │             │  Context     │
   │             │               │             │─────────────>│
   │             │               │             │              │
   │             │               │             │  execute     │
   │             │               │             │  operation   │
   │             │               │             │─────────────>│
   │             │               │             │              │
   │             │               │             │  return      │
   │             │               │             │  result      │
   │             │               │             │<─────────────│
   │             │               │             │              │
   │             │               │  return     │              │
   │             │               │  result     │              │
   │             │               │<────────────│              │
   │             │               │             │              │
   │ return      │               │             │              │
   │ response    │               │             │              │
   │<────────────────────────────│             │              │
   │             │               │             │              │
```

### 5.3 Context Injection Flow

```
┌──────────┐  ┌─────────┐  ┌────────────┐  ┌───────────────┐
│Operation │  │Context  │  │FastMCP     │  │Client/Protocol│
└────┬─────┘  └────┬────┘  └──────┬─────┘  └───────┬───────┘
     │             │              │                │
     │ ctx.info()  │              │                │
     │────────────>│              │                │
     │             │  send        │                │
     │             │  notification│                │
     │             │─────────────>│                │
     │             │              │  forward       │
     │             │              │  notification  │
     │             │              │───────────────>│
     │             │              │                │
     │ ctx.report_ │              │                │
     │ progress()  │              │                │
     │────────────>│              │                │
     │             │  send        │                │
     │             │  progress    │                │
     │             │─────────────>│                │
     │             │              │  forward       │
     │             │              │  progress      │
     │             │              │───────────────>│
     │             │              │                │
     │ ctx.read_   │              │                │
     │ resource()  │              │                │
     │────────────>│              │                │
     │             │  request     │                │
     │             │  resource    │                │
     │             │─────────────>│                │
     │             │              │  get          │
     │             │              │  resource     │
     │             │              │───────────────>│
     │             │              │                │
     │             │              │  return       │
     │             │              │  resource     │
     │             │              │<───────────────│
     │             │  return      │                │
     │             │  resource    │                │
     │             │<─────────────│                │
     │ return      │              │                │
     │ resource    │              │                │
     │<────────────│              │                │
     │             │              │                │
```

## 6. Backward Compatibility Considerations

### 6.1 Operation Signatures

The design maintains backward compatibility for existing operations in several ways:

1. **Existing Operations Continue to Work**: The wrapper system automatically detects whether an operation requires a Context object. If not, the operation is called without it, ensuring existing code works as before.

2. **Detection Mechanism**: The `@operation` decorator analyzes the function signature using `inspect.signature()` to detect if a parameter named `ctx` with the type annotation `Context` exists. This only affects operations that explicitly request it.

3. **Schema Handling**: The existing schema validation continues to work, whether or not the operation uses Context.

### 6.2 ServiceGroup Interface

The `ServiceGroup` class interface remains unchanged, ensuring existing group implementations continue to work:

```python
class ServiceGroup:
    """Service group containing operations."""

    registry: ClassVar[dict[str, Any]] = {}

    @property
    def _is_empty(self) -> bool:
        """Check if group has any registered operations."""
        return not bool(self.registry)
```

### 6.3 Return Type Handling

The system automatically converts various return types to appropriate MCP content types:

1. **Simple Types**: `str`, `int`, `float`, `bool` are automatically converted to `TextContent`
2. **Image Type**: `mcp.server.fastmcp.Image` objects are converted to `ImageContent`
3. **Pydantic Models**: Automatically JSON-serialized and returned as `TextContent`
4. **Mixed Content**: Lists/tuples of different types are correctly converted to a list of appropriate content types

### 6.4 Configuration Files

Existing configuration files continue to work without modification. New fields like `lifespan` are optional and only used if specified:

```yaml
# Existing configuration still works:
name: "ExampleService"
groups:
  "my_package.groups.math:MathGroup":
    name: "math"
    description: "Mathematical operations"

# New optional fields:
lifespan: "my_package.lifespan:app_lifespan"
```

## 7. Required Imports and Dependencies

### 7.1 External Dependencies

- `mcp.server.fastmcp`: Provides `FastMCP`, `Context`, and `Image` classes
- `mcp.types`: For MCP protocol type definitions
- Standard library: `asyncio`, `inspect`, `typing`, `contextlib`

### 7.2 Internal Dependencies

- `automcp.types`: For configuration classes (`ServiceConfig`, `GroupConfig`, etc.)
- `automcp.group`: For `ServiceGroup` base class

### 7.3 Import Statements

```python
# server.py
import asyncio
import inspect
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP, Image
import mcp.types as types

from .group import ServiceGroup
from .types import (
    ExecutionRequest,
    GroupConfig,
    ServiceConfig,
    ServiceResponse,
)

# operation.py
import inspect
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from mcp.server.fastmcp import Context
from pydantic import BaseModel
```

## 8. Additional FastMCP Features to Support

### 8.1 Lifespan Management

FastMCP supports lifespan management via asynccontextmanager functions:

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def app_lifespan(server) -> AsyncIterator[dict]:
    """Application lifespan function."""
    # Setup code
    db = await Database.connect()
    
    try:
        yield {"db": db}  # Provide resources to operations
    finally:
        # Cleanup code
        await db.disconnect()
```

This can be referenced in the configuration:

```yaml
lifespan: "my_package.lifespan:app_lifespan"
```

Operations can access the lifespan context via:

```python
@operation()
async def query_db(self, query: str, ctx: Context):
    db = ctx.request_context.lifespan_context["db"]
    result = await db.execute(query)
    return result
```

### 8.2 Resource Access

FastMCP enables operations to access resources:

```python
@operation()
async def analyze_image(self, image_uri: str, ctx: Context):
    # Read image data
    image_data, mime_type = await ctx.read_resource(image_uri)
    
    # Process image
    # ...
    
    return "Analysis complete"
```

## 9. Implementation Plan

The recommended implementation steps for Phase 1:

1. **Create New Classes**:
   - Create enhanced `operation.py` with Context-aware decorator
   - Update `server.py` with FastMCP integration

2. **Tool Registration**:
   - Implement the tool wrapper registration system
   - Add support for detecting Context requirements
   
3. **Sequence of Changes**:
   1. Enhance operation decorator first
   2. Refactor AutoMCPServer class
   3. Implement tool registration system
   4. Update server start/run methods
   
4. **Testing Strategy**:
   - Unit tests for Context detection
   - Unit tests for tool wrapper registration
   - Integration tests with sample operations
   - Backwards compatibility tests with existing code

## 10. Conclusion

This design document outlines the changes needed for Phase 1 of the AutoMCP modernization plan: integrating FastMCP as a composed backend. The approach maintains backward compatibility with existing code while enabling new features like Context injection, enhanced return types, and lifespan management.

The implementation focuses on:

1. Refactoring `AutoMCPServer` to use composition with `FastMCP`
2. Creating a tool registration system to wrap operations
3. Enhancing the `@operation` decorator for Context detection
4. Maintaining backward compatibility
5. Supporting FastMCP's advanced features

Upon implementation, existing AutoMCP servers will continue to function while gaining access to the advanced capabilities of FastMCP, setting the stage for further modernization phases.