# AutoMCP Documentation Design

This document outlines the comprehensive documentation structure for the AutoMCP framework, including both inline code documentation and user-facing documentation.

## 1. Inline Documentation Standards (Google Style)

All code should follow Google Style docstrings, with the following specific format requirements for different code elements:

### 1.1 Module Docstrings

```python
"""Module description.

This section provides a detailed description of the module's purpose, 
functionality, and usage patterns.

Example:
    ```python
    from module_name import SomeClass
    
    instance = SomeClass()
    instance.some_method()
    ```
"""
```

### 1.2 Class Docstrings

```python
class ClassName:
    """Class description.
    
    This section provides a detailed description of the class's purpose,
    functionality, and usage patterns.
    
    Attributes:
        attribute_name (type): Description of the attribute.
        
    Note:
        Any important notes about using the class.
    """
```

### 1.3 Method/Function Docstrings

```python
def function_name(param1, param2, param3=None):
    """Function description.
    
    More detailed explanation if needed.
    
    Args:
        param1 (type): Description of param1.
        param2 (type): Description of param2.
        param3 (type, optional): Description of param3. Defaults to None.
        
    Returns:
        return_type: Description of the return value.
        
    Raises:
        ExceptionType: When and why this exception is raised.
        
    Example:
        ```python
        result = function_name('value1', 'value2')
        ```
    """
```

### 1.4 Property Docstrings

```python
@property
def property_name(self):
    """Property description.
    
    Returns:
        type: Description of the return value.
    """
```

### 1.5 Decorator Docstrings

```python
def decorator_name(param1=None, param2=None):
    """Decorator description.
    
    Args:
        param1 (type, optional): Description of param1. Defaults to None.
        param2 (type, optional): Description of param2. Defaults to None.
        
    Returns:
        callable: The decorated function/method.
        
    Example:
        ```python
        @decorator_name(param1='value')
        def some_function():
            pass
        ```
    """
```

## 2. User-Facing Documentation Structure

The `docs/` directory should be organized as follows:

```
docs/
├── index.md                    # Main entry point
├── getting_started/            # Getting started guides
│   ├── installation.md         # Installation instructions
│   ├── quickstart.md           # Quick start guide
│   └── configuration.md        # Configuration guide
├── core_concepts/              # Explanation of core concepts
│   ├── service_groups.md       # ServiceGroup explanation
│   ├── operations.md           # Operations and decorators
│   ├── schemas.md              # Input validation with schemas
│   └── context.md              # Context object and usage
├── advanced/                   # Advanced topics
│   ├── concurrency.md          # Concurrency handling
│   ├── timeouts.md             # Timeout configuration
│   ├── error_handling.md       # Error handling strategies
│   └── custom_resources.md     # Custom resource implementation
├── deployment/                 # Deployment guides
│   ├── cli.md                  # CLI usage
│   ├── integration.md          # Integration with other systems
│   └── security.md             # Security considerations
├── reference/                  # API reference
│   ├── group.md                # ServiceGroup API
│   ├── operation.md            # Operation decorator API
│   ├── server.md               # Server API
│   └── types.md                # Data models and types
├── tutorials/                  # Step-by-step tutorials
│   ├── basic_server.md         # Creating a basic server
│   ├── schema_validation.md    # Adding schema validation
│   └── progress_reporting.md   # Implementing progress reporting
└── llm_integration/            # LLM-specific documentation
    ├── concepts.md             # LLM-specific concepts
    ├── tool_design.md          # Designing effective tools for LLMs
    └── prompt_engineering.md   # Prompting best practices
```

## 3. LLM-Specific Concepts Documentation

The `docs/llm_integration/` directory should address the following key concepts:

### 3.1 Context Handling

Topics to cover in `context.md`:

- Context object purpose and functionality
- Progress reporting with Context
- Logging with Context
- Resource access through Context
- Best practices for Context usage

### 3.2 Schema Validation

Topics to cover in `schemas.md`:

- Pydantic schema design for LLM inputs
- Input validation strategies
- Error handling for invalid inputs
- Schema documentation for LLM understanding
- Advanced schema features (validators, computed fields)

### 3.3 Tool Design

Topics to cover in `tool_design.md`:

- Principles of effective tool design for LLMs
- Operation naming conventions
- Documentation clarity for LLM consumption
- Input/output format considerations
- Error messaging best practices

## 4. Sample Docstrings for Key Components

### 4.1 ServiceGroup Class

```python
class ServiceGroup:
    """Base class for implementing MCP service groups.
    
    ServiceGroup is the foundation for building modular functionality in AutoMCP.
    Each group encapsulates a set of related operations that can be exposed 
    as tools to an LLM through the MCP protocol.
    
    Upon initialization, the class automatically discovers and registers any 
    methods decorated with @operation.
    
    Attributes:
        registry (dict): Dictionary mapping operation names to their 
            implementation methods.
        config (GroupConfig): Configuration for this service group.
            
    Example:
        ```python
        class MyGroup(ServiceGroup):
            @operation()
            async def my_operation(self, param: str) -> str:
                return f"Processed: {param}"
        
        group = MyGroup()
        # Operations are automatically registered in group.registry
        ```
    """
```

### 4.2 Operation Decorator

