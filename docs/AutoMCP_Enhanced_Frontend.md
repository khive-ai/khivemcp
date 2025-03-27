---
type: resource
title: "AutoMCP Enhanced Streamlit Frontend"
created: 2024-12-22 19:05 EST
updated: 2024-12-22 19:05 EST
status: active
tags: [resource, frontend, streamlit, mcp]
aliases: [automcp-enhanced-frontend]
related: ["[[AutoMCP_FastAPI_Backend]]", "[[AutoMCP_Client_Implementation]]"]
sources: 
  - "Streamlit Docs: https://docs.streamlit.io/"
  - "OpenRouter API: https://openrouter.ai/docs"
confidence: certain
---

# AutoMCP Enhanced Streamlit Frontend

## Application Structure

### 1. Core Setup
```python
import streamlit as st
import asyncio
import websockets
import json
from datetime import datetime
import httpx

from automcp.client import AutoMCPClient, ClientConfig
from automcp.types import ServerInfo, ChatMessage, ServerStatus

# Page configuration
st.set_page_config(
    page_title="AutoMCP Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'servers' not in st.session_state:
    st.session_state.servers = {}
if 'ws_connection' not in st.session_state:
    st.session_state.ws_connection = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None
```

### 2. Server Management Interface

```python
def show_server_dashboard():
    st.header("MCP Server Management")
    
    # Server status overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        healthy_count = sum(
            1 for s in st.session_state.servers.values()
            if s.status == ServerStatus.HEALTHY
        )
        st.metric("Healthy Servers", healthy_count)
    
    with col2:
        degraded_count = sum(
            1 for s in st.session_state.servers.values()
            if s.status == ServerStatus.DEGRADED
        )
        st.metric("Degraded Servers", degraded_count)
    
    with col3:
        unhealthy_count = sum(
            1 for s in st.session_state.servers.values()
            if s.status == ServerStatus.UNHEALTHY
        )
        st.metric("Unhealthy Servers", unhealthy_count)
    
    # Server list and actions
    st.subheader("Server Status")
    for server_id, server in st.session_state.servers.items():
        with st.expander(f"{server.name} ({server.status})"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.json({
                    "url": server.url,
                    "latency": f"{server.latency_ms:.1f}ms" if server.latency_ms else "N/A",
                    "last_checked": datetime.fromtimestamp(server.last_checked).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "capabilities": server.capabilities
                })
            
            with col2:
                if st.button("Test Connection", key=f"test_{server_id}"):
                    with st.spinner("Testing..."):
                        result = asyncio.run(test_server_connection(server_id))
                        if result.success:
                            st.success(f"Connected! Latency: {result.latency_ms:.1f}ms")
                        else:
                            st.error(f"Failed: {result.error_message}")

async def test_server_connection(server_id: str) -> ServerTestResult:
    """Test connection to a specific server."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/servers/{server_id}/test"
            )
            return ServerTestResult(**response.json())
        except Exception as e:
            return ServerTestResult(
                server_id=server_id,
                success=False,
                latency_ms=-1,
                error_message=str(e)
            )
```

### 3. Chat Interface

```python
def show_chat_interface():
    st.header("Chat Interface")
    
    # Model selection sidebar
    with st.sidebar:
        st.subheader("Model Selection")
        
        # Fetch available models from OpenRouter
        if 'available_models' not in st.session_state:
            with st.spinner("Fetching available models..."):
                models = asyncio.run(fetch_available_models())
                st.session_state.available_models = models
        
        # Model selector
        selected_model = st.selectbox(
            "Select Model",
            options=[(m['id'], m['name']) for m in st.session_state.available_models],
            format_func=lambda x: x[1]
        )
        st.session_state.selected_model = selected_model[0] if selected_model else None
        
        # Model parameters
        st.subheader("Parameters")
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7)
        max_tokens = st.number_input("Max Tokens", 1, 4096, 1000)
    
    # Chat history display
    st.subheader("Chat History")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input area
    if prompt := st.chat_input("Enter your message"):
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get model response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Stream the response
            for response in asyncio.run(
                stream_chat_response(
                    messages=st.session_state.chat_history,
                    model=st.session_state.selected_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            ):
                if 'content' in response.choices[0].delta:
                    full_response += response.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
        
        # Add assistant response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": full_response
        })

async def fetch_available_models():
    """Fetch available models from OpenRouter."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BACKEND_URL}/chat/models")
        return response.json()

async def stream_chat_response(messages, model, temperature, max_tokens):
    """Stream chat response from backend."""
    async with websockets.connect(f"{WS_URL}/chat") as websocket:
        await websocket.send(json.dumps({
            "messages": messages,
            "model": model,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens
        }))
        
        while True:
            response = await websocket.recv()
            yield json.loads(response)
```

