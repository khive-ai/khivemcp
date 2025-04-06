# AutoMCP Framework Modernization Design Document

## 1. Introduction & Objectives

This document outlines the architectural changes needed to modernize the AutoMCP framework by replacing the older `mcp.server.Server` with the newer `mcp.server.fastmcp.FastMCP`. This migration will unlock advanced features while maintaining backward compatibility with existing code.

### Core Objectives

1. **Feature Enhancement**: Leverage FastMCP's advanced features including Context injection, progress reporting, logging, image returns, and more.
2. **Preserve Usability**: Maintain the configuration-driven approach that makes AutoMCP easy to use.
3. **Backward Compatibility**: Ensure existing ServiceGroup implementations continue to function.
4. **Performance Improvement**: Take advantage of FastMCP's concurrency model for better responsiveness.

## 2. Core Class Changes

### 2.1 AutoMCPServer Class

The `AutoMCPServer` class will be refactored to use composition instead of inheritance, integrating a FastMCP instance:

```python
class AutoMCPServer:
    """Modern MCP server implementation using FastMCP."""

    def __init__(
        self,
        name: str,
        config: ServiceConfig | GroupConfig,
        timeout: float = 30.0,
    ):
        """Initialize MCP server.

        Args:
            name: Server name
            config: Service or group configuration
            timeout: Operation timeout in seconds
        """
        self.name = name
        self.config = config
        self.timeout = timeout
        
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
        
        self.groups: dict[str, ServiceGroup] = {}

        # Initialize groups based on config type
        if isinstance(config, ServiceConfig):
            self._init_service_groups()
        else:
            self._init_single_group()

        # Register all operations as tools
        self._register_tools()
```

### 2.2 Tool Registration Methods

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
                # Call without context
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

### 2.3 Server Start Method

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

## 3. Context Injection Mechanism

FastMCP allows operations to request a Context object that provides access to logging, progress reporting, and other capabilities.

### 3.1 Updated Operation Decorator

```python
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

### 3.2 Context Usage Example

```python
from mcp.server.fastmcp import Context

class DataGroup(ServiceGroup):
    @operation(schema=DataProcessingSchema)
    async def process_data(self, input_data: DataProcessingSchema, ctx: Context) -> str:
        """Process data with progress reporting."""
        await ctx.info(f"Processing {len(input_data.items)} items")
        
        # Report initial progress
        await ctx.report_progress(0, total=len(input_data.items))
        
        # Process each item
        for i, item in enumerate(input_data.items):
            result = self._process_item(item)
            await ctx.report_progress(i + 1)
            
        await ctx.info("Processing complete")
        return "Data processing completed successfully"
```

## 4. Return Type Handling

FastMCP provides built-in support for converting various return types to appropriate MCP content types:

| Return Type | MCP Content Type |
|-------------|------------------|
| `str`, `int`, `float`, `bool` | `TextContent` |
| `mcp.server.fastmcp.Image` | `ImageContent` |
| Pydantic models | JSON-serialized as `TextContent` |
| Lists/tuples of the above | List of respective content types |

### 4.1 Example Return Type Implementation

```python
class ImageGroup(ServiceGroup):
    @operation(schema=ImageRequestSchema)
    async def generate_chart(self, request: ImageRequestSchema, ctx: Context) -> Image:
        """Generate a chart based on input data."""
        await ctx.info("Generating chart...")
        
        # Generate chart image using matplotlib
        plt.figure(figsize=(10, 6))
        plt.plot(request.x_values, request.y_values)
        plt.title(request.title)
        
        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Return as Image
        return Image(data=buf.getvalue(), format="png")
    
    @operation()
    def mixed_content(self) -> list:
        """Return mixed content types."""
        text_content = "This is text content"
        image = Image(path="path/to/image.png")
        
        # FastMCP will convert this to a list with both TextContent and ImageContent
        return [text_content, image]
```

## 5. Integration of FastMCP's Features

### 5.1 Logging

Operations can use FastMCP's logging features by requesting a Context parameter:

```python
@operation()
async def log_operation(self, input_data: str, ctx: Context) -> str:
    """Operation that logs its progress."""
    await ctx.debug("Debug-level information")
    await ctx.info("Info-level status update")
    await ctx.warning("Warning about potential issues")
    await ctx.error("Error information (non-fatal)")
    
    return "Operation completed with logs"
```

### 5.2 Progress Reporting

Long-running operations can report progress:

```python
@operation()
async def process_files(self, file_paths: list[str], ctx: Context) -> str:
    """Process multiple files with progress reporting."""
    total = len(file_paths)
    await ctx.report_progress(0, total=total)
    
    results = []
    for i, file_path in enumerate(file_paths):
        # Process file
        result = self._process_file(file_path)
        results.append(result)
        
        # Report progress
        await ctx.report_progress(i + 1, total=total)
        
    return "\n".join(results)
