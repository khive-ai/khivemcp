"""
Tests for the configuration loading utilities in automcp/config.py.
"""

import json
import os
from pathlib import Path

import pytest
import yaml

from automcp.config import load_config
from automcp.exceptions import ConfigFormatError, ConfigNotFoundError
from automcp.types import GroupConfig, ServiceConfig


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


def test_load_config_nonexistent_file():
    """Test that loading a nonexistent file raises ConfigNotFoundError."""
    with pytest.raises(ConfigNotFoundError) as excinfo:
        load_config(Path("nonexistent_file.yaml"))
    assert "Configuration file not found" in str(excinfo.value)


def test_load_config_yaml_service_config(temp_dir):
    """Test loading a valid YAML ServiceConfig."""
    # Create a valid ServiceConfig YAML file
    config_path = temp_dir / "service_config.yaml"
    service_config = {
        "name": "test-service",
        "description": "Test service",
        "groups": {
            "module.path:GroupClass": {
                "name": "test-group",
                "description": "Test group",
                "config": {"setting": "value"},
            }
        },
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(service_config, f)

    # Load the config
    config = load_config(config_path)

    # Verify it's a ServiceConfig
    assert isinstance(config, ServiceConfig)
    assert config.name == "test-service"
    assert config.description == "Test service"
    assert "module.path:GroupClass" in config.groups
    assert config.groups["module.path:GroupClass"].name == "test-group"


def test_load_config_yaml_group_config(temp_dir):
    """Test loading a valid YAML GroupConfig."""
    # Create a valid GroupConfig YAML file
    config_path = temp_dir / "group_config.yaml"
    group_config = {
        "name": "test-group",
        "description": "Test group",
        "config": {"setting": "value"},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(group_config, f)

    # Load the config
    config = load_config(config_path)

    # Verify it's a GroupConfig
    assert isinstance(config, GroupConfig)
    assert config.name == "test-group"
    assert config.description == "Test group"
    assert config.config["setting"] == "value"


def test_load_config_json_group_config(temp_dir):
    """Test loading a valid JSON GroupConfig."""
    # Create a valid GroupConfig JSON file
    config_path = temp_dir / "group_config.json"
    group_config = {
        "name": "test-group",
        "description": "Test group",
        "config": {"setting": "value"},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(group_config, f)

    # Load the config
    config = load_config(config_path)

    # Verify it's a GroupConfig
    assert isinstance(config, GroupConfig)
    assert config.name == "test-group"
    assert config.description == "Test group"
    assert config.config["setting"] == "value"


def test_load_config_json_service_config(temp_dir):
    """Test loading a valid JSON ServiceConfig."""
    # Create a valid ServiceConfig JSON file
    config_path = temp_dir / "service_config.json"
    service_config = {
        "name": "test-service",
        "description": "Test service",
        "groups": {
            "module.path:GroupClass": {
                "name": "test-group",
                "description": "Test group",
                "config": {"setting": "value"},
            }
        },
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(service_config, f)

    # Load the config
    config = load_config(config_path)

    # Verify it's a ServiceConfig
    assert isinstance(config, ServiceConfig)
    assert config.name == "test-service"
    assert config.description == "Test service"
    assert "module.path:GroupClass" in config.groups
    assert config.groups["module.path:GroupClass"].name == "test-group"


def test_load_config_invalid_yaml(temp_dir):
    """Test that loading an invalid YAML file raises ConfigFormatError."""
    # Create an invalid YAML file
    config_path = temp_dir / "invalid.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("invalid: yaml: content: - [")

    with pytest.raises(ConfigFormatError) as excinfo:
        load_config(config_path)
    assert "Invalid configuration file format" in str(excinfo.value)


def test_load_config_invalid_json(temp_dir):
    """Test that loading an invalid JSON file raises ConfigFormatError."""
    # Create an invalid JSON file
    config_path = temp_dir / "invalid.json"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write('{"invalid": "json",}')

    with pytest.raises(ConfigFormatError) as excinfo:
        load_config(config_path)
    assert "Invalid configuration file format" in str(excinfo.value)


def test_load_config_invalid_format(temp_dir):
    """Test that loading a file with an unsupported format raises ConfigFormatError."""
    # Create a file with an unsupported extension
    config_path = temp_dir / "config.txt"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("Some text content")

    with pytest.raises(ConfigFormatError) as excinfo:
        load_config(config_path)
    assert "Unsupported file format" in str(excinfo.value)


def test_load_config_validation_error(temp_dir):
    """Test that loading a file with invalid config structure raises ConfigFormatError."""
    # Create a YAML file with missing required fields
    config_path = temp_dir / "invalid_structure.yaml"
    invalid_config = {
        # Missing required 'name' field
        "description": "Invalid config",
        "groups": {},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(invalid_config, f)

    with pytest.raises(ConfigFormatError) as excinfo:
        load_config(config_path)
    assert "Invalid format for ServiceConfig" in str(excinfo.value)
