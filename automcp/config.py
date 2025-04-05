"""
Configuration loading utilities for AutoMCP.

This module provides functions for loading and validating configuration files
for AutoMCP services and groups.
"""

import json
from pathlib import Path
from typing import Union

import yaml

from .exceptions import ConfigFormatError, ConfigNotFoundError
from .types import GroupConfig, ServiceConfig


def load_config(path: Path) -> Union[ServiceConfig, GroupConfig]:
    """
    Load configuration from a YAML or JSON file.

    This function loads and validates a configuration file, determining whether
    it contains a ServiceConfig (multi-group) or GroupConfig (single-group)
    based on the file content rather than just the extension.

    Args:
        path: Path to the configuration file.

    Returns:
        Either a ServiceConfig or GroupConfig object, depending on the file content.

    Raises:
        ConfigNotFoundError: If the configuration file does not exist.
        ConfigFormatError: If the file format is not supported or if the file
            contains invalid data (JSON/YAML syntax errors or validation errors).
    """
    if not path.exists():
        raise ConfigNotFoundError(f"Configuration file not found: {path}")

    try:
        suffix = path.suffix.lower()
        with open(path, "r", encoding="utf-8") as f:
            if suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            elif suffix == ".json":
                data = json.load(f)
            else:
                raise ConfigFormatError(f"Unsupported file format: {suffix}")

            # Determine if this is a ServiceConfig or GroupConfig based on content
            # ServiceConfig must have a 'groups' key
            if "groups" in data and isinstance(data["groups"], dict):
                try:
                    return ServiceConfig(**data)
                except Exception as e_service:
                    raise ConfigFormatError(
                        f"Invalid format for ServiceConfig: {e_service}"
                    ) from e_service
            else:
                # If no 'groups' key or not a dict, try as GroupConfig
                try:
                    return GroupConfig(**data)
                except Exception as e_group:
                    raise ConfigFormatError(
                        f"Invalid format for GroupConfig: {e_group}"
                    ) from e_group
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ConfigFormatError(
            f"Invalid configuration file format: {e}"
        ) from e
    except Exception as e:
        # Catch any other unexpected errors
        if "validation error" in str(e).lower():
            raise ConfigFormatError(
                f"Configuration validation error: {e}"
            ) from e
        raise ConfigFormatError(f"Failed to load configuration: {e}") from e
