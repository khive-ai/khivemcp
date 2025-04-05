"""Utility functions for AutoMCP."""

import json
from pathlib import Path
from typing import Any, Dict, Union

import yaml

from .types import GroupConfig, ServiceConfig


def load_config(path: Path) -> Union[ServiceConfig, GroupConfig]:
    """Load configuration from a YAML or JSON file.

    Args:
        path: Path to the configuration file.

    Returns:
        Either a ServiceConfig or GroupConfig object, depending on the file format.
        YAML files are assumed to contain ServiceConfig, while JSON files are assumed
        to contain GroupConfig.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file format is not supported or if the file contains invalid data.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        if path.suffix.lower() in [".yaml", ".yml"]:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            return ServiceConfig(**data)
        elif path.suffix.lower() == ".json":
            with open(path, "r") as f:
                data = json.load(f)
            return GroupConfig(**data)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid configuration file format: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")