### 4. WebSocket Connection Management

```python
async def maintain_websocket_connection():
    """Maintain WebSocket connection with backend."""
    while True:
        try:
            async with websockets.connect(f"{WS_URL}/ws") as websocket:
                st.session_state.ws_connection = websocket
                
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data["type"] == "server_update":
                        server_info = ServerInfo(**data["data"])
                        st.session_state.servers[server_info.id] = server_info
                        st.experimental_rerun()
                        
        except websockets.ConnectionClosed:
            await asyncio.sleep(1)  # Retry delay
        except Exception as e:
            st.error(f"WebSocket error: {str(e)}")
            await asyncio.sleep(5)  # Longer retry delay on error

def init_websocket():
    """Initialize WebSocket connection."""
    if 'websocket_task' not in st.session_state:
        st.session_state.websocket_task = asyncio.create_task(
            maintain_websocket_connection()
        )
```

### 5. Main Application

```python
def main():
    st.title("AutoMCP Dashboard")
    
    # Initialize WebSocket
    init_websocket()
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Server Dashboard", "Chat Interface", "Settings"]
    )
    
    if page == "Server Dashboard":
        show_server_dashboard()
    elif page == "Chat Interface":
        show_chat_interface()
    else:
        show_settings()

def show_settings():
    st.header("Settings")
    
    # Backend configuration
    st.subheader("Backend Configuration")
    backend_url = st.text_input(
        "Backend URL",
        value=st.session_state.get('backend_url', 'http://localhost:8000')
    )
    st.session_state.backend_url = backend_url
    
    # OpenRouter configuration
    st.subheader("OpenRouter Configuration")
    api_key = st.text_input(
        "API Key",
        value=st.session_state.get('openrouter_api_key', ''),
        type="password"
    )
    st.session_state.openrouter_api_key = api_key
    
    # Test connections
    if st.button("Test Connections"):
        with st.spinner("Testing backend connection..."):
            try:
                response = httpx.get(f"{backend_url}/health")
                if response.status_code == 200:
                    st.success("Backend connection successful!")
                else:
                    st.error("Backend connection failed!")
            except Exception as e:
                st.error(f"Backend connection error: {str(e)}")
        
        with st.spinner("Testing OpenRouter connection..."):
            try:
                response = httpx.get(
                    "https://openrouter.ai/api/v1/auth/test",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if response.status_code == 200:
                    st.success("OpenRouter connection successful!")
                else:
                    st.error("OpenRouter connection failed!")
            except Exception as e:
                st.error(f"OpenRouter connection error: {str(e)}")

if __name__ == "__main__":
    main()
```

## Best Practices

1. **State Management**
   - Use session state for persistent data
   - Handle WebSocket reconnection
   - Maintain chat history
   - Track server status

2. **User Interface**
   - Clear navigation
   - Real-time updates
   - Progress indicators
   - Error messages

3. **Error Handling**
   - Connection retry logic
   - Clear error messages
   - Graceful degradation
   - Status feedback

4. **Performance**
   - Efficient updates
   - Response streaming
   - Connection pooling
   - Resource cleanup

## Related Documentation
- [[WebSocket Management]]
- [[Streamlit State Management]]
- [[OpenRouter Integration]]