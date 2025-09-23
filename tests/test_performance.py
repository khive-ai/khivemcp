"""Performance tests and benchmarks for khivemcp components."""

import asyncio

import pytest
from pydantic import BaseModel

from khivemcp.tool_spec import ToolSpec
from khivemcp.tools import create_tool_wrapper
from tests.dummies import ComplexRequest, GoodGroup, SimpleRequest


class TestSchemaCoercionPerformance:
    """Benchmark schema coercion with TypeAdapter optimization."""

    def mk_spec(self, schema_cls=SimpleRequest):
        """Helper to create ToolSpec for testing."""
        group = GoodGroup()
        if schema_cls == ComplexRequest:
            bound_method = group.complex_operation
        else:
            bound_method = group.open_operation
        return ToolSpec(
            group_name="perf_test",
            full_tool_name="perf_test_operation",
            bound_method=bound_method,
            schema_cls=schema_cls,
            accepts_ctx=False,
            description="Performance test operation",
        )

    def test_simple_schema_coercion_benchmark(self, benchmark):
        """Benchmark simple schema coercion performance."""
        wrapper = create_tool_wrapper(self.mk_spec())
        payload = {"value": 42}

        def run_coercion():
            return asyncio.run(wrapper(request=payload))

        # Benchmark the coercion
        result = benchmark(run_coercion)
        assert result["result"] == 84

        # Performance target: < 50µs per coercion on reasonable hardware
        # This is just a guideline - actual performance will vary
        assert benchmark.stats["mean"] < 0.001  # Less than 1ms

    def test_complex_schema_coercion_benchmark(self, benchmark):
        """Benchmark complex schema coercion performance."""
        wrapper = create_tool_wrapper(self.mk_spec(ComplexRequest))
        payload = {
            "data": {"key1": "value1", "key2": "value2", "key3": "value3"},
            "count": 5,
        }

        def run_coercion():
            return asyncio.run(wrapper(request=payload))

        result = benchmark(run_coercion)
        assert result["processed"] == payload["data"]

        # Complex schemas should still be reasonably fast
        assert benchmark.stats["mean"] < 0.002  # Less than 2ms

    def test_json_string_coercion_benchmark(self, benchmark):
        """Benchmark JSON string coercion performance."""
        wrapper = create_tool_wrapper(self.mk_spec())
        payload = '{"value": 42}'

        def run_coercion():
            return asyncio.run(wrapper(request=payload))

        result = benchmark(run_coercion)
        assert result["result"] == 84

        # JSON parsing should add minimal overhead
        assert benchmark.stats["mean"] < 0.001  # Less than 1ms

    def test_no_schema_passthrough_benchmark(self, benchmark):
        """Benchmark no-schema passthrough performance."""

        # Create spec without schema
        # Create async passthrough function
        async def passthrough_func(request):
            return {"received": request}

        spec = ToolSpec(
            group_name="perf_test",
            full_tool_name="perf_test_passthrough",
            bound_method=passthrough_func,
            schema_cls=None,
            accepts_ctx=False,
            description="Passthrough test",
        )
        wrapper = create_tool_wrapper(spec)
        payload = {"arbitrary": "data"}

        def run_passthrough():
            return asyncio.run(wrapper(request=payload))

        result = benchmark(run_passthrough)
        assert result["received"] == payload

        # Passthrough should be very fast
        assert benchmark.stats["mean"] < 0.0005  # Less than 0.5ms


class TestConcurrencyPerformance:
    """Test concurrent operation performance."""

    @pytest.mark.asyncio
    async def test_concurrent_schema_coercion(self):
        """Test that concurrent schema coercion performs well."""
        wrapper = create_tool_wrapper(
            ToolSpec(
                group_name="concurrent_test",
                full_tool_name="concurrent_operation",
                bound_method=GoodGroup().open_operation,
                schema_cls=SimpleRequest,
                accepts_ctx=False,
                description="Concurrent test",
            )
        )

        # Create many concurrent requests
        payloads = [{"value": i} for i in range(100)]

        import time

        start_time = time.time()

        # Run all requests concurrently
        tasks = [wrapper(request=payload) for payload in payloads]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Verify results
        assert len(results) == 100
        assert all(
            result["result"] == payload["value"] * 2
            for result, payload in zip(results, payloads)
        )

        # Should complete all 100 requests in reasonable time
        assert total_time < 1.0  # Less than 1 second for 100 requests

        # Average per request should be very fast
        avg_per_request = total_time / 100
        assert avg_per_request < 0.01  # Less than 10ms per request


