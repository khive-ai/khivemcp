"""Base schemas for AutoMCP."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ServerInfo(BaseModel):
    """Server information and status."""

    id: str = Field(..., description="Unique server identifier")
    name: str = Field(..., description="Human-readable server name")
    url: str = Field(..., description="Server URL")
    status: str = Field("unknown", description="Server status")
    last_checked: float = Field(0.0, description="Last health check timestamp")
    capabilities: Dict[str, Any] = Field(
        default_factory=dict, description="Server capabilities"
    )
    latency_ms: Optional[float] = Field(None, description="Last measured latency")


class TextContent(BaseModel):
    """Text content response."""

    type: Literal["text"] = "text"
    text: str = Field(..., description="Text content")


class BinaryContent(BaseModel):
    """Binary content response."""

    type: Literal["binary"] = "binary"
    data: bytes = Field(..., description="Binary content")


class ExecutionRequest(BaseModel):
    """Operation execution request."""

    operation: str = Field(..., description="Operation name")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Operation arguments")


class ServiceRequest(BaseModel):
    """Service request containing multiple execution requests."""

    requests: List[ExecutionRequest] = Field(
        ..., description="List of execution requests"
    )


class ServiceResponse(BaseModel):
    """Service response containing execution results."""

    content: TextContent | BinaryContent = Field(..., description="Response content")
    errors: Optional[List[str]] = Field(None, description="List of error messages")


class ExecutionResponse(BaseModel):
    """Operation execution response."""

    content: TextContent | BinaryContent = Field(..., description="Response content")
    error: Optional[str] = Field(None, description="Error message if any")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


class ServiceConfig(BaseModel):
    """Service configuration."""

    name: str = Field(..., description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    groups: Dict[str, "GroupConfig"] = Field(
        default_factory=dict, description="Service groups"
    )
    packages: List[str] = Field(default_factory=list, description="Required packages")
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )


class GroupConfig(BaseModel):
    """Group configuration."""

    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    packages: List[str] = Field(
        default_factory=list, description="Group-specific packages"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Group configuration"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Group environment variables"
    )


# Update forward references
ServiceConfig.model_rebuild()
