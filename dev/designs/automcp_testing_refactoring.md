---
title: AutoMCP Testing Framework Refactoring
created_at: 2025-04-05
updated_at: 2025-04-05
author: AutoMCP Designer
version: 1.0
description: |
    Design document for refactoring the testing utilities in AutoMCP to improve code reuse,
    standardize parameter handling, and enhance the overall testing experience.
---

# AutoMCP Testing Framework Refactoring

## 1. Overview

This design document outlines improvements to the AutoMCP framework focusing on the relationship between the `automcp` core and `verification` directories. The goal is to apply DRY principles and enhance code quality without adding technical debt.

### 1.1 Current Issues

1. **Duplicated Test Helpers**: Testing utilities in `verification/tests/test_helpers.py` are not easily reusable by other projects using AutoMCP.
2. **Special Case Handlers**: The current implementation requires custom handlers for different operation types (e.g., `fixed_sleep_handler`, `fixed_process_data_handler`).
3. **Inconsistent Parameter Handling**: Operations require custom mapping code to handle parameters correctly.
4. **Schema Management**: Schemas are defined in the verification directory but could be more centrally located for reuse.
5. **Server Connection Utilities**: In-memory server-client communication patterns are not standardized.

### 1.2 Design Goals

1. Create a standardized, reusable testing framework for AutoMCP
2. Eliminate special case handlers through a unified parameter handling approach
3. Centralize schema management for better reuse
4. Standardize server connection utilities for MCP server/client testing

## 2. Test Helpers Refactoring

### 2.1 New Directory Structure

```
automcp/
├── testing/
│   ├── __init__.py
│   ├── context.py         # Existing MockContext implementation
│   ├── server.py          # New TestServer implementation
│   ├── client.py          # New TestClient implementation
│   ├── streams.py         # Memory stream utilities
│   ├── parameter.py       # Parameter handling utilities
│   └── schemas/           # Common test schemas
│       ├── __init__.py
│       └── common.py      # Common schema definitions
```

### 2.2 TestServer Class

Create a standard `TestServer` class that handles special cases without custom code for each operation:

```python
class TestServer:
    """Test server for AutoMCP operations.
    
    This class provides a standardized way to create and test AutoMCP servers
    with automatic parameter handling and schema validation.
    """
    
    def __init__(
        self,
        server: AutoMCPServer,
        parameter_transformers: dict[str, ParameterTransformer] = None,
    ):
        """Initialize the test server.
        
        Args:
            server: The AutoMCPServer instance to test
            parameter_transformers: Optional dictionary mapping operation names to
                parameter transformers for custom parameter handling
        """
        self.server = server
        self.parameter_transformers = parameter_transformers or {}
        
    async def create_client_session(
        self,
        read_timeout_seconds: timedelta | None = None,
    ) -> ClientSession:
        """Create a client session connected to this server.
        
        Args:
            read_timeout_seconds: Optional timeout for read operations
            
        Returns:
            A connected ClientSession
        """
        # Implementation details...
        
    @contextlib.asynccontextmanager
    async def create_connected_client_session(
        self,
        read_timeout_seconds: timedelta | None = None,
    ) -> AsyncGenerator[ClientSession, None]:
        """Create a client session connected to this server as a context manager.
        
        Args:
            read_timeout_seconds: Optional timeout for read operations
            
        Returns:
            A connected ClientSession
        """
        # Implementation details...
```

### 2.3 Parameter Transformation

Create a `ParameterTransformer` protocol and standard implementations to handle different parameter transformation patterns:

```python
class ParameterTransformer(Protocol):
    """Protocol for parameter transformers."""
    
    async def transform(
        self,
        operation_name: str,
        arguments: dict[str, Any],
        context: types.TextContent | None = None,
    ) -> dict[str, Any]:
        """Transform parameters for an operation.
        
        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context
            
        Returns:
            Transformed arguments
        """
        ...

class SchemaParameterTransformer(ParameterTransformer):
    """Parameter transformer for schema-based operations."""
    
    def __init__(self, schema_class: type[BaseModel], param_name: str = None):
        """Initialize the transformer.
        
        Args:
            schema_class: The Pydantic schema class
            param_name: Optional parameter name, defaults to the schema class name
        """
        self.schema_class = schema_class
        self.param_name = param_name or schema_class.__name__.lower()
        
    async def transform(
        self,
        operation_name: str,
        arguments: dict[str, Any],
        context: types.TextContent | None = None,
    ) -> dict[str, Any]:
        """Transform parameters using the schema.
        
        This method handles both flat arguments and nested arguments.
        
        Args:
            operation_name: The name of the operation
            arguments: The arguments to transform
            context: Optional context
            
        Returns:
            Transformed arguments
        """
        # Implementation details...
```