```python
def operation(
    schema: type[BaseModel] | None = None,
    name: str | None = None,
    policy: str | None = None,
):
    """Decorator for exposing ServiceGroup methods as MCP operations.
    
    This decorator marks a method to be automatically registered as an 
    operation when the ServiceGroup is instantiated. It also handles input 
    validation using an optional Pydantic schema.
    
    Args:
        schema (type[BaseModel], optional): Pydantic model class for validating 
            operation input. When provided, the operation receives a validated 
            instance of this model as its first argument after self. 
            Defaults to None.
        name (str, optional): Custom name for the operation. If not provided, 
            the method name is used. Defaults to None.
        policy (str, optional): Policy to apply to the operation, such as 
            rate limiting or access control. Defaults to None.
    
    Returns:
        callable: Decorated method that will be registered as an operation.
        
    Example:
        ```python
        class UserSchema(BaseModel):
            name: str
            age: int
            
        class MyGroup(ServiceGroup):
            @operation(schema=UserSchema)
            async def greet_user(self, user: UserSchema) -> str:
                return f"Hello, {user.name}! You are {user.age} years old."
        ```
        
    Note:
        When using a schema, the decorated method must accept an instance 
        of the schema as its first argument after self.
        
        Context injection is supported by adding a parameter named 'ctx'.
        The context object provides access to logging, progress reporting,
        and other utilities.
    """
```

### 4.3 AutoMCPServer Class

```python
class AutoMCPServer:
    """MCP server implementation supporting both service and group configurations.
    
    AutoMCPServer provides a high-level interface for creating MCP-compatible
    servers that can be used with LLM systems like Claude. It handles the 
    registration of service groups, operation discovery, and request routing.
    
    Args:
        name (str): Server name.
        config (ServiceConfig | GroupConfig): Service or group configuration.
        timeout (float, optional): Operation timeout in seconds. Defaults to 30.0.
        
    Attributes:
        name (str): Server name.
        config (ServiceConfig | GroupConfig): Server configuration.
        timeout (float): Operation timeout in seconds.
        server (Server): Underlying MCP server instance.
        groups (dict[str, ServiceGroup]): Dictionary mapping group names to instances.
        
    Example:
        ```python
        # Using a service config (multiple groups)
        service_config = ServiceConfig.model_validate({
            "name": "my-service",
            "groups": {
                "module.path:GroupClass": {
                    "name": "group-name",
                }
            }
        })
        server = AutoMCPServer("MyServer", service_config)
        await server.start()
        
        # Using a group config (single group)
        group_config = GroupConfig.model_validate({
            "name": "group-name"
        })
        server = AutoMCPServer("MyServer", group_config)
        await server.start()
        ```
    """
```

### 4.4 ExecutionRequest Class

```python
class ExecutionRequest(BaseModel):
    """Request model for operation execution.
    
    This model represents a request to execute a specific operation with
    optional arguments.
    
    Attributes:
        operation (str): Operation name to execute.
        arguments (dict[str, Any] | None): Operation arguments.
        
    Private Attributes:
        _id (str): Unique request identifier.
        _created_at (datetime): Request creation timestamp.
        
    Example:
        ```python
        request = ExecutionRequest(
            operation="my_operation",
            arguments={"param1": "value1", "param2": 42}
        )
        ```
    """
```

## 5. Documentation Implementation Guidelines

### 5.1 Inline Docstrings

1. **Priority order**:
   - Start with core modules: group.py, operation.py, server.py, types.py
   - Then address utility modules and secondary components
   - Finally document test and example code

2. **Completeness requirements**:
   - All public classes, methods, and functions must have docstrings
   - All parameters must be documented
   - Return types must be specified
   - Exceptions must be documented when relevant

3. **Example code**:
   - Provide practical, runnable examples
   - Use realistic parameter names and values
   - Demonstrate common use cases

### 5.2 User-Facing Documentation

1. **Cross-referencing**:
   - Link related concepts across documents
   - Reference API documentation from guides
   - Maintain a consistent navigation structure

2. **Progressive disclosure**:
   - Start with high-level concepts and common use cases
   - Follow with detailed explanations and advanced topics
   - End with API reference material

3. **Content quality**:
   - Include practical examples in each document
   - Use clear, concise language
   - Target both newcomers and experienced users
   - Include diagrams for complex concepts

### 5.3 Documentation Testing

1. **Code examples**:
   - All code examples should be testable
   - Extract examples from docstrings into test files
   - Verify examples work with the latest version

2. **Link validation**:
   - Check for broken cross-references
   - Ensure all links work in generated documentation

3. **Completeness check**:
   - Verify all public APIs are documented
   - Ensure core concepts are covered adequately

## 6. Documentation Tooling

1. **Documentation generation**: 
   - Use Sphinx with Napoleon extension for Google-style docstrings
   - Configure autodoc for API reference generation
   - Set up ReadTheDocs or similar platform for hosting

2. **Static site generation**:
   - Use MkDocs for the user-facing documentation
   - Implement a consistent theme and navigation

3. **Docstring validation**:
   - Integrate pydocstyle with pre-commit hooks
   - Configure CI to check docstring coverage

## 7. Maintenance Plan

1. **Review process**:
   - Documentation changes require review
   - Technical accuracy check by core team
   - Clarity check by documentation specialists

2. **Update frequency**:
   - Update docs with each feature release
   - Quarterly review of existing documentation
   - Annual comprehensive revision

3. **Versioning**:
   - Maintain documentation versions matching software releases
   - Clearly indicate deprecated features
   - Provide migration guides between versions