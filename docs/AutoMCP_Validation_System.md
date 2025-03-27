---
type: resource
title: "AutoMCP Validation System"
created: 2024-12-22 18:46 EST
updated: 2024-12-22 18:46 EST
status: active
tags: [resource, mcp, validation, python]
aliases: [automcp-validation]
related: ["[[Project_AutoMCP]]", "[[AutoMCP_Core_Implementation]]"]
sources:
  - "GitHub: https://github.com/ohdearquant/automcp"
confidence: probable
---

# AutoMCP Validation System

## Overview

AutoMCP implements a comprehensive validation system built on Pydantic that ensures:
- Type safety at runtime
- Schema validation for operations
- Configuration validation
- Response format validation

## Input Validation

### Schema Definition
```python
from pydantic import BaseModel, Field

class ServiceInput(BaseModel):
    name: str = Field(..., description="Service name")
    options: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = Field(default=30, gt=0)
```

### Usage in Operations
```python
@operation(schema=ServiceInput)
async def process(self, input: ServiceInput) -> ExecutionResponse:
    # Input is already validated by this point
    result = await self._process(
        name=input.name,
        options=input.options,
        timeout=input.timeout
    )
```

## Configuration Validation

### 1. Service Configuration
```yaml
name: example-service
description: Service description
groups:
  "module:ServiceGroup":
    name: group-name
    config:
      retry_count: 3
      timeout: 30
```

### 2. Configuration Schema
```python
class GroupConfig(BaseModel):
    retry_count: int = Field(default=3, ge=0)
    timeout: int = Field(default=30, gt=0)
    
class ServiceConfig(BaseModel):
    name: str
    description: str
    groups: Dict[str, GroupConfig]
```

## Response Validation

### 1. Response Types
```python
class ExecutionResponse(BaseModel):
    content: Union[TextContent, BinaryContent]
    metadata: Optional[Dict[str, Any]] = None
    
class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str
    
class BinaryContent(BaseModel):
    type: Literal["binary"] = "binary"
    data: bytes
```

### 2. Response Generation
```python
def create_text_response(text: str) -> ExecutionResponse:
    return ExecutionResponse(
        content=TextContent(text=text)
    )
```

## Validation Pipeline

### 1. Input Stage
```python
async def validate_input(self, schema: Type[BaseModel], data: Dict[str, Any]) -> BaseModel:
    try:
        return schema(**data)
    except ValidationError as e:
        raise InputValidationError(str(e))
```

### 2. Operation Stage
```python
async def execute_operation(self, operation: Callable, input: BaseModel) -> Any:
    try:
        return await operation(input)
    except Exception as e:
        raise OperationError(str(e))
```

### 3. Response Stage
```python
async def validate_response(self, response: Any) -> ExecutionResponse:
    try:
        if isinstance(response, ExecutionResponse):
            return response
        return create_text_response(str(response))
    except ValidationError as e:
        raise ResponseValidationError(str(e))
```

## Error Handling

### 1. Validation Errors
```python
class ValidationError(Exception):
    def __init__(self, message: str, details: Dict[str, Any]):
        self.details = details
        super().__init__(message)

class InputValidationError(ValidationError):
    pass

class ConfigValidationError(ValidationError):
    pass

class ResponseValidationError(ValidationError):
    pass
```

### 2. Error Recovery
```python
async def execute_with_validation(self, operation: Callable, data: Dict[str, Any]) -> ExecutionResponse:
    try:
        # Input validation
        input = await self.validate_input(operation.schema, data)
        
        # Operation execution
        result = await self.execute_operation(operation, input)
        
        # Response validation
        return await self.validate_response(result)
    except ValidationError as e:
        # Handle validation errors
        self.handle_validation_error(e)
```

## Best Practices

1. **Schema Design**
   - Use descriptive field names
   - Include field descriptions
   - Set appropriate constraints
   - Define clear types

2. **Validation Strategy**
   - Validate early
   - Fail fast
   - Provide clear error messages
   - Handle edge cases

3. **Error Management**
   - Use specific error types
   - Include validation context
   - Implement recovery methods
   - Log validation failures

4. **Performance Considerations**
   - Cache validated schemas
   - Use reasonable constraints
   - Optimize for common cases
   - Handle validation async

## Testing

### 1. Schema Testing
```python
def test_input_schema():
    valid_input = {
        "name": "test",
        "timeout": 30
    }
    schema = ServiceInput(**valid_input)
    assert schema.name == "test"
    assert schema.timeout == 30
```

### 2. Validation Testing
```python
async def test_input_validation():
    invalid_input = {
        "name": "",  # Empty string
        "timeout": -1  # Negative timeout
    }
    with pytest.raises(ValidationError):
        await service.validate_input(ServiceInput, invalid_input)
```

## Integration Examples

### 1. With HTTP Routes
```python
@router.post("/process")
async def process_request(data: Dict[str, Any]):
    try:
        input = await validate_input(ServiceInput, data)
        result = await service.process(input)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 2. With Event Handlers
```python
async def handle_event(event: Dict[str, Any]):
    try:
        input = await validate_input(EventInput, event)
        await event_handler.process(input)
    except ValidationError as e:
        await error_handler.handle(e)
```

## Related Concepts
- [[Pydantic Best Practices]]
- [[Type Safety Patterns]]
- [[Validation Strategies]]
