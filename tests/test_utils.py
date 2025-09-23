"""Tests for khivemcp.utils module."""

import json

import pytest
import yaml

from khivemcp.types import GroupConfig, ServiceConfig
from khivemcp.utils import load_config


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_group_config_yaml(self, group_config_file):
        """Should load a valid GroupConfig from YAML file."""
        config = load_config(group_config_file)
        assert isinstance(config, GroupConfig)
        assert config.name == "test_group"
        assert config.class_path == "tests.dummies:GoodGroup"
        assert config.description == "Test group description"

    def test_load_group_config_json(self, group_config_json_file):
        """Should load a valid GroupConfig from JSON file."""
        config = load_config(group_config_json_file)
        assert isinstance(config, GroupConfig)
        assert config.name == "test_group"
        assert config.class_path == "tests.dummies:GoodGroup"
        assert config.description == "Test group description"

    def test_load_service_config(self, service_config_file):
        """Should load a valid ServiceConfig from YAML file."""
        config = load_config(service_config_file)
        assert isinstance(config, ServiceConfig)
        assert config.name == "test_service"
        assert config.description == "Test service description"
        assert len(config.groups) == 2
        assert config.groups["group1"].name == "test_group1"
        assert config.groups["group2"].name == "test_group2"

    def test_file_not_found(self, temp_dir):
        """Should raise FileNotFoundError for non-existent file."""
        non_existent_file = temp_dir / "non_existent.yaml"
        with pytest.raises(FileNotFoundError):
            load_config(non_existent_file)

    def test_unsupported_file_format(self, temp_dir):
        """Should raise ValueError for unsupported file format."""
        unsupported_file = temp_dir / "config.txt"
        unsupported_file.touch()
        with pytest.raises(ValueError, match="Unsupported configuration file format"):
            load_config(unsupported_file)

    def test_invalid_yaml_content(self, temp_dir):
        """Should raise ValueError for invalid YAML content."""
        invalid_yaml_file = temp_dir / "invalid.yaml"
        with open(invalid_yaml_file, "w") as f:
            f.write("invalid: yaml: content:\n  - missing: colon\n    indentation")

        with pytest.raises(ValueError, match="Invalid file format"):
            load_config(invalid_yaml_file)

    def test_invalid_json_content(self, temp_dir):
        """Should raise ValueError for invalid JSON content."""
        invalid_json_file = temp_dir / "invalid.json"
        with open(invalid_json_file, "w") as f:
            f.write("{invalid json}")

        with pytest.raises(ValueError, match="Invalid file format"):
            load_config(invalid_json_file)

    def test_yaml_not_dict(self, temp_dir):
        """Should raise ValueError when YAML content is not a dictionary."""
        not_dict_file = temp_dir / "not_dict.yaml"
        with open(not_dict_file, "w") as f:
            yaml.dump(["item1", "item2"], f)  # List instead of dict

        with pytest.raises(ValueError, match="does not resolve to a dictionary"):
            load_config(not_dict_file)

    def test_json_not_dict(self, temp_dir):
        """Should raise ValueError when JSON content is not an object."""
        not_dict_file = temp_dir / "not_dict.json"
        with open(not_dict_file, "w") as f:
            json.dump(["item1", "item2"], f)  # Array instead of object

        with pytest.raises(ValueError, match="does not resolve to an object"):
            load_config(not_dict_file)

    def test_group_config_missing_class_path(self, temp_dir):
        """Should raise ValueError when GroupConfig is missing class_path."""
        invalid_config_file = temp_dir / "invalid_group.yaml"
        with open(invalid_config_file, "w") as f:
            yaml.dump({"name": "test_group"}, f)  # Missing class_path

        with pytest.raises(ValueError, match="missing the required 'class_path'"):
            load_config(invalid_config_file)

    def test_validation_error_propagation(self, temp_dir):
        """Should propagate validation errors from Pydantic."""
        invalid_config_file = temp_dir / "validation_error.yaml"
        with open(invalid_config_file, "w") as f:
            # Missing required 'name' field
            yaml.dump({"class_path": "module.path:TestClass"}, f)

        with pytest.raises(ValueError, match="Configuration validation failed"):
            load_config(invalid_config_file)
