---
type: resource
title: "AutoMCP Streamlit Frontend Implementation"
created: 2024-12-22 19:05 EST
updated: 2024-12-22 19:05 EST
status: active
tags: [resource, frontend, streamlit, mcp]
aliases: [automcp-streamlit]
related: ["[[AutoMCP_Client_Implementation]]", "[[Project_AutoMCP]]"]
sources: 
  - "Streamlit Docs: https://docs.streamlit.io/"
  - "Restack Streamlit Guide: https://www.restack.io/docs/streamlit-knowledge-streamlit-components-guide"
confidence: certain
---

# AutoMCP Streamlit Frontend

## Overview

This implementation guide covers building a Streamlit frontend for AutoMCP, focusing on:
- Client instance management
- Operation execution UI
- Progress tracking
- Error handling and display

## Core Implementation

### 1. Application Structure
```python
import streamlit as st
from automcp.client import AutoMCPClient, ClientConfig

def init_client():
    """Initialize or retrieve client from session state."""
    if 'client' not in st.session_state:
        st.session_state.client = AutoMCPClient(
            name="streamlit-client",
            config=ClientConfig(
                timeout=30,
                retry_count=3
            )
        )
    return st.session_state.client

def main():
    st.title("AutoMCP Dashboard")
    
    # Initialize client
    client = init_client()
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Operations", "Monitoring", "Configuration"]
    )
    
    # Page routing
    if page == "Operations":
        show_operations_page(client)
    elif page == "Monitoring":
        show_monitoring_page(client)
    else:
        show_configuration_page(client)

if __name__ == "__main__":
    main()
```

### 2. Operations Page
```python
def show_operations_page(client: AutoMCPClient):
    st.header("Operations")
    
    # Group selection
    group_name = st.selectbox(
        "Select Group",
        options=list(client.groups.keys())
    )
    
    group = client.groups[group_name]
    
    # Operation selection
    operation = st.selectbox(
        "Select Operation",
        options=list(group._operations.keys())
    )
    
    # Input form
    with st.form("operation_form"):
        # Dynamic input fields based on operation schema
        input_data = {}
        for field, info in group._operations[operation].schema.items():
            value = st.text_input(
                f"Enter {field}",
                help=info.get("description", "")
            )
            if value:
                input_data[field] = value
        
        submitted = st.form_submit_button("Execute Operation")
        
    if submitted:
        try:
            # Show spinner during execution
            with st.spinner("Executing operation..."):
                result = asyncio.run(
                    group.execute(operation, input_data)
                )
            
            # Display result
            st.success("Operation completed!")
            st.json(result.dict())
            
        except Exception as e:
            st.error(f"Operation failed: {str(e)}")
```

### 3. Monitoring Page
```python
def show_monitoring_page(client: AutoMCPClient):
    st.header("Operation Monitoring")
    
    # Active operations table
    st.subheader("Active Operations")
    if 'progress_tracker' in st.session_state:
        tracker = st.session_state.progress_tracker
        operations = tracker._operations
        
        if operations:
            # Create DataFrame for active operations
            data = []
            for op_id, details in operations.items():
                progress = tracker.get_progress(op_id)
                data.append({
                    'Operation ID': op_id,
                    'Progress': f"{progress['progress']*100:.1f}%",
                    'Elapsed Time': f"{progress['elapsed']:.1f}s",
                    'Status': 'Running' if progress['progress'] < 1 else 'Complete'
                })
            
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No active operations")
    
    # Metrics summary
    st.subheader("System Metrics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Active Operations",
            value=len(operations) if 'operations' in locals() else 0
        )
    
    with col2:
        st.metric(
            label="Available Connections",
            value=client._pool._available
        )
    
    with col3:
        st.metric(
            label="Total Operations",
            value=st.session_state.get('total_operations', 0)
        )
```

### 4. Configuration Page
```python
def show_configuration_page(client: AutoMCPClient):
    st.header("Client Configuration")
    
    # Display current config
    st.subheader("Current Configuration")
    st.json(client.config.__dict__)
    
    # Configuration form
    st.subheader("Update Configuration")
    with st.form("config_form"):
        new_config = {}
        
        new_config['timeout'] = st.number_input(
            "Timeout (seconds)",
            min_value=1,
            value=client.config.timeout
        )
        
        new_config['retry_count'] = st.number_input(
            "Retry Count",
            min_value=0,
            value=client.config.retry_count
        )
        
        new_config['pool_size'] = st.number_input(
            "Connection Pool Size",
            min_value=1,
            value=client.config.pool_size
        )
        
        if st.form_submit_button("Update Configuration"):
            try:
                client.config = ClientConfig(**new_config)
                st.success("Configuration updated successfully!")
            except Exception as e:
                st.error(f"Failed to update configuration: {str(e)}")
```

## Error Handling

### 1. Error Display Component
```python
def show_error_message(error: Exception):
    """Display formatted error message."""
    st.error(
        f"""
        Error Type: {type(error).__name__}
        Message: {str(error)}
        
        If this is a connection error, please check:
        - Server availability
        - Network connectivity
        - Configuration settings
        """
    )

def handle_operation_error(e: Exception):
    """Handle operation execution errors."""
    if isinstance(e, ConnectionError):
        st.error("Connection failed. Please check server status.")
    elif isinstance(e, OperationError):
        st.error(f"Operation failed: {str(e)}")
        if hasattr(e, 'context'):
            st.json(e.context)
    else:
        show_error_message(e)
```

## Progress Tracking

### 1. Progress Bar Component
```python
def show_operation_progress(
    tracker: ProgressTracker,
    operation_id: str
):
    """Display operation progress."""
    try:
        progress = tracker.get_progress(operation_id)
        
        # Progress bar
        st.progress(progress['progress'])
        
        # Details
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Progress", f"{progress['progress']*100:.1f}%")
        with col2:
            st.metric("Time Elapsed", f"{progress['elapsed']:.1f}s")
            
    except KeyError:
        st.warning("Operation not found")
    except Exception as e:
        st.error(f"Error tracking progress: {str(e)}")
```

## Session State Management

### 1. State Initialization
```python
def init_session_state():
    """Initialize session state variables."""
    if 'total_operations' not in st.session_state:
        st.session_state.total_operations = 0
    
    if 'progress_tracker' not in st.session_state:
        st.session_state.progress_tracker = ProgressTracker()
    
    if 'operation_history' not in st.session_state:
        st.session_state.operation_history = []
```

### 2. State Updates
```python
def update_operation_stats(result: ExecutionResponse):
    """Update operation statistics."""
    st.session_state.total_operations += 1
    st.session_state.operation_history.append({
        'timestamp': time.time(),
        'success': not bool(result.error),
        'response': result.dict()
    })
```

## Best Practices

1. **Session State Management**
   - Initialize state consistently
   - Use typed session state variables
   - Handle state updates atomically
   - Clear state when needed

2. **UI Organization**
   - Group related controls
   - Use clear navigation
   - Provide helpful messages
   - Show loading states

3. **Error Handling**
   - Display clear error messages
   - Provide recovery suggestions
   - Log errors appropriately
   - Maintain UI responsiveness

4. **Performance**
   - Cache expensive operations
   - Use st.cache for data loading
   - Update UI efficiently
   - Monitor memory usage

## Related Concepts
- [[AsyncIO in Streamlit]]
- [[UI Design Patterns]]
- [[State Management]]