# Broken Links Resolution Design

## Overview

This document outlines the design for resolving the 13 broken links identified in the AutoMCP documentation. Fixing these links is a high-priority task according to the testing report, as they significantly impact the usability of the documentation.

## 1. Issue Analysis

The verification report identified 13 broken links across the documentation:

### 1.1 In `docs/index.md`

- advanced/concurrency.md
- advanced/timeouts.md
- advanced/error_handling.md
- advanced/custom_resources.md
- reference/group.md
- reference/operation.md
- reference/server.md
- reference/types.md
- llm_integration/concepts.md
- llm_integration/tool_design.md
- llm_integration/prompt_engineering.md
- contributing.md

### 1.2 In `docs/getting_started/quickstart.md`

- ../tutorials/basic_server.md

## 2. Resolution Approach

There are two possible approaches to resolving these broken links:

1. **Create the missing files**: Develop new content for each missing file
2. **Update the links**: Change the links to point to existing content

Given the importance of having comprehensive documentation, **creating the missing files** is the preferred approach. This will ensure that users have access to all the information referenced in the documentation.

## 3. File Creation Plan

### 3.1 Advanced Topics Directory

Create the following files in the `docs/advanced/` directory:

#### 3.1.1 `concurrency.md`

Basic structure:
```markdown
# Concurrency in AutoMCP

Introduction to concurrency concepts in AutoMCP...

## Understanding Async Operations

Explanation of async/await in AutoMCP operations...

## Parallel Execution

Guidance on parallel operation execution...

## Resource Sharing

Best practices for sharing resources across concurrent operations...

## Common Patterns

Examples of common concurrency patterns...

## Related Topics

- [Timeouts](timeouts.md)
- [Error Handling](error_handling.md)
```

#### 3.1.2 `timeouts.md`

Basic structure:
```markdown
# Timeout Management in AutoMCP

Introduction to timeout management...

## Operation Timeouts

How to set and manage operation timeouts...

## Timeout Configuration

Configuring default timeouts...

## Handling Timeout Exceptions

How to properly handle timeout exceptions...

## Best Practices

Best practices for timeout management...

## Related Topics

- [Concurrency](concurrency.md)
- [Error Handling](error_handling.md)
```

#### 3.1.3 `error_handling.md`

Basic structure:
```markdown
# Error Handling in AutoMCP

Introduction to error handling...

## Operation Exceptions

How operations handle and propagate exceptions...

## Error Response Structure

The structure of error responses in AutoMCP...

## Client-Side Error Handling

Guidelines for handling errors on the client side...

## Best Practices

Best practices for robust error handling...

## Related Topics

- [Concurrency](concurrency.md)
- [Timeouts](timeouts.md)
```

#### 3.1.4 `custom_resources.md`

Basic structure:
```markdown
# Custom Resources in AutoMCP

Introduction to custom resources...

## Resource Management

How to create and manage custom resources...

## Lifecycle Hooks

Using lifecycle hooks for resource management...

## Dependency Injection

Implementing dependency injection for resources...

## Examples

Complete examples of custom resource management...

## Related Topics

- [Service Groups](../core_concepts/service_groups.md)
- [Context](../core_concepts/context.md)
```

### 3.2 Reference Directory

Create the following files in the `docs/reference/` directory:

#### 3.2.1 `group.md`

Basic structure:
```markdown
# ServiceGroup Reference

Complete reference for the ServiceGroup class...

## Class Definition

The ServiceGroup class definition and inheritance...

## Properties

List of properties with descriptions...

## Methods

List of methods with signatures and descriptions...

## Lifecycle Hooks

Available lifecycle hooks and their usage...

## Examples

Complete examples of ServiceGroup implementation...

## Related Reference

- [Operation](operation.md)
- [Server](server.md)
```

#### 3.2.2 `operation.md`

Basic structure:
```markdown
# Operation Decorator Reference

Complete reference for the @operation decorator...

## Function Signature

The full signature of the operation decorator...

## Parameters

Detailed description of all parameters...

## Schema Integration

How to use schemas with operations...

## Context Usage

How to use the context object in operations...

## Examples

Complete examples of operation definitions...

## Related Reference

- [ServiceGroup](group.md)
- [Schemas](../core_concepts/schemas.md)
```

#### 3.2.3 `server.md`

Basic structure:
```markdown
# Server Reference

Complete reference for the AutoMCP server...

## Server Classes

Available server implementations...

## Configuration

Server configuration options...

## Lifecycle

Server lifecycle management...

## Examples

Complete examples of server setup...

## Related Reference

- [ServiceGroup](group.md)
- [Configuration](../getting_started/configuration.md)
```

#### 3.2.4 `types.md`

