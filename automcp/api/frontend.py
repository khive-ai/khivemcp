"""Streamlit frontend implementation."""

import asyncio
import json
import time
from typing import Any, Dict, Optional

import httpx
import streamlit as st
import websockets
from websockets.exceptions import ConnectionClosed

from automcp.schemas.base import ExecutionRequest, ExecutionResponse, ServerInfo

# Page configuration
st.set_page_config(
    page_title="AutoMCP Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "servers" not in st.session_state:
    st.session_state.servers = {}
if "ws_connection" not in st.session_state:
    st.session_state.ws_connection = None
if "selected_server" not in st.session_state:
    st.session_state.selected_server = None


async def connect_websocket():
    """Connect to WebSocket server."""
    try:
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            st.session_state.ws_connection = websocket
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data["type"] == "server_update":
                        server = ServerInfo(**data["data"])
                        st.session_state.servers[server.id] = server
                        st.experimental_rerun()
                except ConnectionClosed:
                    break
                except Exception as e:
                    st.error(f"WebSocket error: {str(e)}")
                    break
    except Exception as e:
        st.error(f"Failed to connect to WebSocket: {str(e)}")


def init_websocket():
    """Initialize WebSocket connection."""
    if "websocket_task" not in st.session_state:
        st.session_state.websocket_task = asyncio.create_task(connect_websocket())


def show_server_dashboard():
    """Show server management dashboard."""
    st.header("Server Management")

    # Server status overview
    col1, col2, col3 = st.columns(3)

    with col1:
        healthy_count = sum(
            1 for s in st.session_state.servers.values() if s.status == "healthy"
        )
        st.metric("Healthy Servers", healthy_count)

    with col2:
        degraded_count = sum(
            1 for s in st.session_state.servers.values() if s.status == "degraded"
        )
        st.metric("Degraded Servers", degraded_count)

    with col3:
        unhealthy_count = sum(
            1 for s in st.session_state.servers.values() if s.status == "unhealthy"
        )
        st.metric("Unhealthy Servers", unhealthy_count)

    # Server list
    st.subheader("Server Status")
    for server_id, server in st.session_state.servers.items():
        with st.expander(f"{server.name} ({server.status})"):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.json(
                    {
                        "url": server.url,
                        "latency": (
                            f"{server.latency_ms:.1f}ms" if server.latency_ms else "N/A"
                        ),
                        "last_checked": time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(server.last_checked)
                        ),
                        "capabilities": server.capabilities,
                    }
                )

            with col2:
                if st.button("Test Connection", key=f"test_{server_id}"):
                    with st.spinner("Testing..."):
                        try:
                            response = httpx.get(f"{server.url}/health")
                            if response.status_code == 200:
                                st.success("Connection successful!")
                            else:
                                st.error("Connection failed!")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")


def show_operation_panel():
    """Show operation execution panel."""
    st.header("Operation Execution")

    # Server selection
    server_id = st.selectbox(
        "Select Server",
        options=list(st.session_state.servers.keys()),
        format_func=lambda x: st.session_state.servers[x].name,
    )

    if server_id:
        server = st.session_state.servers[server_id]

        # Operation selection
        if server.capabilities and "tools" in server.capabilities:
            tool = st.selectbox(
                "Select Operation",
                options=server.capabilities["tools"],
                format_func=lambda x: x["name"],
            )

            if tool:
                # Input form
                with st.form("operation_form"):
                    # Dynamic input fields based on schema
                    arguments = {}
                    if "inputSchema" in tool:
                        for field, info in tool["inputSchema"]["properties"].items():
                            value = st.text_input(
                                f"Enter {field}", help=info.get("description", "")
                            )
                            if value:
                                arguments[field] = value

                    submitted = st.form_submit_button("Execute")

                    if submitted:
                        with st.spinner("Executing operation..."):
                            try:
                                response = httpx.post(
                                    f"{server.url}/execute",
                                    json={
                                        "operation": tool["name"],
                                        "arguments": arguments,
                                    },
                                )
                                if response.status_code == 200:
                                    st.success("Operation executed successfully!")
                                    st.json(response.json())
                                else:
                                    st.error(f"Operation failed: {response.text}")
                            except Exception as e:
                                st.error(f"Execution error: {str(e)}")


def show_settings():
    """Show settings panel."""
    st.header("Settings")

    # Backend configuration
    st.subheader("Backend Configuration")
    backend_url = st.text_input(
        "Backend URL",
        value=st.session_state.get("backend_url", "http://localhost:8000"),
    )
    st.session_state.backend_url = backend_url

    # Test connection
    if st.button("Test Backend Connection"):
        with st.spinner("Testing connection..."):
            try:
                response = httpx.get(f"{backend_url}/health")
                if response.status_code == 200:
                    st.success("Backend connection successful!")
                else:
                    st.error("Backend connection failed!")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")


def main():
    """Main application."""
    st.title("AutoMCP Dashboard")

    # Initialize WebSocket
    init_websocket()

    # Navigation
    page = st.sidebar.radio(
        "Navigation", ["Server Dashboard", "Operations", "Settings"]
    )

    if page == "Server Dashboard":
        show_server_dashboard()
    elif page == "Operations":
        show_operation_panel()
    else:
        show_settings()


if __name__ == "__main__":
    main()
