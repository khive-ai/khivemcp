"""Core data models for MCP service operations."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import mcp.types as types
from pydantic import BaseModel, Field, PrivateAttr


class GroupConfig(BaseModel):
    """Configuration for a single service group."""

    name: str = Field(..., description="Group name")
    description: str | None = Field(None, description="Group description")
    packages: list[str] = Field(default_factory=list, description="Required packages")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Group-specific configuration"
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )


class ServiceConfig(BaseModel):
    """Configuration for a service containing multiple groups."""

    name: str = Field(..., description="Service name")
    description: str | None = Field(None, description="Service description")
    groups: dict[str, GroupConfig] = Field(
        ..., description="Group configurations keyed by class path"
    )
    packages: list[str] = Field(
        default_factory=list, description="Shared packages across groups"
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict, description="Shared environment variables"
    )


class ExecutionRequest(BaseModel):
    """Request model for operation execution."""

    _id: str = PrivateAttr(default_factory=uuid4)
    _created_at: datetime = PrivateAttr(default_factory=datetime.now(UTC))
    operation: str = Field(..., description="Operation name to execute")
    arguments: dict[str, Any] | None = Field(None, description="Operation arguments")


class ExecutionResponse(BaseModel):
    """Response model for operation execution."""

    _id: str = PrivateAttr(default_factory=uuid4)
    _request_id: str = PrivateAttr()
    _created_at: datetime = PrivateAttr(default_factory=datetime.now(UTC))
    content: types.TextContent = Field(..., description="Operation result content")
    error: str | None = Field(None, description="Error message if execution failed")

    def model_dump(self) -> dict[str, Any]:
        """Custom dump to handle Pydantic models in content."""
        data = super().model_dump()
        if isinstance(data["content"].text, BaseModel):
            data["content"].text = data["content"].text.model_dump_json()
        return data


class ServiceRequest(BaseModel):
    """Container for multiple execution requests."""

    requests: list[ExecutionRequest] = Field(
        ..., description="List of execution requests"
    )


class ServiceResponse(BaseModel):
    """Combined response for multiple executions."""

    content: types.TextContent = Field(..., description="Combined execution results")
    errors: list[str] | None = Field(None, description="List of execution errors")
