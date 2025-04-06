"""Tests for hivemcp.types module."""

import pytest
from pydantic import ValidationError

from hivemcp.types import GroupConfig, ServiceConfig, ServiceGroup


class TestGroupConfig:
    """Tests for the GroupConfig class."""

    def test_create_valid_group_config(self, sample_group_config):
        """Should create a valid GroupConfig instance."""
        group_config = GroupConfig(**sample_group_config)
        assert group_config.name == "test_group"
        assert group_config.class_path == "module.path:TestClass"
        assert group_config.description == "Test group description"
        assert group_config.packages == ["package1", "package2"]
        assert group_config.config == {"key1": "value1", "key2": 123}
        assert group_config.env_vars == {"ENV_VAR1": "value1", "ENV_VAR2": "value2"}

    def test_minimal_group_config(self):
        """Should create a GroupConfig with only required fields."""
        minimal_config = {
            "name": "minimal_group",
            "class_path": "module.path:MinimalClass",
        }
        group_config = GroupConfig(**minimal_config)
        assert group_config.name == "minimal_group"
        assert group_config.class_path == "module.path:MinimalClass"
        assert group_config.description is None
        assert group_config.packages == []
        assert group_config.config == {}
        assert group_config.env_vars == {}

    def test_invalid_class_path_format(self):
        """Should raise ValidationError for invalid class_path format."""
        # Missing colon
        with pytest.raises(ValueError, match="class_path must be in the format"):
            GroupConfig(name="test", class_path="module.path.TestClass")

        # Starting with dot
        with pytest.raises(ValueError, match="class_path must be in the format"):
            GroupConfig(name="test", class_path=".module.path:TestClass")

        # Colon not in the last segment
        with pytest.raises(ValueError, match="class_path must be in the format"):
            GroupConfig(name="test", class_path="module:path.TestClass")

    def test_missing_required_fields(self):
        """Should raise ValidationError when required fields are missing."""
        # Missing name
        with pytest.raises(ValidationError):
            GroupConfig(class_path="module.path:TestClass")

        # Missing class_path
        with pytest.raises(ValidationError):
            GroupConfig(name="test_group")


class TestServiceConfig:
    """Tests for the ServiceConfig class."""

    def test_create_valid_service_config(self, sample_service_config):
        """Should create a valid ServiceConfig instance."""
        service_config = ServiceConfig(**sample_service_config)
        assert service_config.name == "test_service"
        assert service_config.description == "Test service description"
        assert len(service_config.groups) == 2
        assert "group1" in service_config.groups
        assert "group2" in service_config.groups
        assert service_config.groups["group1"].name == "test_group1"
        assert service_config.groups["group2"].name == "test_group2"
        assert service_config.packages == ["package1", "package2"]
        assert service_config.env_vars == {"ENV_VAR1": "value1", "ENV_VAR2": "value2"}

    def test_minimal_service_config(self):
        """Should create a ServiceConfig with only required fields."""
        minimal_config = {
            "name": "minimal_service",
            "groups": {
                "group1": {
                    "name": "minimal_group",
                    "class_path": "module.path:MinimalClass",
                }
            },
        }
        service_config = ServiceConfig(**minimal_config)
        assert service_config.name == "minimal_service"
        assert service_config.description is None
        assert len(service_config.groups) == 1
        assert service_config.groups["group1"].name == "minimal_group"
        assert service_config.packages == []
        assert service_config.env_vars == {}

    def test_missing_required_fields(self):
        """Should raise ValidationError when required fields are missing."""
        # Missing name
        with pytest.raises(ValidationError):
            ServiceConfig(groups={"group1": {"name": "g1", "class_path": "mod:Class"}})

        # Missing groups
        with pytest.raises(ValidationError):
            ServiceConfig(name="test_service")

        # Empty groups are actually allowed by Pydantic, but invalid group items should fail
        with pytest.raises(ValidationError):
            ServiceConfig(name="test_service", groups={"invalid_group": "not_a_dict"})


class TestServiceGroup:
    """Tests for the ServiceGroup class."""

    def test_init_with_config(self):
        """Should initialize ServiceGroup with config."""
        config = {"key1": "value1", "key2": 123}
        group = ServiceGroup(config=config)
        assert group.group_config == config

    def test_init_without_config(self):
        """Should initialize ServiceGroup without config."""
        group = ServiceGroup()
        assert group.group_config == {}
