"""Tests for the core data models in automcp/types.py."""

import json
from datetime import datetime

import pytest
from pydantic import BaseModel

import mcp.types as mcp_types
from automcp.types import (
    ExecutionRequest,
    ExecutionResponse,
    GroupConfig,
    ServiceConfig,
    ServiceRequest,
    ServiceResponse,
)


class TestGroupConfig:
    """Tests for the GroupConfig class."""

    def test_basic_initialization(self):
        """Test basic initialization with required fields."""
        config = GroupConfig(name="test-group")
        assert config.name == "test-group"
        assert config.description is None
        assert config.packages == []
        assert config.config == {}
        assert config.env_vars == {}
        assert config.class_path is None

    def test_full_initialization(self):
        """Test initialization with all fields."""
        config = GroupConfig(
            name="test-group",
            description="Test group description",
            packages=["package1", "package2"],
            config={"key1": "value1", "key2": 42},
            env_vars={"ENV_VAR1": "value1", "ENV_VAR2": "value2"},
            class_path="my_package.groups:MyGroup",
        )
        assert config.name == "test-group"
        assert config.description == "Test group description"
        assert config.packages == ["package1", "package2"]
        assert config.config == {"key1": "value1", "key2": 42}
        assert config.env_vars == {"ENV_VAR1": "value1", "ENV_VAR2": "value2"}
        assert config.class_path == "my_package.groups:MyGroup"

    def test_serialization(self):
        """Test serialization to dict and JSON."""
        config = GroupConfig(
            name="test-group",
            description="Test group description",
            class_path="my_package.groups:MyGroup",
        )
        config_dict = config.model_dump()
        assert config_dict["name"] == "test-group"
        assert config_dict["description"] == "Test group description"
        assert config_dict["class_path"] == "my_package.groups:MyGroup"

        # Test JSON serialization
        config_json = config.model_dump_json()
        config_from_json = json.loads(config_json)
        assert config_from_json["name"] == "test-group"
        assert config_from_json["class_path"] == "my_package.groups:MyGroup"


class TestServiceConfig:
    """Tests for the ServiceConfig class."""

    def test_basic_initialization(self):
        """Test basic initialization with required fields."""
        config = ServiceConfig(
            name="test-service",
            groups={
                "module.path:GroupClass": GroupConfig(name="group1"),
                "another.module:AnotherGroup": GroupConfig(name="group2"),
            },
        )
        assert config.name == "test-service"
        assert config.description is None
        assert len(config.groups) == 2
        assert config.groups["module.path:GroupClass"].name == "group1"
        assert config.groups["another.module:AnotherGroup"].name == "group2"
        assert config.packages == []
        assert config.env_vars == {}

    def test_full_initialization(self):
        """Test initialization with all fields."""
        config = ServiceConfig(
            name="test-service",
            description="Test service description",
            groups={
                "module.path:GroupClass": GroupConfig(
                    name="group1",
                    description="Group 1 description",
                    class_path="module.path:GroupClass",
                ),
            },
            packages=["shared-package1", "shared-package2"],
            env_vars={"SHARED_ENV1": "value1", "SHARED_ENV2": "value2"},
        )
        assert config.name == "test-service"
        assert config.description == "Test service description"
        assert len(config.groups) == 1
        assert config.groups["module.path:GroupClass"].name == "group1"
        assert config.groups["module.path:GroupClass"].description == "Group 1 description"
        assert config.groups["module.path:GroupClass"].class_path == "module.path:GroupClass"
        assert config.packages == ["shared-package1", "shared-package2"]
        assert config.env_vars == {"SHARED_ENV1": "value1", "SHARED_ENV2": "value2"}


class TestExecutionRequestResponse:
    """Tests for the ExecutionRequest and ExecutionResponse classes."""

    def test_execution_request(self):
        """Test ExecutionRequest initialization and properties."""
        request = ExecutionRequest(
            operation="test_operation",
            arguments={"arg1": "value1", "arg2": 42},
        )
        assert request.operation == "test_operation"
        assert request.arguments == {"arg1": "value1", "arg2": 42}
        assert hasattr(request, "_id")
        assert hasattr(request, "_created_at")

    def test_execution_response(self):
        """Test ExecutionResponse initialization and properties."""
        content = mcp_types.TextContent(type="text", text="Test result")
        response = ExecutionResponse(
            content=content,
            error=None,
        )
        assert response.content == content
        assert response.error is None
        assert hasattr(response, "_id")
        assert hasattr(response, "_created_at")
        assert hasattr(response, "_request_id")

    def test_execution_response_with_error(self):
        """Test ExecutionResponse with error message."""
        content = mcp_types.TextContent(type="text", text="Error occurred")
        response = ExecutionResponse(
            content=content,
            error="Test error message",
        )
        assert response.content == content
        assert response.error == "Test error message"


class TestModelDump:
    """Tests for the model_dump method of ExecutionResponse."""

    def test_model_dump_with_string_content(self):
        """Test model_dump with string content."""
        # Create a response with a string in content
        response = ExecutionResponse(
            content=mcp_types.TextContent(type="text", text="Simple string content"),
        )
        
        # Dump the model and check the result
        dumped = response.model_dump()
        assert dumped["content"]["text"] == "Simple string content"
        
    def test_model_dump_with_pydantic_model(self):
        """Test model_dump with a Pydantic model in content.text."""
        # This test requires mocking the behavior since TextContent normally
        # doesn't accept a Pydantic model directly
        
        class TestModel(BaseModel):
            name: str
            value: int
            
        # Create a test model
        test_model = TestModel(name="test", value=42)
        
        # Create a response with text content
        response = ExecutionResponse(
            content=mcp_types.TextContent(type="text", text="placeholder"),
        )
        
        # Manually set the content.text to be a Pydantic model to test the model_dump method
        # This is a test-only scenario to verify the model_dump logic
        response.content.text = test_model
        
        # Now dump the model and verify it handles the Pydantic model correctly
        dumped = response.model_dump()
        assert isinstance(dumped["content"]["text"], str)
        assert "test" in dumped["content"]["text"]
        assert "42" in dumped["content"]["text"]


class TestServiceRequestResponse:
    """Tests for the ServiceRequest and ServiceResponse classes."""

    def test_service_request(self):
        """Test ServiceRequest initialization and properties."""
        requests = [
            ExecutionRequest(operation="op1", arguments={"arg": "value1"}),
            ExecutionRequest(operation="op2", arguments={"arg": "value2"}),
        ]
        service_request = ServiceRequest(requests=requests)
        assert len(service_request.requests) == 2
        assert service_request.requests[0].operation == "op1"
        assert service_request.requests[1].operation == "op2"

    def test_service_response(self):
        """Test ServiceResponse initialization and properties."""
        content = mcp_types.TextContent(type="text", text="Combined results")
        service_response = ServiceResponse(
            content=content,
            errors=["Error in op1", "Error in op2"],
        )
        assert service_response.content == content
        assert len(service_response.errors) == 2
        assert "Error in op1" in service_response.errors
        assert "Error in op2" in service_response.errors