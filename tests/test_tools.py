"""Unit tests for tool wrapper creation and RBAC enforcement."""

import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from khivemcp.tool_spec import ToolSpec
from khivemcp.tools import create_tool_wrapper
from tests.dummies import ComplexRequest, GoodGroup, SimpleRequest


class TestToolWrapper:
    """Test tool wrapper creation and validation."""

    def mk_spec(self, accepts_ctx=False, auth=None, schema=SimpleRequest):
        """Helper to create ToolSpec instances."""
        group = GoodGroup()

        # Choose correct method based on schema and context requirements
        if accepts_ctx:
            bound_method = group.secure_operation  # Requires auth and context
        elif schema == ComplexRequest:
            bound_method = group.complex_operation  # For ComplexRequest schema
        else:
            bound_method = group.open_operation  # Default for SimpleRequest

        return ToolSpec(
            group_name="test_group",
            full_tool_name="test_group_operation",
            bound_method=bound_method,
            schema_cls=schema,
            accepts_ctx=accepts_ctx,
            description="Test operation",
            auth_required=auth,
        )

    async def run_wrapper(self, wrapper, payload, ctx=None):
        """Helper to run wrapper with proper signature."""
        if ctx is not None:
            return await wrapper(ctx=ctx, request=payload)
        else:
            return await wrapper(request=payload)

    def test_schema_coercion_dict_and_str(self):
        """Test that dict and JSON string payloads are properly validated."""
        wrapper = create_tool_wrapper(self.mk_spec())

        # Test with dict payload
        result = asyncio.run(self.run_wrapper(wrapper, {"value": 3}))
        assert result["result"] == 6  # GoodGroup.open_operation multiplies by 2

        # Test with JSON string payload
        result = asyncio.run(self.run_wrapper(wrapper, '{"value": 4}'))
        assert result["result"] == 8

    def test_schema_validation_with_type_adapter(self):
        """Test that TypeAdapter provides fast validation."""
        wrapper = create_tool_wrapper(self.mk_spec(schema=ComplexRequest))

        # Valid complex request
        payload = {"data": {"key": "value"}, "count": 3}
        result = asyncio.run(self.run_wrapper(wrapper, payload))
        assert result["processed"] == {"key": "value"}
        assert result["multiplied_count"] == 3

    def test_schema_invalid_raises_error(self):
        """Test that invalid payloads raise proper validation errors."""
        wrapper = create_tool_wrapper(self.mk_spec())

        # Invalid payload (missing required field)
        with pytest.raises(ValueError, match="Invalid request format"):
            asyncio.run(self.run_wrapper(wrapper, {"wrong_field": "oops"}))

        # Invalid JSON string
        with pytest.raises(ValueError, match="Invalid request format"):
            asyncio.run(self.run_wrapper(wrapper, '{"value": "not_a_number"}'))

    def test_no_schema_passes_through(self):
        """Test that operations without schema pass requests unchanged."""

        # Create async function for testing
        async def passthrough_method(request):
            return {"received": str(request)}

        # Create spec without schema
        spec = ToolSpec(
            group_name="test",
            full_tool_name="test_passthrough",
            bound_method=passthrough_method,
            schema_cls=None,
            accepts_ctx=False,
            description="Test",
            auth_required=None,
        )
        wrapper = create_tool_wrapper(spec)

        # Any payload should pass through unchanged
        result = asyncio.run(self.run_wrapper(wrapper, {"anything": "goes"}))
        assert "anything" in result["received"]