class TestAuthPerformance:
    """Test authentication and authorization performance."""

    def mk_auth_spec(self, auth_required=["read"]):
        """Helper to create auth-required ToolSpec."""
        group = GoodGroup()
        return ToolSpec(
            group_name="auth_test",
            full_tool_name="auth_test_operation",
            bound_method=group.open_operation,
            schema_cls=SimpleRequest,
            accepts_ctx=False,  # Auth wrapper will add ctx
            description="Auth test operation",
            auth_required=auth_required,
        )

    def test_auth_check_benchmark(self, benchmark, mock_context, mock_token):
        """Benchmark auth check performance."""
        wrapper = create_tool_wrapper(self.mk_auth_spec())
        token = mock_token(scopes=["read", "write"])
        ctx = mock_context(token=token)
        payload = {"value": 10}

        def run_with_auth():
            return asyncio.run(wrapper(ctx=ctx, request=payload))

        result = benchmark(run_with_auth)
        assert result["result"] == 20

        # Auth checks should add minimal overhead
        assert benchmark.stats["mean"] < 0.002  # Less than 2ms

    def test_multiple_scope_auth_benchmark(self, benchmark, mock_context, mock_token):
        """Benchmark auth with multiple required scopes."""
        wrapper = create_tool_wrapper(
            self.mk_auth_spec(auth_required=["read", "write", "admin"])
        )
        token = mock_token(scopes=["read", "write", "admin", "extra"])
        ctx = mock_context(token=token)
        payload = {"value": 15}

        def run_with_multi_scope_auth():
            return asyncio.run(wrapper(ctx=ctx, request=payload))

        result = benchmark(run_with_multi_scope_auth)
        assert result["result"] == 30

        # Multiple scope checks should still be fast
        assert benchmark.stats["mean"] < 0.003  # Less than 3ms


class TestMemoryUsage:
    """Test memory usage patterns."""

    def test_wrapper_creation_memory_efficiency(self):
        """Test that wrapper creation doesn't leak memory."""
        import gc
        import sys

        # Get baseline memory
        gc.collect()
        baseline_objects = len(gc.get_objects())

        # Create many wrappers
        wrappers = []
        for i in range(100):
            spec = ToolSpec(
                group_name=f"test_{i}",
                full_tool_name=f"test_operation_{i}",
                bound_method=GoodGroup().open_operation,
                schema_cls=SimpleRequest,
                accepts_ctx=False,
                description=f"Test operation {i}",
            )
            wrapper = create_tool_wrapper(spec)
            wrappers.append(wrapper)

        # Check memory after creation
        gc.collect()
        after_creation_objects = len(gc.get_objects())

        # Clear wrappers
        wrappers.clear()
        gc.collect()
        after_cleanup_objects = len(gc.get_objects())

        # Memory should not grow excessively
        creation_growth = after_creation_objects - baseline_objects
        cleanup_growth = after_cleanup_objects - baseline_objects

        # Some growth is expected, but cleanup should free most memory
        assert creation_growth > 0  # We did create objects
        assert cleanup_growth < creation_growth * 0.5  # At least 50% cleaned up

    def test_type_adapter_reuse(self):
        """Test that TypeAdapter instances are properly reused."""
        # Create multiple wrappers with the same schema
        specs = []
        wrappers = []

        for i in range(10):
            spec = ToolSpec(
                group_name=f"test_{i}",
                full_tool_name=f"test_operation_{i}",
                bound_method=GoodGroup().open_operation,
                schema_cls=SimpleRequest,  # Same schema for all
                accepts_ctx=False,
                description=f"Test operation {i}",
            )
            specs.append(spec)
            wrappers.append(create_tool_wrapper(spec))

        # All wrappers should work correctly
        for wrapper in wrappers:
            result = asyncio.run(wrapper(request={"value": 5}))
            assert result["result"] == 10

        # This test mainly ensures no exceptions are raised
        # Actual TypeAdapter reuse optimization would require more
        # sophisticated introspection to verify
