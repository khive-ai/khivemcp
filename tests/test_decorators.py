"""Unit tests for khivemcp decorators - ensuring metadata-only behavior."""

import asyncio

import pytest
from pydantic import BaseModel

from khivemcp.decorators import _KHIVEMCP_OP_META, operation
from tests.dummies import SimpleRequest


class TestOperationDecorator:
    """Test the @operation decorator functionality."""

    def test_operation_attaches_metadata(self):
        """Test that @operation decorator attaches proper metadata."""

        class TestGroup:
            @operation(
                name="test_op", description="Test operation", schema=SimpleRequest
            )
            async def test_method(self, request: SimpleRequest):
                return request.value

        group = TestGroup()
        method = group.test_method

        # Check that metadata is attached
        assert hasattr(method, _KHIVEMCP_OP_META)
        meta = getattr(method, _KHIVEMCP_OP_META)

        assert meta["local_name"] == "test_op"
        assert "Test operation" in meta["description"]
        assert "Input schema:" in meta["description"]
        assert meta["is_khivemcp_operation"] is True
        assert meta["schema"] is SimpleRequest
        assert meta["auth_required"] is None
        assert meta["rate_limited"] is False

    def test_operation_auto_detects_context_parameter(self):
        """Test that @operation auto-detects ctx parameter in method signature."""

        class TestGroup:
            @operation(name="with_ctx")
            async def method_with_ctx(self, ctx, request):
                return {"has_ctx": True}

            @operation(name="without_ctx")
            async def method_without_ctx(self, request):
                return {"has_ctx": False}

        group = TestGroup()

        with_ctx_meta = getattr(group.method_with_ctx, _KHIVEMCP_OP_META)
        without_ctx_meta = getattr(group.method_without_ctx, _KHIVEMCP_OP_META)

        assert with_ctx_meta["accepts_context"] is True
        assert without_ctx_meta["accepts_context"] is False

    def test_operation_explicit_context_override(self):
        """Test that accepts_context parameter overrides auto-detection."""

        class TestGroup:
            @operation(name="override_ctx", accepts_context=False)
            async def method_with_ctx_override(self, ctx, request):
                return {"overridden": True}

        group = TestGroup()
        meta = getattr(group.method_with_ctx_override, _KHIVEMCP_OP_META)

        assert meta["accepts_context"] is False  # Explicitly overridden

    def test_operation_auth_configuration(self):
        """Test that auth requirements are properly stored."""

        class TestGroup:
            @operation(name="secure", auth=["read", "write"])
            async def secure_method(self, request):
                return {"secure": True}

        group = TestGroup()
        meta = getattr(group.secure_method, _KHIVEMCP_OP_META)

        assert meta["auth_required"] == ["read", "write"]

    def test_operation_preserves_original_function_completely(self):
        """Test that decorator returns original function unchanged (metadata-only)."""

        class TestGroup:
            @operation(name="original")
            async def original_method(self, ctx, request: SimpleRequest):
                # This should receive both ctx and request unchanged
                return {
                    "ctx_received": ctx is not None,
                    "ctx_type": type(ctx).__name__,
                    "request_type": type(request).__name__,
                    "request_value": (
                        request.value if hasattr(request, "value") else None
                    ),
                }

        group = TestGroup()
        method = group.original_method

        # Directly call the decorated method with proper arguments
        result = asyncio.run(
            method(ctx={"test": "context"}, request=SimpleRequest(value=42))
        )

        assert result["ctx_received"] is True
        assert result["ctx_type"] == "dict"
        assert result["request_type"] == "SimpleRequest"
        assert result["request_value"] == 42

    def test_operation_no_schema_coercion_in_decorator(self):
        """Test that decorator doesn't perform any schema coercion (metadata-only)."""

        class TestGroup:
            @operation(name="dict_test", schema=SimpleRequest)
            async def dict_method(self, request):
                # Since decorator is metadata-only, this receives whatever is passed
                return {"received_type": type(request).__name__}

        group = TestGroup()

        # Direct call with dict - decorator doesn't coerce
        result = asyncio.run(group.dict_method(request={"value": 42}))
        assert result["received_type"] == "dict"

        # Direct call with model - decorator doesn't interfere
        result = asyncio.run(group.dict_method(request=SimpleRequest(value=42)))
        assert result["received_type"] == "SimpleRequest"

    def test_operation_validation_errors(self):
        """Test that decorator validates parameters properly."""

        with pytest.raises(TypeError, match="'name' must be a string"):

            @operation(name=123)
            async def bad_name_method(self, request):
                pass

        with pytest.raises(TypeError, match="'description' must be a string"):

            @operation(description=123)
            async def bad_description_method(self, request):
                pass

        with pytest.raises(TypeError, match="'auth' must be a list"):

            @operation(auth="not_a_list")
            async def bad_auth_method(self, request):
                pass

        with pytest.raises(TypeError, match="'rate_limit' must be a boolean"):

            @operation(rate_limit="not_a_bool")
            async def bad_rate_limit_method(self, request):
                pass

    def test_operation_requires_async_function(self):
        """Test that decorator only works with async functions."""

        with pytest.raises(TypeError, match="requires an async function"):

            class TestGroup:
                @operation(name="sync")
                def sync_method(self, request):  # Not async
                    return {"sync": True}

    def test_operation_uses_docstring_as_fallback_description(self):
        """Test that method docstring is used when description not provided."""

        class TestGroup:
            @operation(name="documented")
            async def documented_method(self, request):
                """This is the method docstring."""
                return {"documented": True}

        group = TestGroup()
        meta = getattr(group.documented_method, _KHIVEMCP_OP_META)

        assert "This is the method docstring." in meta["description"]

    def test_operation_name_defaults_to_method_name(self):
        """Test that operation name defaults to method name when not provided."""

        class TestGroup:
            @operation()
            async def my_method_name(self, request):
                return {"named": True}

        group = TestGroup()
        meta = getattr(group.my_method_name, _KHIVEMCP_OP_META)

        assert meta["local_name"] == "my_method_name"

    def test_critical_ctx_preservation(self):
        """CRITICAL: Test that ctx is never dropped by the decorator."""

        class TestGroup:
            @operation(name="ctx_critical", accepts_context=True)
            async def ctx_method(self, ctx, request, extra_param="default"):
                # Verify all parameters are preserved
                return {"ctx": ctx, "request": request, "extra_param": extra_param}

        group = TestGroup()

        # Test that all parameters including ctx are preserved
        test_ctx = {"user": "test_user", "request_id": "123"}
        test_request = SimpleRequest(value=99)

        result = asyncio.run(
            group.ctx_method(ctx=test_ctx, request=test_request, extra_param="custom")
        )

        assert result["ctx"] == test_ctx
        assert result["request"] == test_request
        assert result["extra_param"] == "custom"
