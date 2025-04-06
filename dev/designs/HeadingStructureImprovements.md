# Heading Structure Improvements Design

## Overview

This document provides a detailed design for fixing the heading level jumps identified in three documentation files: `specifications.md`, `service_groups.md`, and `configuration.md`. Proper heading structure is essential for progressive disclosure and readability of documentation.

## 1. Issue Analysis

The verification report identified heading level jumps in three files:

1. **`docs/specifications.md`**: Jump from level 1 (H1) to level 3 (H3)
2. **`docs/core_concepts/service_groups.md`**: Multiple jumps from level 1 (H1) to level 3 (H3)
3. **`docs/getting_started/configuration.md`**: Multiple jumps from level 1 (H1) to level 3 (H3)

These heading level jumps violate the principle of progressive disclosure, where content should be organized in a hierarchical structure with no skipped levels. This makes the documentation harder to navigate and understand.

## 2. Progressive Disclosure Principles

Before outlining the specific changes, let's establish the principles for proper heading structure:

1. **Hierarchical Organization**: Content should be organized in a clear hierarchy from most general (H1) to most specific (H3, H4, etc.).
2. **No Skipped Levels**: Heading levels should not skip (e.g., from H1 to H3 without an H2 in between).
3. **Logical Grouping**: H2 headings should group related H3 headings.
4. **Single H1**: Each document should have only one H1 heading, which is the title of the document.
5. **Balance**: The structure should be balanced, with each level containing a reasonable number of sections.

## 3. Detailed Improvement Plans

### 3.1 specifications.md

#### Current Structure (Problematic)

```markdown
# Specifications

Content...

### Subsection 1

Content...

### Subsection 2

Content...
```

#### Redesigned Structure

```markdown
# Specifications

Introductory content...

## Overview

General specifications overview...

### Subsection 1

Content...

### Subsection 2

Content...

## Detailed Specifications

More detailed specifications...

### Another Subsection

Content...

### Final Subsection

Content...
```

#### Implementation Approach

1. Analyze the current content to identify logical groupings for H2 headings
2. Introduce appropriate H2 headings between the H1 and existing H3 headings
3. Reorganize content if necessary to maintain logical flow
4. Ensure all H3 headings are properly nested under relevant H2 headings

### 3.2 service_groups.md

#### Current Structure Analysis

The current `service_groups.md` file has these heading level jumps:

- H1: Service Groups
- (Content about what a ServiceGroup is)
- H3: 1. Automatic Operation Registration
- H3: 2. Operation Namespacing
- H3: 3. Group Configuration
- H3: 4. Stateful Services

There are also other sections without proper hierarchical organization.

#### Redesigned Structure

```markdown
# Service Groups

Introductory content about service groups...

## What is a ServiceGroup?

Content explaining the basic concept...

## Creating a ServiceGroup

Content about how to create a service group...

## Key Characteristics

Overview of key characteristics...

### 1. Automatic Operation Registration

Content about automatic registration...

### 2. Operation Namespacing

Content about namespacing...

### 3. Group Configuration

Content about configuration...

### 4. Stateful Services

Content about stateful services...

## Advanced ServiceGroup Patterns

Overview of advanced patterns...

### Composition

Content about composition...

### Resource Management

Content about resource management...

## Best Practices

Content about best practices...

## Related Concepts

Links to related concepts...
```

#### Implementation Approach

1. Add the missing H2 "Key Characteristics" heading to group the numbered H3 sections
2. Ensure the "Advanced ServiceGroup Patterns" section is properly marked as H2
3. Promote "Best Practices" and "Related Concepts" to H2 level if they are currently H3
4. Review the content flow to ensure logical progression

### 3.3 configuration.md

#### Current Structure Analysis

The `configuration.md` file has these heading level jumps:

- H1: Configuration Guide
- (Introductory content)
- H3: Key Components (under Service Configuration)
- Other H3 headings without proper H2 parents

#### Redesigned Structure

```markdown
# Configuration Guide

Introductory content...

## Configuration Overview

General overview of configuration approaches...

## Service Configuration

Content about service configuration...

### Key Components

Details about key components...

## Group Configuration

Content about group configuration...

## Configuration Format

Overview of supported formats...

### YAML Example

YAML example...

### JSON Example

JSON example...

## Loading Configuration

Methods for loading configuration...

### From File

Loading from file...

### Direct Creation

Creating config directly...

## Custom Group Configuration

Content about custom configuration...

## Environment Variables

Content about environment variables...

## Configuration Best Practices

Content about best practices...

## Related Topics

Links to related topics...
```

#### Implementation Approach

1. Ensure all H3 headings are properly nested under relevant H2 headings
2. Add missing H2 headings where necessary to group related H3 sections
3. Review the organization of examples to ensure they're properly nested
4. Maintain the logical flow of content while fixing the heading structure

## 4. General Implementation Guidelines