class TestRBACEnforcement:
    """Test Role-Based Access Control enforcement."""

    def mk_token(self, scopes=None, sub="test_user"):
        """Create a mock access token."""
        return SimpleNamespace(
            scopes=scopes or [],
            sub=sub,
            exp=9999999999,
            iat=1000000000,
            iss="test_issuer",
        )

    def mk_context(self, token=None, **kwargs):
        """Create a mock FastMCP Context."""
        ctx = SimpleNamespace(**kwargs)
        if token:
            ctx.access_token = token
        return ctx

    def mk_spec_with_auth(self, auth_required, accepts_ctx=False):
        """Create ToolSpec with auth requirements."""
        group = GoodGroup()
        method = group.secure_operation if accepts_ctx else group.open_operation
        return ToolSpec(
            group_name="secure_group",
            full_tool_name="secure_operation",
            bound_method=method,
            schema_cls=SimpleRequest,
            accepts_ctx=accepts_ctx,
            description="Secure operation",
            auth_required=auth_required,
        )

    def test_no_auth_required_allows_access(self):
        """Test that operations without auth requirements work normally."""
        spec = ToolSpec(
            group_name="open",
            full_tool_name="open_op",
            bound_method=GoodGroup().open_operation,
            schema_cls=SimpleRequest,
            accepts_ctx=False,
            description="Open operation",
            auth_required=None,  # No auth required
        )
        wrapper = create_tool_wrapper(spec)

        # Should work without any context
        result = asyncio.run(wrapper(request={"value": 5}))
        assert result["result"] == 10

    def test_auth_required_denies_without_context(self):
        """Test that auth-required operations deny access without context."""
        spec = self.mk_spec_with_auth(auth_required=["write"])
        wrapper = create_tool_wrapper(spec)

        # Should require context for auth operations (wrapper signature changes)
        # This should fail due to missing ctx parameter
        with pytest.raises(TypeError):
            asyncio.run(wrapper(request={"value": 5}))

    def test_auth_required_denies_without_token(self):
        """Test that auth-required operations deny access without token."""
        spec = self.mk_spec_with_auth(auth_required=["write"])
        wrapper = create_tool_wrapper(spec)

        # Context without token should be denied
        ctx = self.mk_context()  # No token
        with pytest.raises(PermissionError, match="Authentication required"):
            asyncio.run(wrapper(ctx=ctx, request={"value": 5}))

    def test_auth_required_denies_insufficient_scopes(self):
        """Test that operations deny access when token lacks required scopes."""
        spec = self.mk_spec_with_auth(auth_required=["write", "admin"])
        wrapper = create_tool_wrapper(spec)

        # Token with insufficient scopes
        token = self.mk_token(scopes=["read"])  # Missing 'write' and 'admin'
        ctx = self.mk_context(token=token)

        with pytest.raises(PermissionError, match="Missing required scopes"):
            asyncio.run(wrapper(ctx=ctx, request={"value": 5}))

    def test_auth_required_allows_sufficient_scopes(self):
        """Test that operations allow access when token has required scopes."""
        spec = self.mk_spec_with_auth(auth_required=["read"], accepts_ctx=False)
        wrapper = create_tool_wrapper(spec)

        # Token with sufficient scopes
        token = self.mk_token(scopes=["read", "write"])
        ctx = self.mk_context(token=token)

        # Should succeed
        result = asyncio.run(wrapper(ctx=ctx, request={"value": 5}))
        assert result["result"] == 10

    def test_auth_with_context_method_passes_context(self):
        """Test that auth-required methods that accept context receive it properly."""
        spec = self.mk_spec_with_auth(auth_required=["write"], accepts_ctx=True)
        wrapper = create_tool_wrapper(spec)

        # Token with sufficient scopes
        token = self.mk_token(scopes=["write"])
        ctx = self.mk_context(token=token)

        # Should succeed and pass context to underlying method
        result = asyncio.run(wrapper(ctx=ctx, request={"value": 5}))
        assert result["result"] == 15  # secure_operation multiplies by 3
        assert "user" in result  # secure_operation includes user info from context

    def test_auth_without_context_method_works(self):
        """Test that auth wrapper works for methods that don't accept context."""
        spec = self.mk_spec_with_auth(auth_required=["read"], accepts_ctx=False)
        wrapper = create_tool_wrapper(spec)

        token = self.mk_token(scopes=["read"])
        ctx = self.mk_context(token=token)

        # Should work even though underlying method doesn't take ctx
        result = asyncio.run(wrapper(ctx=ctx, request={"value": 7}))
        assert result["result"] == 14  # open_operation multiplies by 2

    def test_multiple_scope_requirements(self):
        """Test operations requiring multiple scopes."""
        spec = self.mk_spec_with_auth(auth_required=["read", "write", "admin"])
        wrapper = create_tool_wrapper(spec)

        # Token with all required scopes
        token = self.mk_token(scopes=["read", "write", "admin", "extra"])
        ctx = self.mk_context(token=token)

        result = asyncio.run(wrapper(ctx=ctx, request={"value": 3}))
        assert result["result"] == 6

        # Token missing one scope
        token_insufficient = self.mk_token(scopes=["read", "write"])  # Missing 'admin'
        ctx_insufficient = self.mk_context(token=token_insufficient)

        with pytest.raises(PermissionError, match="Missing required scopes"):
            asyncio.run(wrapper(ctx=ctx_insufficient, request={"value": 3}))

    def test_wrapper_function_metadata(self):
        """Test that wrapper functions have proper metadata set."""
        spec = self.mk_spec_with_auth(auth_required=["test"])
        wrapper = create_tool_wrapper(spec)

        assert wrapper.__name__ == "secure_operation"
        assert wrapper.__qualname__ == "secure_operation"
        assert wrapper.__doc__ == "Secure operation"

    def test_performance_type_adapter_reuse(self):
        """Test that TypeAdapter is cached for performance."""
        spec = self.mk_spec_with_auth(auth_required=None, accepts_ctx=False)
        wrapper = create_tool_wrapper(spec)

        # Multiple calls should reuse the same TypeAdapter
        payload1 = {"value": 1}
        payload2 = {"value": 2}

        result1 = asyncio.run(wrapper(request=payload1))
        result2 = asyncio.run(wrapper(request=payload2))

        assert result1["result"] == 2
        assert result2["result"] == 4
