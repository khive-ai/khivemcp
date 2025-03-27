---
type: resource
title: "AutoMCP Usage Guide"
created: 2024-12-22 19:05 EST
updated: 2024-12-22 19:05 EST
status: active
tags: [resource, guide, mcp, usage]
aliases: [automcp-usage]
related: ["[[AutoMCP_FastAPI_Backend]]", "[[AutoMCP_Enhanced_Frontend]]"]
sources: []
confidence: certain
---

# AutoMCP Usage Guide

## System Overview

### Architecture Components
1. **FastAPI Backend**
   - Manages MCP server connections
   - Handles WebSocket communication
   - Integrates with OpenRouter
   - Provides server monitoring

2. **Streamlit Frontend**
   - Server management dashboard
   - Interactive chat interface
   - Real-time status monitoring
   - Configuration management

3. **MCP Servers**
   - Individual MCP protocol servers
   - Provide various capabilities
   - Expose resources and tools
   - Handle specific operations

## Installation Guide

### 1. Backend Setup
```bash
# Clone repository
git clone https://github.com/yourusername/automcp
cd automcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export OPENROUTER_API_KEY="your-api-key"
export ENVIRONMENT="development"

# Run backend
uvicorn main:app --reload
```

### 2. Frontend Setup
```bash
# Install frontend dependencies
cd frontend
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py
```

### 3. Docker Deployment
```bash
# Build and run with docker-compose
docker-compose up --build
```

## Configuration Guide

### 1. Backend Configuration

#### Environment Variables
```bash
OPENROUTER_API_KEY=your-api-key
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_CONNECTIONS=100
```

#### Server Registry Setup
1. Create server configuration file:
```yaml
# servers.yaml
servers:
  - id: "server1"
    name: "Document Server"
    url: "http://localhost:8001"
    capabilities:
      - resources
      - tools
  
  - id: "server2"
    name: "Code Analysis Server"
    url: "http://localhost:8002"
    capabilities:
      - code_analysis
      - git_integration
```

2. Register servers through API:
```python
import httpx
import yaml

with open('servers.yaml') as f:
    config = yaml.safe_load(f)

for server in config['servers']:
    response = httpx.post(
        'http://localhost:8000/servers/register',
        json=server
    )
    print(f"Registered {server['name']}: {response.status_code}")
```

### 2. Frontend Configuration

#### Application Settings
1. Navigate to Settings page
2. Configure:
   - Backend URL
   - OpenRouter API key
   - Connection parameters
   - UI preferences

#### Model Configuration
1. In Chat Interface:
   - Select preferred model
   - Adjust parameters:
     - Temperature
     - Max tokens
     - Other model-specific settings

## Usage Guide

### 1. Server Management

#### Monitoring Servers
1. Open Server Dashboard
2. View server status overview:
   - Healthy count
   - Degraded count
   - Unhealthy count

#### Testing Connections
1. Expand server details
2. Click "Test Connection"
3. Review:
   - Connection status
   - Latency
   - Available capabilities

#### Debugging Servers
1. Check server logs:
```bash
# Backend logs
docker-compose logs -f backend

# Server logs
docker-compose logs -f server1
```

2. Review connection metrics:
   - Response times
   - Error rates
   - Request counts

### 2. Chat Interface Usage

#### Starting a Conversation
1. Select desired model:
   - Choose from OpenRouter models
   - Configure parameters

2. Enter prompt:
   - Type message in chat input
   - View streaming response
   - Check message history

#### Using MCP Capabilities
1. Access server resources:
```python
# Example: Using document server
message = "Analyze document: file://docs/report.pdf"
# System will automatically route to appropriate server
```

2. Execute server tools:
```python
# Example: Using code analysis
message = "Analyze code quality in src/main.py"
# System routes to code analysis server
```

### 3. Advanced Features

#### Custom Server Integration
1. Create server implementation:
```python
from automcp import ServiceGroup, operation
from pydantic import BaseModel

class CustomInput(BaseModel):
    parameter: str

class CustomGroup(ServiceGroup):
    @operation(schema=CustomInput)
    async def custom_operation(self, input: CustomInput):
        # Implementation
        return ExecutionResponse(...)
```

2. Register with system:
```python
server_config = {
    "id": "custom-server",
    "name": "Custom Implementation",
    "url": "http://localhost:8003",
    "capabilities": ["custom_operation"]
}

response = httpx.post(
    'http://localhost:8000/servers/register',
    json=server_config
)
```

## Troubleshooting Guide

### Common Issues

#### 1. Connection Problems
```python
# Test backend connectivity
response = httpx.get('http://localhost:8000/health')
print(f"Backend Status: {response.status_code}")

# Test server connectivity
response = httpx.get('http://localhost:8001/health')
print(f"Server Status: {response.status_code}")
```

#### 2. WebSocket Issues
- Check WebSocket connection in browser console
- Verify WebSocket URLs
- Review connection logs

#### 3. Model Errors
- Verify OpenRouter API key
- Check model availability
- Review parameter settings

### Recovery Steps

1. **Server Recovery**
   ```bash
   # Restart services
   docker-compose restart
   
   # Check logs
   docker-compose logs --tail=100
   ```

2. **State Reset**
   ```python
   # Clear session state
   st.session_state.clear()
   
   # Reinitialize connections
   init_websocket()
   ```

3. **Configuration Reset**
   - Reset to default settings
   - Retest connections
   - Verify environment variables

## Best Practices

1. **Regular Maintenance**
   - Monitor server health
   - Review error logs
   - Update configurations
   - Test connections

2. **Security**
   - Rotate API keys
   - Monitor access logs
   - Update dependencies
   - Review permissions

3. **Performance**
   - Monitor resource usage
   - Optimize configurations
   - Cache when possible
   - Clean up resources

## Related Documentation
- [[AutoMCP Architecture]]
- [[Deployment Guide]]
- [[Security Guidelines]]