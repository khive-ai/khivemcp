"""Core configuration data models for khivemcp."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class GroupConfig(BaseModel):
    """Configuration for a single service group instance."""

    name: str = Field(
        ...,
        description="Unique name for this specific group instance (used in MCP tool names like 'name.operation').",
    )
    class_path: str = Field(
        ...,
        description="Full Python import path to the ServiceGroup class (e.g., 'my_module.submodule:MyGroupClass').",
    )
    description: str | None = Field(
        None, description="Optional description of this group instance."
    )
    packages: list[str] = Field(
        default_factory=list,
        description="List of additional Python packages required specifically for this group.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Group-specific configuration dictionary passed to the group's __init__ if it accepts a 'config' argument.",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables specific to this group (currently informational, not automatically injected).",
    )

    @field_validator("class_path")
    def check_class_path_format(cls, v):
        if ":" not in v or v.startswith(".") or ":" not in v.split(".")[-1]:
            raise ValueError("class_path must be in the format 'module.path:ClassName'")
        return v


class ServiceConfig(BaseModel):
    """Configuration for a service containing multiple named group instances."""

    name: str = Field(..., description="Name of the overall service.")
    description: str | None = Field(
        None, description="Optional description of the service."
    )
    groups: dict[str, GroupConfig] = Field(
        ...,
        description="Dictionary of group configurations. The keys are logical identifiers for the instances within this service config.",
    )
    packages: list[str] = Field(
        default_factory=list,
        description="List of shared Python packages required across all groups in this service.",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Shared environment variables for all groups (currently informational, not automatically injected).",
    )


class ServiceGroup:

    def __init__(self, config: dict[str, Any] = None):
        self.group_config = config or {}