### 2.4 Operation Handler Factory

Create a factory function to generate operation handlers dynamically:

```python
def create_operation_handler(
    group: ServiceGroup,
    operation_name: str,
    parameter_transformer: ParameterTransformer = None,
) -> Callable:
    """Create a handler function for an operation.
    
    Args:
        group: The service group containing the operation
        operation_name: The name of the operation
        parameter_transformer: Optional parameter transformer
        
    Returns:
        A handler function that can be registered with FastMCP
    """
    operation = group.registry.get(operation_name)
    if not operation:
        raise ValueError(f"Unknown operation: {operation_name}")
        
    async def handler(
        arguments: dict | None = None,
        ctx: types.TextContent = None,
    ) -> types.TextContent:
        try:
            # Transform parameters if needed
            transformed_args = arguments or {}
            if parameter_transformer:
                transformed_args = await parameter_transformer.transform(
                    operation_name, transformed_args, ctx
                )
                
            # Add context if needed
            if hasattr(operation, "requires_context") and operation.requires_context:
                transformed_args["ctx"] = ctx
                
            # Execute operation
            result = await operation(**transformed_args)
            
            # Convert result to TextContent
            response_text = ""
            if isinstance(result, BaseModel):
                response_text = result.model_dump_json()
            elif isinstance(result, (dict, list)):
                response_text = json.dumps(result)
            elif result is not None:
                response_text = str(result)
                
            return types.TextContent(type="text", text=response_text)
            
        except Exception as e:
            error_msg = f"Error during '{operation_name}' execution: {str(e)}"
            logging.exception(error_msg)
            return types.TextContent(type="text", text=error_msg)
            
    return handler
```

## 3. Parameter Handling Standardization

### 3.1 Unified Parameter Handling

Modify the `@operation` decorator to include parameter transformation capabilities:

```python
def operation(
    schema: type[BaseModel] | None = None,
    name: str | None = None,
    policy: str | None = None,
    parameter_transformer: ParameterTransformer | None = None,
) -> Callable:
    """Decorator for service operations.
    
    This decorator marks a method as an operation that can be executed by
    the ServiceGroup. It handles schema validation, context injection,
    parameter transformation, and attaches metadata to the wrapped function.
    
    Args:
        schema: Optional Pydantic model class for input validation
        name: Optional custom name for the operation. Defaults to the function name
        policy: Optional policy string for access control
        parameter_transformer: Optional parameter transformer for custom parameter handling
        
    Returns:
        A decorator function that wraps the original operation method
    """
    # Implementation details...
```

### 3.2 Standard Parameter Transformers

Create a set of standard parameter transformers for common patterns:

1. `FlatParameterTransformer`: Handles flat parameters (e.g., `{"name": "John", "age": 30}`)
2. `NestedParameterTransformer`: Handles nested parameters (e.g., `{"person": {"name": "John", "age": 30}}`)
3. `SchemaParameterTransformer`: Handles schema-based parameters (as shown above)
4. `CompositeParameterTransformer`: Combines multiple transformers

## 4. Schema Management

### 4.1 Central Schema Location

Move common schemas to a central location in the `automcp` package:

```
automcp/
├── schemas/
│   ├── __init__.py
│   ├── common.py       # Common schema definitions
│   ├── validation.py   # Schema validation utilities
│   └── extraction.py   # Parameter extraction utilities
```

### 4.2 Schema Registry

Create a schema registry to manage and retrieve schemas:

```python
class SchemaRegistry:
    """Registry for Pydantic schemas.
    
    This class provides a central registry for Pydantic schemas used in
    AutoMCP operations, allowing for schema reuse and discovery.
    """
    
    def __init__(self):
        """Initialize the schema registry."""
        self.schemas: dict[str, type[BaseModel]] = {}
        
    def register(self, schema: type[BaseModel], name: str = None) -> None:
        """Register a schema.
        
        Args:
            schema: The Pydantic schema class
            name: Optional name for the schema, defaults to the schema class name
        """
        name = name or schema.__name__
        self.schemas[name] = schema
        
    def get(self, name: str) -> type[BaseModel] | None:
        """Get a schema by name.
        
        Args:
            name: The name of the schema
            
        Returns:
            The schema class, or None if not found
        """
        return self.schemas.get(name)
```

### 4.3 Schema Validation Utilities

Create utilities for schema validation and parameter extraction:

