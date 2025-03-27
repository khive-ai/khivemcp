"""FastAPI server implementation."""

import asyncio
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from automcp.core.errors import OperationError
from automcp.schemas.base import (
    ExecutionRequest,
    ExecutionResponse,
    ServerInfo,
    TextContent,
)

app = FastAPI(
    title="AutoMCP API",
    description="HTTP/WebSocket API for AutoMCP servers",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server state
servers: Dict[str, ServerInfo] = {}
active_connections: List[WebSocket] = []


# Server management
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


@app.get("/servers/{server_id}")
async def get_server(server_id: str) -> ServerInfo:
    """Get server information."""
    if server_id not in servers:
        raise HTTPException(status_code=404, detail="Server not found")
    return servers[server_id]


@app.post("/servers/{server_id}/execute")
async def execute_operation(
    server_id: str,
    request: ExecutionRequest,
) -> ExecutionResponse:
    """Execute operation on server."""
    if server_id not in servers:
        raise HTTPException(status_code=404, detail="Server not found")

    server = servers[server_id]
    try:
        # Future: implement actual server communication
        return ExecutionResponse(
            content=TextContent(type="text", text="Operation executed")
        )
    except Exception as e:
        if isinstance(e, OperationError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoints
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for server updates."""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        active_connections.remove(websocket)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time(), "version": "1.0.0"}


# Utility functions
async def broadcast_server_update(server: ServerInfo):
    """Broadcast server status updates to all connected clients."""
    message = {"type": "server_update", "data": server.dict()}
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass  # Connection might be closed


# Background tasks
async def monitor_servers():
    """Background task to monitor server health."""
    while True:
        for server_id, server in servers.items():
            try:
                # Future: implement actual health check
                server.last_checked = time.time()
                await broadcast_server_update(server)
            except:
                pass
        await asyncio.sleep(30)  # Check every 30 seconds


@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    asyncio.create_task(monitor_servers())
