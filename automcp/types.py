"""
Core data models for AutoMCP framework.

This module defines the Pydantic models used throughout the AutoMCP framework for:
- Configuration (GroupConfig, ServiceConfig)
- Request/Response handling (ExecutionRequest, ExecutionResponse, ServiceRequest, ServiceResponse)

These models provide validation, serialization, and structured data representation
for the framework's core functionality.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import mcp.types as types
from pydantic import BaseModel, Field, PrivateAttr


class GroupConfig(BaseModel):
    """
    Configuration for a single service group.
    
    A GroupConfig defines the properties of a ServiceGroup implementation,
    including its name, description, required packages, and custom configuration.
    It can be loaded directly from a YAML or JSON file.
    
    When used in a ServiceConfig, multiple GroupConfigs are mapped to their
    implementation class paths.
    """

    name: str = Field(
        ..., 
        description="Group name (must be unique within a service)"
    )
    description: Optional[str] = Field(
        None, 
        description="Human-readable description of the group's purpose and functionality"
    )
    packages: List[str] = Field(
        default_factory=list, 
        description="Required Python packages for this group to function properly"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Group-specific configuration dictionary passed to the ServiceGroup instance"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict, 
        description="Environment variables required by this group"
    )
    class_path: Optional[str] = Field(
        None, 
        description="Optional path to the ServiceGroup implementation (e.g., 'my_service.groups:MyGroup') when loading a single group directly"
    )


class ServiceConfig(BaseModel):
    """
    Configuration for a service containing multiple groups.
    
    A ServiceConfig defines a complete MCP service with multiple ServiceGroups.
    It includes shared configuration that applies to all groups, as well as
    group-specific configurations mapped to their implementation class paths.
    
    This is typically loaded from a YAML file and used to initialize an AutoMCPServer.
    """

    name: str = Field(
        ..., 
        description="Service name used to identify the MCP server"
    )
    description: Optional[str] = Field(
        None, 
        description="Human-readable description of the service's purpose and functionality"
    )
    groups: Dict[str, GroupConfig] = Field(
        ..., 
        description="Group configurations keyed by class path (e.g., 'my_service.groups:MyGroup')"
    )
    packages: List[str] = Field(
        default_factory=list, 
        description="Shared Python packages required by all groups in this service"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict, 
        description="Shared environment variables required by all groups in this service"
    )


class ExecutionRequest(BaseModel):
    """
    Request model for operation execution.
    
    An ExecutionRequest represents a single operation call within a ServiceGroup.
    It contains the operation name and any arguments required by that operation.
    
    This is primarily used internally by the AutoMCPServer to route MCP call_tool
    requests to the appropriate ServiceGroup and operation.
    """

    _id: str = PrivateAttr(default_factory=lambda: str(uuid4()))
    _created_at: datetime = PrivateAttr(default_factory=lambda: datetime.now(UTC))
    operation: str = Field(
        ..., 
        description="Operation name to execute (must match an @operation-decorated method)"
    )
    arguments: Optional[Dict[str, Any]] = Field(
        None, 
        description="Operation arguments as key-value pairs matching the operation's schema"
    )


class ExecutionResponse(BaseModel):
    """
    Response model for operation execution.
    
    An ExecutionResponse contains the result of executing a single operation.
    It includes the operation's output content and any error information if
    the execution failed.
    
    This is primarily used internally by the AutoMCPServer to format responses
    to MCP call_tool requests.
    """

    _id: str = PrivateAttr(default_factory=lambda: str(uuid4()))
    _request_id: str = PrivateAttr(default="")
    _created_at: datetime = PrivateAttr(default_factory=lambda: datetime.now(UTC))
    content: types.TextContent = Field(
        ..., 
        description="Operation result content formatted as MCP TextContent"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message if execution failed, None if successful"
    )

    def model_dump(self) -> Dict[str, Any]:
        """
        Custom dump to handle Pydantic models in content.
        
        If the content.text field contains a Pydantic model, it will be
        serialized to JSON before returning the dumped data.
        
        Returns:
            Dict[str, Any]: The serialized model data
        """
        data = super().model_dump()
        # In the dumped data, content is a dictionary
        if isinstance(self.content.text, BaseModel):
            data["content"]["text"] = self.content.text.model_dump_json()
        return data


class ServiceRequest(BaseModel):
    """
    Container for multiple execution requests.
    
    A ServiceRequest groups multiple ExecutionRequests together for batch
    processing. This is used internally by the AutoMCPServer when handling
    multiple operations in a single request.
    """

    requests: List[ExecutionRequest] = Field(
        ..., 
        description="List of execution requests to process"
    )


class ServiceResponse(BaseModel):
    """
    Combined response for multiple executions.
    
    A ServiceResponse contains the aggregated results of executing multiple
    operations. It includes the combined content and any errors that occurred
    during execution.
    
    This is used internally by the AutoMCPServer when responding to batch
    operation requests.
    """

    content: types.TextContent = Field(
        ..., 
        description="Combined execution results formatted as MCP TextContent"
    )
    errors: Optional[List[str]] = Field(
        None, 
        description="List of execution errors, None if all operations succeeded"
    )