```

### 5.3 Resource Access

Operations can access resources through the Context object:

```python
@operation(schema=ResourceRequestSchema)
async def analyze_resource(self, request: ResourceRequestSchema, ctx: Context) -> str:
    """Analyze content from a resource."""
    # Read resource content
    content, mime_type = await ctx.read_resource(request.resource_uri)
    
    # Process the content based on mime_type
    if mime_type.startswith("text/"):
        return f"Analyzed text resource: {len(content)} characters"
    elif mime_type.startswith("image/"):
        return f"Analyzed image resource: {len(content)} bytes"
    else:
        return f"Analyzed resource of type {mime_type}: {len(content)} bytes"
```

### 5.4 Lifespan Management

The modernized framework will support lifespan functions for setup and teardown operations:

```python
# In a separate module (my_package.lifespan)
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from database import Database

@dataclass
class AppContext:
    db: Database
    config: dict

@asynccontextmanager
async def app_lifespan(server) -> AsyncIterator[AppContext]:
    """Initialize resources and provide context."""
    # Setup phase
    print("Starting database connection")
    db = await Database.connect()
    config = load_config()
    
    try:
        # Yield the context to the application
        yield AppContext(db=db, config=config)
    finally:
        # Cleanup phase
        print("Closing database connection")
        await db.disconnect()
```

Then in the YAML configuration:

```yaml
# config.yaml
name: "MyService"
description: "Service with lifespan management"
lifespan: "my_package.lifespan:app_lifespan"
# ...
```

And usage in an operation:

```python
@operation()
async def query_database(self, query: str, ctx: Context) -> str:
    """Execute a database query using the connection from lifespan."""
    # Access the database from lifespan context
    app_context = ctx.request_context.lifespan_context
    db = app_context.db
    
    result = await db.execute(query)
    return result
```

## 6. Component Diagrams

### 6.1 High-Level Architecture

```
┌──────────────────────────────────┐
│         AutoMCPServer            │
│                                  │
│  ┌───────────┐    ┌───────────┐  │
│  │  FastMCP  │    │ ServiceGroup │◄───┐
│  │  Instance │    │  Instances  │    │
│  └───────────┘    └───────────┘  │    │
│         │              ▲         │    │
└─────────┼──────────────┼─────────┘    │
          │              │              │
          ▼              │              │
┌──────────────────┐     │         ┌────────────┐
│   MCP Protocol   │     └─────────┤ @operation │
│   (JSON-RPC)     │               │ Decorator  │
└──────────────────┘               └────────────┘
```

### 6.2 Tool Registration and Execution Flow

```
┌──────────────────┐   Registers   ┌───────────────┐
│ ServiceGroup with │──────────────►│ AutoMCPServer │
│  @operations     │               │               │
└──────────────────┘               └───────┬───────┘
                                          │
                                          ▼
                                  ┌───────────────┐
                                  │ Create wrapper│
                                  │   functions   │
                                  └───────┬───────┘
                                          │
                                          ▼
                                  ┌───────────────┐
                                  │ Register with │
                                  │    FastMCP    │
                                  └───────┬───────┘
                                          │
             ┌──────────────┐             ▼
Client ──────► tools/call   │───────► ┌───────────────┐
             └──────────────┘         │ FastMCP routes│
                                      │  to wrapper   │
                                      └───────┬───────┘
                                              │
                                              ▼
                                      ┌───────────────┐
                            ┌─────────┤  Check for    │
                            │         │ Context need  │
                            │         └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │Call ServiceGroup│
                    │   operation   │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Return result │
                    │ (auto-convert)│
                    └───────────────┘
```

### 6.3 Context and Resource Interaction

```
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Operation   │    │    Context    │    │    FastMCP    │
│               │    │               │    │               │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        │ request            │                    │
        │ ctx.info("msg")    │                    │
        ├───────────────────►│                    │
        │                    │ notification       │
        │                    ├───────────────────►│
        │                    │                    │
        │ request            │                    │
        │ ctx.report_progress│                    │
        ├───────────────────►│                    │
        │                    │ progress           │
        │                    ├───────────────────►│
        │                    │                    │
        │ request            │                    │
        │ ctx.read_resource  │                    │
        ├───────────────────►│                    │
        │                    │ resource/read      │
        │                    ├───────────────────►│
        │                    │                    │
        │                    │ resource content   │
        │                    │◄───────────────────┤
        │ resource content   │                    │
        │◄───────────────────┤                    │
        │                    │                    │