Basic structure:
```markdown
# Types Reference

Complete reference for AutoMCP types...

## Configuration Types

Types used for configuration...

## Context Types

Types related to the context object...

## Schema Types

Types used in schema definitions...

## Utility Types

Utility types and helpers...

## Examples

Examples of type usage...

## Related Reference

- [Schemas](../core_concepts/schemas.md)
- [Context](../core_concepts/context.md)
```

### 3.3 LLM Integration Directory

Create the following files in the `docs/llm_integration/` directory:

#### 3.3.1 `concepts.md`

See the `LLMIntegrationDocumentation.md` design document for detailed structure.

#### 3.3.2 `tool_design.md`

See the `LLMIntegrationDocumentation.md` design document for detailed structure.

#### 3.3.3 `prompt_engineering.md`

See the `LLMIntegrationDocumentation.md` design document for detailed structure.

### 3.4 Project Root Documentation

#### 3.4.1 `contributing.md`

Basic structure:
```markdown
# Contributing to AutoMCP

Guidelines for contributing to the AutoMCP project...

## Code of Conduct

Code of conduct for contributors...

## Setting Up Development Environment

How to set up your development environment...

## Development Workflow

The development workflow for contributions...

## Pull Request Process

How to submit and review pull requests...

## Style Guide

Coding style guidelines...

## Testing

Testing requirements and procedures...

## Documentation

Documentation requirements and standards...
```

### 3.5 Tutorials Directory

#### 3.5.1 `basic_server.md`

Basic structure:
```markdown
# Building a Basic AutoMCP Server

Step-by-step tutorial for building a basic AutoMCP server...

## Prerequisites

What you'll need before starting...

## Project Setup

Setting up your project...

## Creating a ServiceGroup

Implementing your first ServiceGroup...

## Configuring the Server

Creating a server configuration file...

## Running the Server

Starting and testing your server...

## Next Steps

Where to go from here...
```

## 4. Implementation Strategy

### 4.1 Prioritization

Implement the files in this order:

1. High Priority:
   - llm_integration/concepts.md
   - llm_integration/tool_design.md
   - llm_integration/prompt_engineering.md
   - reference/operation.md

2. Medium Priority:
   - reference/group.md
   - reference/server.md
   - reference/types.md
   - tutorials/basic_server.md

3. Lower Priority:
   - advanced/concurrency.md
   - advanced/timeouts.md
   - advanced/error_handling.md
   - advanced/custom_resources.md
   - contributing.md

### 4.2 Content Development Guidelines

When developing content for these files:

1. **Consistency**: Maintain consistent style and formatting across all files
2. **Completeness**: Ensure all topics mentioned in the outline are covered
3. **Examples**: Include practical, runnable code examples
4. **Cross-References**: Add links to related documentation
5. **Progressive Disclosure**: Follow proper heading hierarchy (H1 > H2 > H3)

### 4.3 Content Sources

Gather information for these files from:

1. **Existing Code**: Analyze the AutoMCP codebase for examples and reference
2. **Design Documents**: Review original design documents for intentions and concepts
3. **Test Files**: Extract examples and usage patterns from test files
4. **Verification Code**: Review verification scripts for expectations and standards

## 5. Link Verification

After creating all the missing files:

1. Run the documentation verification script:
   ```
   python verification/check_docs_structure.py
   ```

2. Verify that no broken links are reported

3. Check for any new links added during content development that might also be broken

4. Ensure all cross-references within the new documents are valid

## 6. Example Content: `reference/operation.md`

Here's a more detailed outline for the `operation.md` file, which is a high-priority item:

```markdown
# Operation Decorator Reference

The `@operation` decorator is a core feature of AutoMCP that transforms regular methods in ServiceGroup classes into callable operations exposed through the MCP protocol.

## Basic Usage

The most basic use of the operation decorator:

```python
from automcp import ServiceGroup, operation

class ExampleGroup(ServiceGroup):
    @operation()
    async def simple_operation(self, input_string: str) -> str:
        """A simple operation that returns the input string.
        
        Args:
            input_string: The input string
            
        Returns:
            The same input string
        """
        return input_string
```

## Parameters

The operation decorator accepts several parameters to customize the behavior of the operation:

### name

Specifies a custom name for the operation. If not provided, the method name is used.

```python
@operation(name="custom_name")
async def method_name(self, ...) -> ...:
    # This operation will be exposed as "custom_name" instead of "method_name"
    ...
```

### schema

A Pydantic BaseModel class that defines the schema for the operation's input parameters.

```python
from pydantic import BaseModel, Field

class AddNumbersRequest(BaseModel):
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")

@operation(schema=AddNumbersRequest)
async def add(self, request: AddNumbersRequest) -> float:
    """Add two numbers.
    
    Args:
        request: The validated request containing two numbers
        
    Returns:
        The sum of the two numbers
    """
    return request.a + request.b
