---
type: resource
title: "AutoMCP FastAPI Backend Implementation"
created: 2024-12-22 19:05 EST
updated: 2024-12-22 19:05 EST
status: active
tags: [resource, backend, fastapi, mcp]
aliases: [automcp-backend]
related: ["[[AutoMCP_Client_Implementation]]", "[[AutoMCP_Streamlit_Frontend]]"]
sources:
  - "FastAPI Docs: https://fastapi.tiangolo.com/"
  - "OpenRouter API: https://openrouter.ai/docs"
confidence: certain
---

# AutoMCP FastAPI Backend

## Core Architecture

### 1. Data Models
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum

class ServerStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ServerInfo(BaseModel):
    """Server information and status."""
    id: str
    name: str
    url: str
    status: ServerStatus
    last_checked: float
    capabilities: Dict[str, Any]
    latency_ms: Optional[float] = None

class ChatMessage(BaseModel):
    """Chat message structure."""
    role: str
    content: str
    name: Optional[str] = None

class ChatRequest(BaseModel):
    """Chat completion request."""
    messages: List[ChatMessage]
    model: str
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class ServerTestResult(BaseModel):
    """Server test results."""
    server_id: str
    success: bool
    latency_ms: float
    error_message: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
```

### 2. FastAPI Application

```python
from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import time

app = FastAPI(
    title="AutoMCP Backend",
    description="Backend server for AutoMCP system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server registry
servers: Dict[str, ServerInfo] = {}

# Active WebSocket connections
active_connections: List[WebSocket] = []
```

### 3. Server Management Routes

```python
@app.post("/servers/register")
async def register_server(server: ServerInfo):
    """Register a new MCP server."""
    servers[server.id] = server
    await broadcast_server_update(server)
    return {"status": "success", "server_id": server.id}

@app.get("/servers")
async def list_servers() -> List[ServerInfo]:
    """Get list of all registered servers."""
    return list(servers.values())

@app.get("/servers/{server_id}/status")
async def get_server_status(server_id: str) -> ServerInfo:
    """Get status of specific server."""
    if server_id not in servers:
        raise HTTPException(status_code=404, detail="Server not found")
    return servers[server_id]

@app.post("/servers/{server_id}/test")
async def test_server(server_id: str) -> ServerTestResult:
    """Test server connectivity and capabilities."""
    if server_id not in servers:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = servers[server_id]
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{server.url}/health",
                timeout=5.0
            )
            
        latency = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            capabilities = response.json().get("capabilities", {})
            servers[server_id].latency_ms = latency
            servers[server_id].status = ServerStatus.HEALTHY
            
            return ServerTestResult(
                server_id=server_id,
                success=True,
                latency_ms=latency,
                capabilities=capabilities
            )
        else:
            servers[server_id].status = ServerStatus.DEGRADED
            return ServerTestResult(
                server_id=server_id,
                success=False,
                latency_ms=latency,
                error_message=f"Server returned status {response.status_code}"
            )
            
    except Exception as e:
        servers[server_id].status = ServerStatus.UNHEALTHY
        return ServerTestResult(
            server_id=server_id,
            success=False,
            latency_ms=-1,
            error_message=str(e)
        )
```

### 4. Chat Interface Routes

```python
@app.post("/chat/models")
async def list_available_models():
    """Get list of available models from OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}"
            }
        )
        return response.json()

@app.websocket("/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for chat interactions."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            request = ChatRequest(**data)
            
            # Handle streaming
            if request.stream:
                async for chunk in stream_chat_response(request):
                    await websocket.send_json(chunk)
            else:
                response = await get_chat_response(request)
                await websocket.send_json(response)
                
    except Exception as e:
        await websocket.send_json({
            "error": str(e)
        })
    finally:
        active_connections.remove(websocket)
        await websocket.close()

async def stream_chat_response(request: ChatRequest):
    """Stream chat response from OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:8501",
            },
            json={
                "model": request.model,
                "messages": [m.dict() for m in request.messages],
                "stream": True,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            },
            stream=True
        )
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                chunk = json.loads(line[6:])
                yield chunk

async def get_chat_response(request: ChatRequest):
    """Get complete chat response from OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:8501",
            },
            json={
                "model": request.model,
                "messages": [m.dict() for m in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        return response.json()
```

### 5. WebSocket Notifications

```python
async def broadcast_server_update(server: ServerInfo):
    """Broadcast server status updates to all connected clients."""
    message = {
        "type": "server_update",
        "data": server.dict()
    }
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass  # Connection might be closed

async def monitor_servers():
    """Background task to monitor server health."""
    while True:
        for server_id in servers:
            result = await test_server(server_id)
            if result.success:
                await broadcast_server_update(servers[server_id])
        await asyncio.sleep(30)  # Check every 30 seconds

@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup."""
    asyncio.create_task(monitor_servers())
```

## Deployment Configuration

### 1. Docker Setup

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose

```yaml
version: "3.8"
services:
  automcp-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - ENVIRONMENT=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Best Practices

1. **Error Handling**
   - Use specific exception types
   - Provide clear error messages
   - Handle websocket disconnections
   - Log errors appropriately

2. **Performance**
   - Use connection pooling
   - Implement caching where appropriate
   - Monitor resource usage
   - Handle backpressure

3. **Security**
   - Validate all inputs
   - Sanitize outputs
   - Use proper authentication
   - Rate limit requests

4. **Monitoring**
   - Track server health
   - Monitor latencies
   - Log important events
   - Set up alerts

## Related Concepts
- [[WebSocket Implementation]]
- [[FastAPI Deployment]]
- [[Server Monitoring]]