```

## 7. Backward Compatibility Considerations

### 7.1 Operation Signatures

The modernized framework maintains backward compatibility with existing operations:

- **Existing Operations**: Operations without Context parameters will continue to work unchanged
- **New Context Feature**: Only operations explicitly requesting Context will receive it
- **Automatic Detection**: The framework automatically detects if an operation needs Context by inspecting its signature

### 7.2 Return Types

The return type handling will be expanded while maintaining compatibility:

- **Existing Return Types**: Text returns will work as before
- **Enhanced Types**: New support for images, Pydantic models, and mixed content
- **Automatic Conversion**: FastMCP handles conversion to appropriate MCP types

### 7.3 Configuration Files

Existing configuration files will remain compatible:

- **Core Structure**: Unchanged format for groups, packages, and env_vars
- **New Fields**: Optional fields like `lifespan` enhance functionality without breaking compatibility
- **Validation**: Type validation will continue to work as before

### 7.4 Transport Options

While stdio remains the default, the modernized framework adds support for other transport methods:

- **Default stdio**: Maintains compatibility with existing deployment patterns
- **New Options**: Optional SSE or WebSocket transport through FastMCP
- **Environment Integration**: Continued support for mcp CLI tools

## 8. Example Configuration

### 8.1 Configuration File

```yaml
# config.yaml
name: "AnalyticsService"
description: "Data analytics service with FastMCP features"

# Optional lifespan function for setup/teardown
lifespan: "my_package.lifespan:app_lifespan"

# Required packages (dependencies)
packages:
  - pandas
  - numpy
  - matplotlib

# Environment variables
env_vars:
  API_KEY: "${API_KEY}"
  LOG_LEVEL: "INFO"

# Service groups
groups:
  "my_package.groups.math:MathGroup":
    name: "math"
    description: "Mathematical operations"
    packages:
      - sympy  # Group-specific packages
    config:
      precision: 4  # Group-specific configuration
  
  "my_package.groups.data:DataGroup":
    name: "data"
    description: "Data analysis and processing"
    packages:
      - scikit-learn
    env_vars:
      DATA_PATH: "${DATA_PATH}"  # Group-specific environment variables
```

### 8.2 Example Implementation

```python
# my_package/groups/data.py
from mcp.server.fastmcp import Context, Image
from automcp import ServiceGroup, operation
from pydantic import BaseModel

class DataAnalysisInput(BaseModel):
    data_path: str
    columns: list[str]
    analysis_type: str

class DataGroup(ServiceGroup):
    @operation(schema=DataAnalysisInput)
    async def analyze(self, input_data: DataAnalysisInput, ctx: Context) -> list:
        """Analyze data and return both text and visualizations."""
        await ctx.info(f"Starting analysis of {input_data.data_path}")
        
        # Load data
        import pandas as pd
        try:
            df = pd.read_csv(input_data.data_path)
        except Exception as e:
            await ctx.error(f"Failed to load data: {e}")
            return f"Error: {e}"
        
        # Generate text summary
        summary = f"Dataset has {len(df)} rows and {len(df.columns)} columns"
        
        # Generate visualization
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        plt.figure(figsize=(10, 6))
        df[input_data.columns].plot()
        plt.title(f"{input_data.analysis_type} Analysis")
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        chart = Image(data=buf.getvalue(), format="png")
        
        # Return mixed content
        return [summary, chart]
```

## 9. Implementation Roadmap

To implement this modernization, we recommend the following steps:

1. **Core Server Update**:
   - Refactor `AutoMCPServer` to use FastMCP composition
   - Implement the tool wrapper registration system
   - Update the start method to use FastMCP transport

2. **Operation Decorator Enhancement**:
   - Update the `@operation` decorator to detect Context usage
   - Add support for Context injection
   - Ensure backward compatibility with existing operations

3. **Configuration Updates**:
   - Add support for lifespan configuration
   - Ensure all existing configuration options are preserved

4. **Testing**:
   - Create tests for Context injection
   - Test various return types (text, images, mixed)
   - Test logging and progress reporting functionality
   - Verify backward compatibility with existing code

5. **Documentation**:
   - Update developer guide with Context usage examples
   - Document new return type capabilities
   - Provide migration guidelines for existing users

## 10. Conclusion

The modernization of AutoMCP to use FastMCP will significantly enhance its capabilities while maintaining backward compatibility with existing code. The new design leverages FastMCP's advanced features like Context injection, diverse return types, and improved concurrency, providing developers with a more powerful and flexible framework for creating MCP servers.

By embracing this modernization, AutoMCP will continue to provide a user-friendly, configuration-driven approach to MCP server creation while unlocking the latest advances in the MCP ecosystem.