When implementing these changes, follow these guidelines:

1. **Preserve Content**: Don't remove or substantially alter the existing content
2. **Maintain Flow**: Ensure the logical flow of information is preserved
3. **Consistent Style**: Keep the style and tone consistent throughout the document
4. **Update Cross-References**: If any cross-references use heading anchors, update them
5. **Add Transitions**: Where necessary, add brief transition sentences between newly created sections

## 5. Example Implementation: service_groups.md

Here's a detailed example of how `service_groups.md` should be restructured:

```markdown
# Service Groups

Service Groups are the fundamental building blocks of AutoMCP applications. They provide a way to organize related operations into logical units.

## What is a ServiceGroup?

A `ServiceGroup` is a Python class that:

1. Inherits from `automcp.ServiceGroup`
2. Contains methods decorated with `@operation`
3. Automatically registers these methods as callable operations

ServiceGroups help you organize your code into cohesive, focused components that can be composed together to form a complete MCP server.

## Creating a ServiceGroup

Here's a basic example of creating a ServiceGroup:

```python
from automcp import ServiceGroup, operation

class CalculatorGroup(ServiceGroup):
    """A group providing basic calculator operations."""
    
    @operation()
    async def add(self, a: float, b: float) -> float:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            The sum of a and b
        """
        return a + b
    
    @operation()
    async def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            The product of a and b
        """
        return a * b
```

## Key Characteristics

ServiceGroups have several important characteristics that make them powerful building blocks for your MCP server.

### 1. Automatic Operation Registration

When you instantiate a ServiceGroup, it automatically discovers and registers any methods decorated with `@operation`. Each operation becomes available to be called through the MCP protocol.

```python
# Operations are automatically registered
calculator = CalculatorGroup()
print(calculator.registry)  # Shows registered operations
```

### 2. Operation Namespacing

Each operation is namespaced by its group name when exposed through an MCP server. For example, if your `CalculatorGroup` is registered as "math", the operations would be accessible as:

- `math.add`
- `math.multiply`

This namespacing helps organize operations and avoid name conflicts.

### 3. Group Configuration

Each ServiceGroup can have its own configuration options that customize its behavior. These are specified in the server configuration:

```yaml
# config.yaml
name: calculator-service
groups:
  my_module:CalculatorGroup:
    name: math
    config:
      precision: 2
      max_value: 1000
```

You can access this configuration in your ServiceGroup using the `self.config` attribute.

### 4. Stateful Services

ServiceGroups can maintain state between operation calls, which is useful for caching, connection pooling, or managing shared resources.

```python
class DatabaseGroup(ServiceGroup):
    def __init__(self):
        super().__init__()
        self.connections = {}  # State maintained across operations
    
    @operation()
    async def query(self, database: str, sql: str) -> list:
        # Use and manage connections
        if database not in self.connections:
            self.connections[database] = create_connection(database)
        return await self.connections[database].execute(sql)
```

## Advanced ServiceGroup Patterns

ServiceGroups can be combined and extended in various ways to create powerful patterns.

### Composition

You can create hierarchical service structures by having one ServiceGroup use another:

```python
class AdvancedMathGroup(ServiceGroup):
    def __init__(self):
        super().__init__()
        self.calculator = CalculatorGroup()
    
    @operation()
    async def square(self, x: float) -> float:
        """Square a number using the calculator group."""
        return await self.calculator.multiply(x, x)
```

### Resource Management

ServiceGroups can manage resources like database connections, file handles, or external API clients:

```python
class FileGroup(ServiceGroup):
    def __init__(self):
        super().__init__()
        self.open_files = {}
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when the server shuts down."""
        for file in self.open_files.values():
            file.close()
```

## Best Practices

1. **Single Responsibility**: Each ServiceGroup should have a clear, focused purpose.
2. **Logical Grouping**: Group operations that work with the same data or provide related functionality.
3. **Descriptive Naming**: Use clear, descriptive names for both groups and operations.
4. **Thorough Documentation**: Document the purpose of each group and operation with docstrings.
5. **Error Handling**: Implement proper error handling within operations.

## Related Concepts

- [Operations](operations.md): Learn how to define and customize operations within ServiceGroups.
- [Schemas](schemas.md): Understand how to validate operation inputs using Pydantic schemas.
- [Context](context.md): Learn about the context object for logging and progress reporting.
```

## 6. Testing and Verification

After implementing these changes:

1. Run the documentation verification script:
   ```
   python verification/check_docs_structure.py
   ```

2. Verify that no heading level jumps are reported

3. Manually review the modified documentation to ensure:
   - The content flow is logical
   - The relationships between sections are clear
   - The documentation is still accurate and readable

## 7. Conclusion

Fixing the heading structure issues in these three files will improve the readability and navigability of the AutoMCP documentation. This design provides a detailed plan for restructuring each file to follow progressive disclosure principles while maintaining the quality and accuracy of the content.