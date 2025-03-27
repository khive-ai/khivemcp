---
type: resource
title: "AutoMCP Configuration Guide"
created: 2024-12-22 18:46 EST
updated: 2024-12-22 18:46 EST
status: active
tags: [resource, guide, configuration, mcp]
aliases: [automcp-config]
related: ["[[Project_AutoMCP]]", "[[AutoMCP_Server_Guide]]"]
sources:
  - "GitHub: https://github.com/ohdearquant/automcp/blob/main/pyproject.toml"
  - "GitHub: https://github.com/ohdearquant/automcp"
confidence: certain
---

# AutoMCP Configuration Guide

## Installation

### Requirements
- Python ≥3.10
- Dependencies:
  - mcp ≥1.1.0
  - pydantic ≥2.0.0
  - typer ≥0.15.1

### Install Steps
```bash
# Using pip
pip install automcp

# For development
pip install automcp[dev]
```

## Configuration Formats

### 1. Service Configuration (YAML)

This is the primary configuration format for services with multiple groups:

```yaml
# service.yaml
name: complex-service
description: "A service with multiple groups"

# Shared packages across all groups
packages:
  - numpy
  - pandas

# Shared environment variables
env_vars:
  LOG_LEVEL: INFO
  DEBUG: false

# Group configurations
groups:
  # Group 1: Math Operations
  "math.groups:MathGroup":
    name: math-ops
    description: "Mathematical operations"
    config:
      precision: 4
      max_value: 1000
    packages:
      - scipy  # Group-specific package

  # Group 2: Data Processing
  "data.groups:ProcessingGroup":
    name: data-ops
    description: "Data processing operations"
    config:
      batch_size: 100
      timeout: 30
    env_vars:
      CACHE_DIR: /tmp/cache  # Group-specific env var
```

### 2. Single Group Configuration (JSON)

For simpler services with just one group:

```json
{
  "name": "simple-group",
  "description": "Single group service",
  "packages": ["numpy"],
  "config": {
    "setting1": "value1",
    "setting2": "value2"
  },
  "env_vars": {
    "ENV_VAR1": "value1"
  }
}
```

## Configuration Schema

### 1. Service Configuration

```python
class ServiceConfig(BaseModel):
    name: str
    description: str | None = None
    groups: dict[str, GroupConfig]
    packages: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)
```

### 2. Group Configuration

```python
class GroupConfig(BaseModel):
    name: str
    description: str | None = None
    packages: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    env_vars: dict[str, str] = Field(default_factory=dict)
```

## Environment Variables

### 1. System Environment Variables
```bash
# Service configuration
AUTOMCP_CONFIG_DIR=/etc/automcp
AUTOMCP_LOG_LEVEL=INFO

# Timeouts
AUTOMCP_OPERATION_TIMEOUT=30
AUTOMCP_CONNECTION_TIMEOUT=5

# Resource limits
AUTOMCP_MAX_WORKERS=4
AUTOMCP_MAX_MEMORY=1024  # MB
```

### 2. Group-Specific Variables
Specified in configuration:
```yaml
groups:
  "my.group:MyGroup":
    env_vars:
      GROUP_SETTING: value
      CACHE_DIR: /path/to/cache
```

## Advanced Configuration

### 1. Dynamic Group Loading

Groups can be loaded dynamically based on their module path:

```yaml
groups:
  "mypackage.groups.math:MathGroup":
    name: math-ops
    config: {}
```

The server will:
1. Import `mypackage.groups.math`
2. Get `MathGroup` class
3. Initialize with config

### 2. Configuration Inheritance

You can create base configurations and extend them:

```yaml
# base.yaml
name: base-service
packages:
  - base-package

# service.yaml
extends: base.yaml
name: extended-service
packages:
  - extra-package
```

### 3. Resource Configuration

Configure resource limits and paths:

```yaml
name: resource-service
config:
  paths:
    data: /var/lib/automcp/data
    cache: /var/cache/automcp
    temp: /tmp/automcp
  limits:
    max_file_size: 100MB
    max_memory: 1GB
    max_processes: 4
```

## Development Configuration

### 1. Development Settings

For local development:

```yaml
name: dev-service
description: "Development configuration"

env_vars:
  ENV: development
  DEBUG: true
  LOG_LEVEL: DEBUG

config:
  hot_reload: true
  auto_restart: true
  watch_paths:
    - src/
    - config/
```

### 2. Testing Configuration

For testing environments:

```yaml
name: test-service
description: "Test configuration"

env_vars:
  ENV: testing
  TEST_DB: sqlite:///:memory:

config:
  mock_external: true
  test_timeout: 30
```

## Security Configuration

### 1. Authentication Settings

```yaml
name: secure-service
security:
  auth:
    type: bearer
    token_expiry: 3600
    refresh_enabled: true
  tls:
    enabled: true
    cert_file: /etc/automcp/cert.pem
    key_file: /etc/automcp/key.pem
```

### 2. Permission Configuration

```yaml
groups:
  "secure.group:SecureGroup":
    permissions:
      read:
        - /data/public/*
      write:
        - /data/private/{user}/*
    roles:
      admin:
        - ALL
      user:
        - read
        - write_own
```

## Monitoring Configuration

### 1. Metrics Settings

```yaml
name: monitored-service
monitoring:
  metrics:
    enabled: true
    port: 9090
    path: /metrics
  health:
    enabled: true
    path: /health
    checks:
      - database
      - cache
      - external_api
```

### 2. Logging Configuration

```yaml
logging:
  level: INFO
  format: json
  outputs:
    - type: file
      path: /var/log/automcp/service.log
      rotation: 1d
    - type: syslog
      facility: local0
  traces:
    enabled: true
    exporter: jaeger
```

## Best Practices

1. **Configuration Organization**
   - Use clear group names
   - Organize by functionality
   - Keep configurations DRY
   - Document non-obvious settings

2. **Environment Variables**
   - Use for secrets
   - Use for deployment-specific values
   - Prefix all variables
   - Document required variables

3. **Resource Management**
   - Set reasonable limits
   - Configure timeouts
   - Plan for scaling
   - Monitor resource usage

4. **Security**
   - Encrypt sensitive values
   - Use secure defaults
   - Restrict permissions
   - Enable audit logging

5. **Development**
   - Use separate dev configs
   - Enable debugging
   - Configure hot reload
   - Set up test data

## Related Concepts
- [[AutoMCP Server Guide]]
- [[Configuration Management]]
- [[Security Best Practices]]
