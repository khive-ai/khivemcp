"""Pytest configuration and shared fixtures for khivemcp tests."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
import yaml

# Add the parent directory to sys.path so we can import khivemcp modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from khivemcp.types import GroupConfig, ServiceConfig

# Removed event_loop fixture to avoid pytest-asyncio conflict


@pytest.fixture
def mock_token():
    """Create a mock access token with configurable scopes."""

    def _create_token(scopes: List[str] = None, sub: str = "test_user"):
        return SimpleNamespace(
            scopes=scopes or [],
            sub=sub,
            exp=9999999999,  # Far future
            iat=1000000000,
            iss="test_issuer",
        )

    return _create_token


@pytest.fixture
def mock_context():
    """Create a mock FastMCP Context with configurable token."""

    def _create_context(token=None, **kwargs):
        ctx = SimpleNamespace(**kwargs)
        if token:
            ctx.access_token = token
        return ctx

    return _create_context


@pytest.fixture(scope="session")
def session_tmp_dir():
    """Create a session-scoped temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_dir(session_tmp_dir) -> Path:
    """Create a test-scoped directory within the session temp dir."""
    test_dir = session_tmp_dir / f"test_{id(object())}"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture
def good_group_config():
    """Create a valid GroupConfig for testing."""
    return GroupConfig(
        name="test_good",
        class_path="tests.dummies:GoodGroup",
        description="Good test group",
        config={"test_param": "test_value"},
    )


@pytest.fixture
def bad_group_config():
    """Create a GroupConfig that points to a group that fails startup."""
    return GroupConfig(
        name="test_bad",
        class_path="tests.dummies:BadGroup",
        description="Bad test group for failure testing",
    )


@pytest.fixture
def service_config(good_group_config, bad_group_config):
    """Create a ServiceConfig with multiple groups."""
    return ServiceConfig(
        name="test_service",
        description="Test service configuration",
        groups={"good": good_group_config, "bad": bad_group_config},
    )


@pytest.fixture
def sample_group_config():
    """Sample group configuration dictionary."""
    return {
        "name": "test_group",
        "class_path": "tests.dummies:GoodGroup",
        "description": "Test group description",
        "packages": ["package1", "package2"],
        "config": {"key1": "value1", "key2": 123},
        "env_vars": {"ENV_VAR1": "value1", "ENV_VAR2": "value2"},
    }


@pytest.fixture
def sample_service_config():
    """Sample service configuration dictionary."""
    return {
        "name": "test_service",
        "description": "Test service description",
        "groups": {
            "group1": {
                "name": "test_group1",
                "class_path": "tests.dummies:GoodGroup",
                "description": "Test group 1 description",
                "config": {"key1": "value1"},
            },
            "group2": {
                "name": "test_group2",
                "class_path": "tests.dummies:GoodGroup",
                "description": "Test group 2 description",
                "config": {"key2": "value2"},
            },
        },
        "packages": ["package1", "package2"],
        "env_vars": {"ENV_VAR1": "value1", "ENV_VAR2": "value2"},
    }


@pytest.fixture
def sample_config_data():
    """Sample configuration data for file-based tests."""
    return {
        "name": "test_service",
        "description": "Test service from file",
        "groups": {
            "main": {
                "name": "main_group",
                "class_path": "tests.dummies:GoodGroup",
                "description": "Main test group",
                "config": {"param1": "value1", "param2": 42},
            }
        },
    }


@pytest.fixture
def group_config_file(temp_dir, sample_group_config):
    """Create a temporary YAML file with group configuration."""
    config_file = temp_dir / "test_group_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_group_config, f)
    return config_file


@pytest.fixture
def group_config_json_file(temp_dir, sample_group_config):
    """Create a temporary JSON file with group configuration."""
    config_file = temp_dir / "test_group_config.json"
    with open(config_file, "w") as f:
        json.dump(sample_group_config, f, indent=2)
    return config_file


@pytest.fixture
def service_config_file(temp_dir, sample_service_config):
    """Create a temporary YAML file with service configuration."""
    config_file = temp_dir / "test_service_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_service_config, f)
    return config_file


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file for testing."""

    def _create_config(config_data: Dict[str, Any], format: str = "yaml"):
        if format == "yaml":
            config_file = tmp_path / "test_config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)
        else:  # json
            config_file = tmp_path / "test_config.json"
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)
        return config_file

    return _create_config


class AsyncMock:
    """Simple async mock for testing."""

    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.call_count = 0
        self.call_args_list = []

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args_list.append((args, kwargs))

        if self.side_effect:
            if isinstance(self.side_effect, Exception):
                raise self.side_effect
            return self.side_effect(*args, **kwargs)

        return self.return_value


@pytest.fixture
def async_mock():
    """Create an AsyncMock instance."""
    return AsyncMock