```

### timeout

Specifies a timeout in seconds for the operation. If the operation exceeds this timeout, it will be cancelled and an error will be returned.

```python
@operation(timeout=30)
async def long_running_operation(self, ...) -> ...:
    # This operation will time out after 30 seconds if not completed
    ...
```

## Using Context

Operations can receive a context object that provides access to request information, progress reporting, and logging.

```python
from mcp.server.fastmcp import Context

@operation()
async def operation_with_context(self, input_data: str, ctx: Context) -> str:
    # The context is automatically injected
    await ctx.report_progress(0, 2)
    # Do some processing...
    ctx.info(f"Processing: {input_data}")
    await ctx.report_progress(1, 2)
    # Do more processing...
    await ctx.report_progress(2, 2)
    return result
```

## Advanced Configuration

### Multiple decorators

You can combine multiple decorators with the operation decorator:

```python
def log_call(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        print(f"Calling {func.__name__}")
        return await func(self, *args, **kwargs)
    return wrapper

@operation()
@log_call
async def logged_operation(self, ...) -> ...:
    # This operation will be logged when called
    ...
```

### Operation registration

Operations are automatically registered with the ServiceGroup when the class is instantiated. You can access the registry to see all registered operations:

```python
group_instance = MyServiceGroup()
print(group_instance.registry)  # Shows all registered operations
```

## Error Handling

Operations can handle errors in several ways:

```python
@operation()
async def operation_with_error_handling(self, input_data: str) -> dict:
    try:
        # Attempt some operation that might fail
        result = process_data(input_data)
        return {"success": True, "result": result}
    except ValueError as e:
        # Handle specific errors
        return {"success": False, "error": str(e), "error_type": "ValueError"}
    except Exception as e:
        # Handle unexpected errors
        logging.exception("Unexpected error")
        return {"success": False, "error": "An unexpected error occurred"}
```

## Complete Example

Here's a complete example of a ServiceGroup with multiple operations:

```python
from typing import List, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import Context
from automcp import ServiceGroup, operation

class SearchRequest(BaseModel):
    """Schema for search operations."""
    query: str = Field(..., description="Search query string")
    max_results: int = Field(10, description="Maximum number of results to return")
    filter_by: Optional[str] = Field(None, description="Optional filter")

class SearchResult(BaseModel):
    """Schema for search results."""
    id: str
    title: str
    snippet: str
    relevance: float

class SearchGroup(ServiceGroup):
    """A service group for search operations."""
    
    def __init__(self):
        super().__init__()
        self.data = self._load_data()
    
    def _load_data(self):
        # Load sample data
        return {
            "1": {"title": "Introduction to AutoMCP", "content": "AutoMCP is a framework for..."},
            "2": {"title": "ServiceGroups in AutoMCP", "content": "ServiceGroups are the building blocks..."},
            # More data...
        }
    
    @operation(schema=SearchRequest)
    async def search(self, request: SearchRequest, ctx: Context) -> List[SearchResult]:
        """Search for documents matching a query.
        
        Args:
            request: The validated search request
            ctx: The context object for progress reporting
            
        Returns:
            A list of search results matching the query
        """
        await ctx.report_progress(0, 2)
        ctx.info(f"Searching for: {request.query}")
        
        # Simple search implementation
        results = []
        for id, doc in self.data.items():
            if request.query.lower() in doc["title"].lower() or request.query.lower() in doc["content"].lower():
                # Check filter if provided
                if request.filter_by and request.filter_by not in doc["title"]:
                    continue
                
                # Calculate simple relevance score
                relevance = 1.0
                if request.query.lower() in doc["title"].lower():
                    relevance = 1.5
                
                results.append(SearchResult(
                    id=id,
                    title=doc["title"],
                    snippet=doc["content"][:100] + "...",
                    relevance=relevance
                ))
                
                # Limit results
                if len(results) >= request.max_results:
                    break
        
        await ctx.report_progress(1, 2)
        ctx.info(f"Found {len(results)} results")
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance, reverse=True)
        
        await ctx.report_progress(2, 2)
        return results
    
    @operation()
    async def get_document(self, doc_id: str) -> Optional[dict]:
        """Retrieve a document by ID.
        
        Args:
            doc_id: The document ID
            
        Returns:
            The document if found, None otherwise
        """
        if doc_id in self.data:
            return {"id": doc_id, **self.data[doc_id]}
        return None
```

## Related Topics

- [ServiceGroup Reference](group.md)
- [Schemas](../core_concepts/schemas.md)
- [Context](../core_concepts/context.md)
```

## 7. Conclusion

This design outlines a comprehensive plan for resolving the broken links in the AutoMCP documentation. By creating these missing files with high-quality content, the documentation will become more complete, usable, and valuable to users of the framework.

The prioritization strategy ensures that the most important files are addressed first, while the content development guidelines and example content provide clear direction for implementation. Once implemented, the documentation verification script will confirm that all links are valid.