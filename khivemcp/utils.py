"""Utility functions for loading khivemcp configurations."""

import json
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .types import GroupConfig, ServiceConfig


def load_config(path: Path) -> ServiceConfig | GroupConfig:
    """Load and validate configuration from a YAML or JSON file.

    Determines whether the file represents a ServiceConfig (multiple groups)
    or a GroupConfig (single group) based on structure.

    Args:
        path: Path to the configuration file.

    Returns:
        A validated ServiceConfig or GroupConfig object.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file format is unsupported, content is invalid,
            or required fields (like class_path for GroupConfig) are missing.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    print(f"[Config Loader] Reading configuration from: {path}", file=sys.stderr)
    file_content = path.read_text(encoding="utf-8")

    try:
        data: dict
        if path.suffix.lower() in [".yaml", ".yml"]:
            data = yaml.safe_load(file_content)
            if not isinstance(data, dict):
                raise ValueError("YAML content does not resolve to a dictionary.")
            print(
                f"[Config Loader] Parsed YAML content from '{path.name}'",
                file=sys.stderr,
            )
        elif path.suffix.lower() == ".json":
            data = json.loads(file_content)
            if not isinstance(data, dict):
                raise ValueError("JSON content does not resolve to an object.")
            print(
                f"[Config Loader] Parsed JSON content from '{path.name}'",
                file=sys.stderr,
            )
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")

        # Differentiate based on structure (presence of 'groups' dictionary)
        if "groups" in data and isinstance(data.get("groups"), dict):
            print(
                f"[Config Loader] Detected ServiceConfig structure. Validating...",
                file=sys.stderr,
            )
            config_obj = ServiceConfig(**data)
            print(
                f"[Config Loader] ServiceConfig '{config_obj.name}' validated successfully.",
                file=sys.stderr,
            )
            return config_obj
        else:
            print(
                f"[Config Loader] Assuming GroupConfig structure. Validating...",
                file=sys.stderr,
            )
            # GroupConfig requires 'class_path'
            if "class_path" not in data:
                raise ValueError(
                    "Configuration appears to be GroupConfig but is missing the required 'class_path' field."
                )
            config_obj = GroupConfig(**data)
            print(
                f"[Config Loader] GroupConfig '{config_obj.name}' validated successfully.",
                file=sys.stderr,
            )
            return config_obj

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid file format in '{path.name}': {e}")
    except ValidationError as e:
        raise ValueError(f"Configuration validation failed for '{path.name}':\n{e}")
    except Exception as e:
        raise ValueError(
            f"Failed to load configuration from '{path.name}': {type(e).__name__}: {e}"
        )
