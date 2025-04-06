"""Shared fixtures for hivemcp tests."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Tuple

import pytest
import yaml
from mcp.shared.memory import create_connected_server_and_client_session
from pydantic import BaseModel

from hivemcp.types import GroupConfig, ServiceConfig, ServiceGroup


class TestModel(BaseModel):
    """Test model for schema validation in decorator tests."""

    name: str
    value: int


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
def sample_group_config() -> Dict[str, Any]:
    """Sample group configuration dictionary."""
    return {
        "name": "test_group",
        "class_path": "module.path:TestClass",
        "description": "Test group description",
        "packages": ["package1", "package2"],
        "config": {"key1": "value1", "key2": 123},
        "env_vars": {"ENV_VAR1": "value1", "ENV_VAR2": "value2"},
    }


@pytest.fixture
def sample_service_config() -> Dict[str, Any]:
    """Sample service configuration dictionary."""
    return {
        "name": "test_service",
        "description": "Test service description",
        "groups": {
            "group1": {
                "name": "test_group1",
                "class_path": "module.path:TestClass1",
                "description": "Test group 1 description",
                "config": {"key1": "value1"},
            },
            "group2": {
                "name": "test_group2",
                "class_path": "module.path:TestClass2",
                "description": "Test group 2 description",
                "config": {"key2": "value2"},
            },
        },
        "packages": ["package1", "package2"],
        "env_vars": {"ENV_VAR1": "value1", "ENV_VAR2": "value2"},
    }


@pytest.fixture
def group_config_file(temp_dir: Path, sample_group_config: Dict[str, Any]) -> Path:
    """Create a temporary YAML file with group configuration."""
    config_file = temp_dir / "test_group_config.yaml"
    config_file.write_text(yaml.dump(sample_group_config))
    return config_file


@pytest.fixture
def group_config_json_file(temp_dir: Path, sample_group_config: Dict[str, Any]) -> Path:
    """Create a temporary JSON file with group configuration."""
    config_file = temp_dir / "test_group_config.json"
    config_file.write_text(json.dumps(sample_group_config))
    return config_file


@pytest.fixture
def service_config_file(temp_dir: Path, sample_service_config: Dict[str, Any]) -> Path:
    """Create a temporary YAML file with service configuration."""
    config_file = temp_dir / "test_service_config.yaml"
    config_file.write_text(yaml.dump(sample_service_config))
    return config_file


@pytest.fixture
def valid_group_config(sample_group_config: Dict[str, Any]) -> GroupConfig:
    """Return a valid GroupConfig instance."""
    return GroupConfig(**sample_group_config)


@pytest.fixture
def valid_service_config(sample_service_config: Dict[str, Any]) -> ServiceConfig:
    """Return a valid ServiceConfig instance."""
    return ServiceConfig(**sample_service_config)


@pytest.fixture
def mock_connected_server_and_client():
    """Create an in-memory connected server and client pair."""
    return create_connected_server_and_client_session


class ConfTestServiceGroup(ServiceGroup):
    """Service Group implementation for test fixtures."""

    def __init__(self, config=None):
        super().__init__(config)
        self.initialized_with_config = config

    async def test_operation(self, context, request=None):
        """Test operation."""
        return {"success": True, "message": "Test operation executed"}

    async def test_operation_with_params(self, context, request=None):
        """Test operation with parameters."""
        if request:
            return {"success": True, "message": f"Received: {request}"}
        return {"success": True, "message": "No parameters received"}


@pytest.fixture
def test_service_group() -> ConfTestServiceGroup:
    """Create a TestServiceGroup instance."""
    return ConfTestServiceGroup(config={"test_key": "test_value"})
