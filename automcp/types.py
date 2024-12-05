"""Core data models for MCP service operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import mcp.types as types
from pydantic import BaseModel, PrivateAttr, field_validator


class OperationType(str, Enum):
    """Types of MCP operations."""

    TOOL = "tool"
    PROMPT = "prompt"
    RESOURCE = "resource"


class ExecutionRequest(BaseModel):
    """Request model for operation execution."""

    _id: str = PrivateAttr(default_factory=uuid4)
    _created_at: datetime = PrivateAttr(default_factory=datetime.utcnow)
    type: OperationType
    operation: str
    arguments: dict[str, Any] | None = None


class ExecutionResponse(BaseModel):
    """Response model for operation execution."""

    _id: str = PrivateAttr(default_factory=uuid4)
    _request_id: str = PrivateAttr()
    _created_at: datetime = PrivateAttr(default_factory=datetime.utcnow)
    content: types.TextContent
    error: str | None = None

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, content: types.TextContent) -> types.TextContent:
        """Convert Pydantic models in content to JSON."""
        if isinstance(content.text, BaseModel):
            content.text = content.text.model_dump_json()
        return content


class ServiceRequest(BaseModel):
    """Container for multiple operation requests."""

    requests: list[ExecutionRequest]


class ServiceResponse(BaseModel):
    """Response containing concatenated operation results."""

    content: types.TextContent
    errors: list[str] | None = None
