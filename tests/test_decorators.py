"""Tests for hivemcp.decorators module."""

import inspect
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from khivemcp.decorators import _KHIVEMCP_OP_META, operation


class TestOperation:
    """Tests for the @operation decorator."""

    async def test_operation_default_params(self):
        """Should decorate function with default parameters."""

        @operation()
        async def test_func(context, request=None):
            """Test docstring."""
            return {"result": "success"}

        # Check metadata
        assert hasattr(test_func, _KHIVEMCP_OP_META)
        meta = getattr(test_func, _KHIVEMCP_OP_META)
        assert meta["is_khivemcp_operation"] is True
        assert meta["local_name"] == "test_func"
        assert "Test docstring." in meta["description"]

        # Check function execution
        context_mock = AsyncMock()
        result = await test_func(context_mock)
        assert result == {"result": "success"}

    async def test_operation_with_explicit_params(self):
        """Should decorate function with explicit name and description."""

        @operation(name="custom_name", description="Custom description")
        async def test_func(context, request=None):
            return {"result": "success"}

        # Check metadata
        assert hasattr(test_func, _KHIVEMCP_OP_META)
        meta = getattr(test_func, _KHIVEMCP_OP_META)
        assert meta["is_khivemcp_operation"] is True
        assert meta["local_name"] == "custom_name"
        assert meta["description"] == "Custom description"

        # Check function execution
        context_mock = AsyncMock()
        result = await test_func(context_mock)
        assert result == {"result": "success"}

    async def test_operation_with_schema(self, test_service_group):
        """Should decorate function with schema and validate requests."""

        class TestSchema(BaseModel):
            name: str
            value: int

        @operation(schema=TestSchema)
        async def test_func(context, request=None):
            return {"request": request}

        # Check metadata
        assert hasattr(test_func, _KHIVEMCP_OP_META)
        meta = getattr(test_func, _KHIVEMCP_OP_META)
        assert meta["is_khivemcp_operation"] is True
        assert "Input schema:" in meta["description"]

        # Test with dict request (should convert to model)
        context_mock = AsyncMock()
        result = await test_func(context_mock, request={"name": "test", "value": 42})
        assert isinstance(result["request"], TestSchema)
        assert result["request"].name == "test"
        assert result["request"].value == 42

        # Test with JSON string request (should convert to model)
        result = await test_func(
            context_mock, request='{"name": "test_json", "value": 100}'
        )
        assert isinstance(result["request"], TestSchema)
        assert result["request"].name == "test_json"
        assert result["request"].value == 100

        # Test with already validated model
        model = TestSchema(name="pre_validated", value=200)
        result = await test_func(context_mock, request=model)
        assert result["request"] == model

    def test_non_async_function(self):
        """Should raise TypeError when decorating non-async function."""

        with pytest.raises(TypeError, match="requires an async function"):

            @operation()
            def test_func(context, request=None):
                return {"result": "success"}

    def test_non_function(self):
        """Should raise TypeError when decorating non-function."""

        with pytest.raises(TypeError, match="can only decorate functions/methods"):
            # Attempting to decorate a class
            @operation()
            class TestClass:
                pass

    def test_invalid_name_type(self):
        """Should raise TypeError when name is not a string."""

        with pytest.raises(TypeError, match="'name' must be a string"):

            @operation(name=123)
            async def test_func(context, request=None):
                return {"result": "success"}

    def test_invalid_description_type(self):
        """Should raise TypeError when description is not a string."""

        with pytest.raises(TypeError, match="'description' must be a string"):

            @operation(description=123)
            async def test_func(context, request=None):
                return {"result": "success"}

    async def test_wrapper_preserves_function_signature(self):
        """Should preserve original function signature in the wrapper."""

        @operation()
        async def test_func(context, param1: str, param2: int = 0, request=None):
            """Test docstring."""
            return {"param1": param1, "param2": param2}

        # Check if wrapper preserves signature
        sig = inspect.signature(test_func)
        assert "context" in sig.parameters
        assert "param1" in sig.parameters
        assert "param2" in sig.parameters
        assert "request" in sig.parameters
        assert sig.parameters["param2"].default == 0

        # Check if wrapper preserves docstring
        assert test_func.__doc__ == "Test docstring."

        # Check function execution
        context_mock = AsyncMock()
        result = await test_func(context_mock, "test", 42)
        assert result == {"param1": "test", "param2": 42}

    async def test_schema_validation_errors(self):
        """Should handle validation errors with schema."""

        class TestSchema(BaseModel):
            name: str
            value: int

        @operation(schema=TestSchema)
        async def test_func(context, request=None):
            return {"request": request}

        context_mock = AsyncMock()

        # Test with invalid dict (missing required field)
        with pytest.raises(Exception):  # Will raise some kind of validation error
            await test_func(context_mock, request={"name": "test"})  # Missing 'value'

        # Test with invalid JSON
        with pytest.raises(Exception):  # Will raise some kind of validation error
            await test_func(context_mock, request='{"name": "test"}')  # Missing 'value'

        # Test with invalid JSON syntax
        with pytest.raises(Exception):  # Will raise some kind of JSON parsing error
            await test_func(context_mock, request="{invalid json}")