```python
def validate_schema(
    schema: type[BaseModel],
    data: dict[str, Any],
    partial: bool = False,
) -> BaseModel:
    """Validate data against a schema.
    
    Args:
        schema: The Pydantic schema class
        data: The data to validate
        partial: Whether to allow partial validation (missing fields)
        
    Returns:
        A validated schema instance
        
    Raises:
        ValidationError: If validation fails
    """
    # Implementation details...
    
def extract_schema_parameters(
    schema: type[BaseModel],
    data: dict[str, Any],
    nested_key: str = None,
) -> dict[str, Any]:
    """Extract parameters for a schema from data.
    
    This function handles both flat and nested parameters.
    
    Args:
        schema: The Pydantic schema class
        data: The data to extract parameters from
        nested_key: Optional key for nested parameters
        
    Returns:
        Extracted parameters
    """
    # Implementation details...
```

## 5. Server Connection Utilities

### 5.1 Memory Stream Utilities

Create utilities for in-memory server-client communication:

```python
@contextlib.asynccontextmanager
async def create_memory_streams() -> AsyncGenerator[tuple[MessageStream, MessageStream], None]:
    """Create a pair of bidirectional memory streams for client-server communication.
    
    Returns:
        A tuple of (client_streams, server_streams) where each is a tuple of
        (read_stream, write_stream)
    """
    # Implementation details...
```

### 5.2 TestClient Class

Create a `TestClient` class for testing MCP servers:

```python
class TestClient:
    """Test client for MCP servers.
    
    This class provides a standardized way to test MCP servers with
    automatic parameter handling and result parsing.
    """
    
    def __init__(
        self,
        client_session: ClientSession,
        parameter_transformers: dict[str, ParameterTransformer] = None,
    ):
        """Initialize the test client.
        
        Args:
            client_session: The ClientSession to use
            parameter_transformers: Optional dictionary mapping operation names to
                parameter transformers for custom parameter handling
        """
        self.client_session = client_session
        self.parameter_transformers = parameter_transformers or {}
        
    async def call_operation(
        self,
        operation_name: str,
        arguments: dict[str, Any] = None,
        transform_parameters: bool = True,
    ) -> Any:
        """Call an operation on the server.
        
        Args:
            operation_name: The name of the operation to call
            arguments: The arguments to pass to the operation
            transform_parameters: Whether to transform parameters
            
        Returns:
            The operation result
        """
        # Implementation details...
```

### 5.3 Integration Testing Utilities

Create utilities for integration testing:

```python
@contextlib.asynccontextmanager
async def create_test_environment(
    server: AutoMCPServer,
    parameter_transformers: dict[str, ParameterTransformer] = None,
    read_timeout_seconds: timedelta | None = None,
) -> AsyncGenerator[tuple[TestServer, TestClient], None]:
    """Create a test environment with a server and client.
    
    Args:
        server: The AutoMCPServer to test
        parameter_transformers: Optional dictionary mapping operation names to
            parameter transformers for custom parameter handling
        read_timeout_seconds: Optional timeout for read operations
        
    Returns:
        A tuple of (test_server, test_client)
    """
    # Implementation details...
```

## 6. Implementation Plan

### 6.1 Phase 1: Core Testing Framework

1. Create the `automcp/testing/streams.py` module with memory stream utilities
2. Create the `automcp/testing/parameter.py` module with parameter transformation utilities
3. Create the `automcp/testing/server.py` module with the `TestServer` class
4. Create the `automcp/testing/client.py` module with the `TestClient` class

### 6.2 Phase 2: Schema Management

1. Create the `automcp/schemas` package with common schema definitions
2. Create the `SchemaRegistry` class
3. Create schema validation and parameter extraction utilities

### 6.3 Phase 3: Integration and Migration

1. Update the `@operation` decorator to support parameter transformers
2. Create integration testing utilities
3. Migrate existing tests to use the new framework
4. Update documentation

## 7. Conclusion

This design addresses the key opportunities for improving the AutoMCP framework:

1. **Test Helpers Refactoring**: By moving test helpers to `automcp/testing/` and creating standardized classes, we make them more reusable and maintainable.
2. **Parameter Handling Standardization**: By creating a unified approach to parameter handling with transformers, we eliminate the need for special case handlers.
3. **Schema Management**: By centralizing schema management, we improve reuse and consistency.
4. **Server Connection Utilities**: By standardizing in-memory server-client communication, we make it easier to test MCP servers.

These improvements will make the AutoMCP framework more robust, maintainable, and user-friendly, while adhering to DRY principles and avoiding technical debt.