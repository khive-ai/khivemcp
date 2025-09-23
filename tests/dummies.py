"""Test helper groups and models for khivemcp test suite."""

import asyncio

from pydantic import BaseModel

from khivemcp.decorators import operation
from khivemcp.types import DependencyCheck, Readiness, ServiceGroup


class SimpleRequest(BaseModel):
    """Simple request model for testing."""

    value: int


class ComplexRequest(BaseModel):
    """More complex request model for testing."""

    data: dict
    count: int = 1


class GoodGroup(ServiceGroup):
    """A well-behaved service group for testing with dependency validation."""

    async def startup(self):
        """Setup mock dependencies during startup."""
        # Add a healthy database dependency
        self.add_database_dependency(
            name="primary_db",
            check_function=self._check_mock_db,
            required=True,
            timeout_ms=1000,
        )

        # Add optional cache dependency
        self.add_dependency(
            DependencyCheck(
                name="cache_service",
                type="cache",
                check_function=self._check_mock_cache,
                required=False,
                timeout_ms=500,
            )
        )

    async def _check_mock_db(self):
        """Mock database health check - always healthy."""
        await asyncio.sleep(0.001)  # Simulate minimal delay
        return True

    async def _check_mock_cache(self):
        """Mock cache health check - always healthy."""
        await asyncio.sleep(0.001)  # Simulate minimal delay
        return True

    @operation(name="open", schema=SimpleRequest)
    async def open_operation(self, request: SimpleRequest):
        """Open operation requiring no auth or context."""
        return {"result": request.value * 2}

    @operation(
        name="secure", schema=SimpleRequest, accepts_context=True, auth=["write"]
    )
    async def secure_operation(self, ctx, request: SimpleRequest):
        """Secure operation requiring auth and context."""
        user_info = getattr(getattr(ctx, "access_token", None), "sub", "unknown")
        return {"result": request.value * 3, "user": user_info}

    @operation(name="complex", schema=ComplexRequest, auth=["read", "admin"])
    async def complex_operation(self, request: ComplexRequest):
        """Complex operation requiring multiple scopes but no context."""
        return {
            "processed": request.data,
            "multiplied_count": request.count * len(request.data),
        }


class BadGroup(ServiceGroup):
    """A service group that fails during startup and has failing dependencies."""

    async def startup(self):
        """Setup dependencies that will fail."""
        # Add a failing required dependency
        self.add_database_dependency(
            name="failing_db",
            check_function=self._check_failing_db,
            required=True,
            timeout_ms=1000,
        )

        # Then fail startup
        raise RuntimeError("Intentional startup failure for testing")

    async def _check_failing_db(self):
        """Mock failing database check."""
        raise ConnectionError("Database connection failed")

    async def readiness(self) -> Readiness:
        """Override to always return down status for testing."""
        return Readiness(
            name="BadGroup", status="down", details={"error": "startup_failed"}
        )

    @operation(name="fail", schema=SimpleRequest)
    async def failing_operation(self, request: SimpleRequest):
        raise Exception("This operation always fails")


class DegradedGroup(ServiceGroup):
    """A service group with degraded dependencies."""

    async def startup(self):
        """Setup dependencies that will cause degraded status."""
        # Required dependency that's healthy
        self.add_database_dependency(
            name="primary_db",
            check_function=self._check_healthy_db,
            required=True,
            timeout_ms=1000,
        )

        # Optional dependency that fails (causes degraded status)
        self.add_api_dependency(
            name="optional_api",
            check_function=self._check_failing_api,
            required=False,
            timeout_ms=1000,
        )

    async def _check_healthy_db(self):
        """Mock healthy database check."""
        await asyncio.sleep(0.001)
        return True

    async def _check_failing_api(self):
        """Mock failing API check."""
        raise ConnectionError("External API unavailable")

    @operation(name="slow", schema=SimpleRequest)
    async def slow_operation(self, request: SimpleRequest):
        """Operation that works but service is degraded."""
        return {"result": request.value, "warning": "service_degraded"}


class ContextlessGroup(ServiceGroup):
    """A service group with operations that don't use context."""

    @operation(name="simple", schema=SimpleRequest)
    async def simple_operation(self, request: SimpleRequest):
        return {"simple": True, "value": request.value}

    @operation(name="unprotected")
    async def unprotected_operation(self, request):
        """Operation without schema validation."""
        return {"unprotected": True, "request": str(request)}


class NoOperationsGroup(ServiceGroup):
    """A service group with no @operation decorated methods."""

    async def some_method(self):
        return "not an operation"

    def sync_method(self):
        return "also not an operation"
