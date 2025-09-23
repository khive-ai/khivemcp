"""Unit tests for group loading, auth resolution, and configuration management."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from khivemcp.groups import (
    collect_auth_providers,
    instantiate_single_group,
    load_and_instantiate_groups,
    prepare_groups_to_load,
    resolve_auth_provider,
)
from khivemcp.types import GroupConfig, ServiceConfig
from tests.dummies import BadGroup, GoodGroup


class TestGroupPreparation:
    """Test group configuration preparation."""

    def test_prepare_groups_from_service_config(self):
        """Test preparing groups from ServiceConfig."""
        group1_config = GroupConfig(name="group1", class_path="tests.dummies:GoodGroup")
        group2_config = GroupConfig(name="group2", class_path="tests.dummies:BadGroup")

        service_config = ServiceConfig(
            name="test_service", groups={"g1": group1_config, "g2": group2_config}
        )

        groups_to_load = prepare_groups_to_load(service_config)

        assert len(groups_to_load) == 2
        assert groups_to_load[0][0] == "tests.dummies:GoodGroup"
        assert groups_to_load[0][1].name == "group1"
        assert groups_to_load[1][0] == "tests.dummies:BadGroup"
        assert groups_to_load[1][1].name == "group2"

    def test_prepare_groups_from_single_group_config(self):
        """Test preparing groups from single GroupConfig."""
        group_config = GroupConfig(
            name="single_group", class_path="tests.dummies:GoodGroup"
        )

        groups_to_load = prepare_groups_to_load(group_config)

        assert len(groups_to_load) == 1
        assert groups_to_load[0][0] == "tests.dummies:GoodGroup"
        assert groups_to_load[0][1].name == "single_group"

    def test_prepare_groups_duplicate_names_error(self):
        """Test that duplicate group names cause an error."""
        group1_config = GroupConfig(
            name="duplicate", class_path="tests.dummies:GoodGroup"
        )
        group2_config = GroupConfig(
            name="duplicate", class_path="tests.dummies:BadGroup"  # Same name!
        )

        service_config = ServiceConfig(
            name="test_service", groups={"g1": group1_config, "g2": group2_config}
        )

        with pytest.raises(SystemExit):
            prepare_groups_to_load(service_config)


class TestGroupInstantiation:
    """Test individual group instantiation."""

    def test_instantiate_good_group(self):
        """Test successful group instantiation."""
        group_config = GroupConfig(
            name="test_group",
            class_path="tests.dummies:GoodGroup",
            config={"test_param": "test_value"},
        )

        instance = instantiate_single_group("tests.dummies:GoodGroup", group_config)

        assert instance is not None
        assert isinstance(instance, GoodGroup)
        assert instance.group_config["test_param"] == "test_value"

    def test_instantiate_invalid_class_path(self):
        """Test instantiation with invalid class path."""
        group_config = GroupConfig(
            name="test_group", class_path="nonexistent.module:NonexistentClass"
        )

        instance = instantiate_single_group(
            "nonexistent.module:NonexistentClass", group_config
        )
        assert instance is None

    def test_instantiate_invalid_class_format(self):
        """Test instantiation with malformed class path."""
        # The GroupConfig validation will catch this during construction
        with pytest.raises(ValueError, match="class_path must be in the format"):
            GroupConfig(name="test_group", class_path="invalid_format")  # Missing ":"

    def test_instantiate_non_service_group_class(self):
        """Test instantiation of class that doesn't inherit from ServiceGroup."""
        # Mock a class that doesn't inherit from ServiceGroup
        with patch("khivemcp.groups.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_class = str  # String class doesn't inherit from ServiceGroup
            mock_module.NotServiceGroup = mock_class
            mock_import.return_value = mock_module

            group_config = GroupConfig(
                name="test_group", class_path="fake.module:NotServiceGroup"
            )

            instance = instantiate_single_group(
                "fake.module:NotServiceGroup", group_config
            )
            assert instance is None


class TestAuthProviders:
    """Test auth provider collection and resolution."""

    def test_collect_auth_providers_none(self):
        """Test collecting auth providers when groups have none."""
        good_group = GoodGroup()
        bad_group = BadGroup()

        group_config1 = GroupConfig(name="good", class_path="tests.dummies:GoodGroup")
        group_config2 = GroupConfig(name="bad", class_path="tests.dummies:BadGroup")

        instantiated_groups = [(good_group, group_config1), (bad_group, group_config2)]

        auth_providers = collect_auth_providers(instantiated_groups)
        assert len(auth_providers) == 0

    def test_collect_auth_providers_with_providers(self):
        """Test collecting auth providers when groups have them."""
        # Create groups with mock auth providers
        mock_auth1 = MagicMock()
        mock_auth2 = MagicMock()

        group1 = GoodGroup()
        group1.fastmcp_auth_provider = mock_auth1

        group2 = GoodGroup()
        group2.fastmcp_auth_provider = mock_auth2

        group_config1 = GroupConfig(name="group1", class_path="tests.dummies:GoodGroup")
        group_config2 = GroupConfig(name="group2", class_path="tests.dummies:GoodGroup")

        instantiated_groups = [(group1, group_config1), (group2, group_config2)]

        auth_providers = collect_auth_providers(instantiated_groups)
        assert len(auth_providers) == 2
        assert mock_auth1 in auth_providers
        assert mock_auth2 in auth_providers

    def test_resolve_auth_provider_none_choice(self):
        """Test resolving auth provider with 'none' choice."""
        mock_providers = [MagicMock(), MagicMock()]

        result = resolve_auth_provider(mock_providers, "none")
        assert result is None

    def test_resolve_auth_provider_auto_choice(self):
        """Test resolving auth provider with 'auto' choice."""
        mock_provider1 = MagicMock()
        mock_provider2 = MagicMock()
        mock_providers = [mock_provider1, mock_provider2]

        result = resolve_auth_provider(mock_providers, "auto")
        assert result is mock_provider1  # Should return first provider

    def test_resolve_auth_provider_no_candidates(self):
        """Test resolving auth provider with no candidates."""
        result = resolve_auth_provider([], "auto")
        assert result is None

    def test_resolve_auth_provider_unexpected_choice(self):
        """Test resolving auth provider with unexpected choice."""
        mock_providers = [MagicMock()]

        # Should handle gracefully and return first provider
        result = resolve_auth_provider(mock_providers, "unexpected")
        assert result is mock_providers[0]


class TestEndToEndGroupLoading:
    """Test complete group loading process."""

    def test_load_and_instantiate_good_groups(self):
        """Test loading and instantiating valid groups."""
        group_config = GroupConfig(
            name="test_group",
            class_path="tests.dummies:GoodGroup",
            config={"test": "value"},
        )

        service_config = ServiceConfig(
            name="test_service", groups={"main": group_config}
        )

        instantiated_groups, auth_candidates = load_and_instantiate_groups(
            service_config
        )

        assert len(instantiated_groups) == 1
        instance, config = instantiated_groups[0]
        assert isinstance(instance, GoodGroup)
        assert config.name == "test_group"
        assert len(auth_candidates) == 0  # GoodGroup doesn't provide auth

    def test_load_and_instantiate_with_auth_providers(self):
        """Test loading groups that provide auth providers."""

        # Create a custom group config that will have auth
        class AuthProvidingGroup(GoodGroup):
            def __init__(self, config=None):
                super().__init__(config)
                self.fastmcp_auth_provider = MagicMock()

        # Patch the import to return our auth-providing group
        with patch("khivemcp.groups.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.AuthGroup = AuthProvidingGroup
            mock_import.return_value = mock_module

            group_config = GroupConfig(
                name="auth_group", class_path="fake.module:AuthGroup"
            )

            instantiated_groups, auth_candidates = load_and_instantiate_groups(
                group_config
            )

            assert len(instantiated_groups) == 1
            assert len(auth_candidates) == 1

    def test_load_and_instantiate_mixed_success_failure(self):
        """Test loading with some groups succeeding and others failing."""
        good_config = GroupConfig(
            name="good_group", class_path="tests.dummies:GoodGroup"
        )

        bad_config = GroupConfig(
            name="bad_group", class_path="nonexistent.module:BadClass"
        )

        service_config = ServiceConfig(
            name="mixed_service", groups={"good": good_config, "bad": bad_config}
        )

        instantiated_groups, auth_candidates = load_and_instantiate_groups(
            service_config
        )

        # Only the good group should be instantiated
        assert len(instantiated_groups) == 1
        instance, config = instantiated_groups[0]
        assert isinstance(instance, GoodGroup)
        assert config.name == "good_group"

    def test_load_and_instantiate_no_valid_groups(self):
        """Test loading when no groups can be instantiated."""
        bad_config = GroupConfig(
            name="bad_group", class_path="nonexistent.module:BadClass"
        )

        service_config = ServiceConfig(name="bad_service", groups={"bad": bad_config})

        instantiated_groups, auth_candidates = load_and_instantiate_groups(
            service_config
        )

        assert len(instantiated_groups) == 0
        assert len(auth_candidates) == 0


class TestConfigValidation:
    """Test configuration validation and error handling."""

    def test_group_config_validation(self):
        """Test GroupConfig validation."""
        # Valid config
        config = GroupConfig(name="test", class_path="module.path:ClassName")
        assert config.name == "test"
        assert config.class_path == "module.path:ClassName"

        # Invalid class_path format
        with pytest.raises(ValueError, match="class_path must be in the format"):
            GroupConfig(name="test", class_path="invalid_format")  # Missing ":"

    def test_service_config_validation(self):
        """Test ServiceConfig validation."""
        group_config = GroupConfig(name="test_group", class_path="module:Class")

        config = ServiceConfig(name="test_service", groups={"main": group_config})

        assert config.name == "test_service"
        assert "main" in config.groups
        assert config.groups["main"].name == "test_group"
