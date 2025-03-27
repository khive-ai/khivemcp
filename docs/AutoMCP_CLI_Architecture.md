---
type: resource
title: "AutoMCP CLI and Server Architecture"
created: 2024-12-22 18:46 EST
updated: 2024-12-22 18:46 EST
status: active
tags: [resource, architecture, mcp, cli]
aliases: [automcp-cli]
related: ["[[Project_AutoMCP]]", "[[AutoMCP_Core_Implementation]]"]
sources:
  - "GitHub: https://github.com/ohdearquant/automcp/blob/main/automcp/cli.py"
  - "GitHub: https://github.com/ohdearquant/automcp/blob/main/automcp/server.py"
confidence: certain
---

# AutoMCP CLI and Server Architecture

## CLI Structure

The CLI is built using Typer and provides a streamlined interface for server deployment:

```python
app = typer.Typer(
    name="automcp",
    help="AutoMCP server deployment tools",
    add_completion=False,
    no_args_is_help=True,
)
```

### Configuration Loading

```python
def load_config(path: Path) -> ServiceConfig | GroupConfig:
    """Load configuration from file."""
    if path.suffix in [".yaml", ".yml"]:
        with open(path) as f:
            data = yaml.safe_load(f)
        return ServiceConfig(**data)
    else:
        with open(path) as f:
            data = json.load(f)
        return GroupConfig(**data)
```

Key features:
- Supports both YAML and JSON formats
- Validates against ServiceConfig or GroupConfig schemas
- Provides clear error messages on load failure

## Server Implementation

The AutoMCP server (`AutoMCPServer`) implements the Model Context Protocol:

```python
class AutoMCPServer:
    def __init__(
        self,
        name: str,
        config: ServiceConfig | GroupConfig,
        timeout: float = 30.0,
    ):
        self.name = name
        self.config = config
        self.timeout = timeout
        self.server = Server(name)
        self.groups: dict[str, ServiceGroup] = {}
```

### Group Initialization

1. **Service Groups**:
```python
def _init_service_groups(self) -> None:
    for class_path, group_config in self.config.groups.items():
        module_path, class_name = class_path.split(":")
        module = __import__(module_path, fromlist=[class_name])
        group_cls = getattr(module, class_name)
        group = group_cls()
        group.config = group_config
        self.groups[group_config.name] = group
```

2. **Single Group**:
```python
def _init_single_group(self) -> None:
    group = ServiceGroup()
    group.config = self.config
    self.groups[self.config.name] = group
```

## Protocol Handlers

### Tool Listing
```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    tools = []
    for group in self.groups.values():
        for op_name, operation in group.registry.items():
            tools.append(
                types.Tool(
                    name=f"{group.config.name}.{op_name}",
                    description=operation.doc,
                    inputSchema=operation.schema.model_json_schema()
                )
            )
    return tools
```

### Tool Execution
```python
@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict | None = None
) -> list[types.TextContent]:
    group_name, op_name = name.split(".", 1)
    request = ServiceRequest(
        requests=[ExecutionRequest(
            operation=op_name, 
            arguments=arguments
        )]
    )
    response = await self._handle_service_request(
        group_name, 
        request
    )
    return [response.content]
```

## Request Processing

### Service Request Handler
```python
async def _handle_service_request(
    self, 
    group_name: str, 
    request: ServiceRequest
) -> ServiceResponse:
    group = self.groups.get(group_name)
    if not group:
        return ServiceResponse(
            content=types.TextContent(
                type="text",
                text=f"Group not found: {group_name}"
            ),
            errors=[f"Group not found: {group_name}"]
        )
    
    tasks = [group.execute(req) for req in request.requests]
    responses = await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True),
        timeout=self.timeout
    )
```

## Error Handling

1. **Configuration Errors**:
```python
try:
    cfg = load_config(config_path)
except Exception as e:
    typer.echo(f"Failed to load config: {e}")
    raise typer.Exit(1)
```

2. **Runtime Errors**:
```python
try:
    async with server:
        await server.start()
except Exception as e:
    typer.echo(f"Server error: {e}")
    raise typer.Exit(1)
```

## Command Line Interface

### Run Command
```python
@app.command()
def run(
    config: Annotated[Path, typer.Argument()],
    group: Annotated[str | None, typer.Option()] = None,
    timeout: Annotated[float, typer.Option()] = 30.0,
) -> None:
    """Run AutoMCP server."""
    config_path = Path(config).resolve()
    cfg = load_config(config_path)
    
    if isinstance(cfg, ServiceConfig) and group:
        if group not in cfg.groups:
            typer.echo(f"Group {group} not found in config")
            raise typer.Exit(1)
        cfg = cfg.groups[group]
```

## Configuration Models

### Service Configuration
```python
class ServiceConfig(BaseModel):
    name: str
    description: str | None
    groups: dict[str, GroupConfig]
    packages: list[str] = []
    env_vars: dict[str, str] = {}
```

### Group Configuration
```python
class GroupConfig(BaseModel):
    name: str
    description: str | None
    packages: list[str] = []
    config: dict[str, Any] = {}
    env_vars: dict[str, str] = {}
```

## Best Practices

1. **Configuration Management**
   - Use YAML for service configs
   - Use JSON for single group configs
   - Validate all inputs
   - Handle missing files gracefully

2. **Error Handling**
   - Provide clear error messages
   - Exit with appropriate codes
   - Handle timeouts properly
   - Log all failures

3. **Resource Management**
   - Use async context managers
   - Clean up resources properly
   - Handle interrupts gracefully
   - Monitor timeouts

4. **Security Considerations**
   - Validate config paths
   - Check file permissions
   - Sanitize group names
   - Monitor resource usage

## Related Patterns
- [[CLI Design Patterns]]
- [[Async Service Architecture]]
- [[Configuration Management]]
