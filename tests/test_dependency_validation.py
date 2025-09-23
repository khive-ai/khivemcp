"""Tests for enhanced dependency validation system."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from khivemcp.types import DependencyCheck, DependencyStatus, Readiness, ServiceGroup


class MockTestServiceGroup(ServiceGroup):
    """Test service group with dependency validation."""

    async def startup(self):
        """Setup dependencies during startup."""
        # Add a healthy database dependency
        self.add_database_dependency(
            name="primary_db",
            check_function=self._check_primary_db,
            required=True,
            timeout_ms=2000,
        )

        # Add an external API dependency
        self.add_api_dependency(
            name="external_api",
            check_function=self._check_external_api,
            required=False,
            timeout_ms=3000,
        )

        # Add custom dependency
        self.add_dependency(
            DependencyCheck(
                name="redis_cache",
                type="cache",
                check_function=self._check_redis,
                required=False,
                timeout_ms=1000,
            )
        )

    async def _check_primary_db(self):
        """Mock database health check."""
        await asyncio.sleep(0.01)  # Simulate DB query
        return True

    async def _check_external_api(self):
        """Mock external API health check."""
        await asyncio.sleep(0.02)  # Simulate API call
        return True

    async def _check_redis(self):
        """Mock Redis health check."""
        await asyncio.sleep(0.005)  # Simulate Redis ping
        return True


class MockFailingServiceGroup(ServiceGroup):
    """Service group with failing dependencies."""

    async def startup(self):
        """Setup failing dependencies."""
        self.add_database_dependency(
            name="failing_db", check_function=self._check_failing_db, required=True
        )

        self.add_api_dependency(
            name="slow_api",
            check_function=self._check_slow_api,
            required=False,
            timeout_ms=100,  # Very short timeout
        )

    async def _check_failing_db(self):
        """Mock failing database check."""
        raise ConnectionError("Database connection failed")

    async def _check_slow_api(self):
        """Mock slow API that will timeout."""
        await asyncio.sleep(1.0)  # Will timeout with 100ms limit


class TestDependencyValidation:
    """Test dependency validation functionality."""

    @pytest.mark.asyncio
    async def test_healthy_dependencies(self):
        """Test service group with all healthy dependencies."""
        group = MockTestServiceGroup()
        await group.startup()

        readiness = await group.readiness()

        assert readiness.name == "MockTestServiceGroup"
        assert readiness.status == "ready"
        assert len(readiness.dependencies) == 3
        assert readiness.check_duration_ms is not None
        assert readiness.check_duration_ms > 0

        # Check individual dependencies
        db_dep = next(d for d in readiness.dependencies if d.name == "primary_db")
        assert db_dep.status == "healthy"
        assert db_dep.type == "database"
        assert db_dep.response_time_ms is not None

        api_dep = next(d for d in readiness.dependencies if d.name == "external_api")
        assert api_dep.status == "healthy"
        assert api_dep.type == "api"

        cache_dep = next(d for d in readiness.dependencies if d.name == "redis_cache")
        assert cache_dep.status == "healthy"
        assert cache_dep.type == "cache"

        # Check readiness properties
        assert len(readiness.healthy_dependencies) == 3
        assert len(readiness.unhealthy_dependencies) == 0
        assert readiness.dependency_summary["healthy"] == 3

        # Check details
        assert readiness.details["dependency_count"] == 3
        assert readiness.details["required_dependencies"] == 1
        assert readiness.details["optional_dependencies"] == 2
        assert readiness.details["healthy_dependencies"] == 3

    @pytest.mark.asyncio
    async def test_failing_dependencies(self):
        """Test service group with failing dependencies."""
        group = MockFailingServiceGroup()
        await group.startup()

        readiness = await group.readiness()

        assert readiness.name == "MockFailingServiceGroup"
        assert readiness.status == "down"  # Required dependency failed
        assert len(readiness.dependencies) == 2

        # Check failing database (required)
        db_dep = next(d for d in readiness.dependencies if d.name == "failing_db")
        assert db_dep.status == "unhealthy"
        assert db_dep.error == "Database connection failed"

        # Check slow API (timeout)
        api_dep = next(d for d in readiness.dependencies if d.name == "slow_api")
        assert api_dep.status == "unhealthy"
        assert "Timeout after 100ms" in api_dep.error

        # Check unhealthy dependencies
        assert len(readiness.healthy_dependencies) == 0
        assert len(readiness.unhealthy_dependencies) == 2

    @pytest.mark.asyncio
    async def test_degraded_status(self):
        """Test service group with optional dependency failures (degraded)."""
        group = MockTestServiceGroup()
        await group.startup()

        # Replace one optional dependency with a failing one
        group.dependencies = [
            dep for dep in group.dependencies if dep.name != "redis_cache"
        ]
        group.add_dependency(
            DependencyCheck(
                name="failing_optional",
                type="cache",
                check_function=lambda: asyncio.create_task(self._failing_check()),
                required=False,
            )
        )

        async def _failing_check():
            raise ValueError("Optional service unavailable")

        # Monkey patch the failing check
        group.dependencies[-1].check_function = _failing_check

        readiness = await group.readiness()

        assert readiness.status == "degraded"  # Optional dependency failed
        assert len(readiness.healthy_dependencies) == 2
        assert len(readiness.unhealthy_dependencies) == 1

    @pytest.mark.asyncio
    async def test_no_dependencies(self):
        """Test service group with no dependencies."""
        group = ServiceGroup()

        readiness = await group.readiness()

        assert readiness.name == "ServiceGroup"
        assert readiness.status == "ready"
        assert len(readiness.dependencies) == 0
        assert readiness.details["dependency_count"] == 0

    def test_dependency_status_model(self):
        """Test DependencyStatus model validation."""
        # Valid dependency status
        status = DependencyStatus(
            name="test_db",
            type="database",
            status="healthy",
            response_time_ms=45.2,
            details={"connection_pool": "active"},
        )

        assert status.name == "test_db"
        assert status.type == "database"
        assert status.status == "healthy"
        assert status.response_time_ms == 45.2
        assert status.error is None

        # Unhealthy dependency with error
        unhealthy_status = DependencyStatus(
            name="failing_api",
            type="api",
            status="unhealthy",
            error="Connection refused",
        )

        assert unhealthy_status.status == "unhealthy"
        assert unhealthy_status.error == "Connection refused"

    def test_dependency_check_model(self):
        """Test DependencyCheck model validation."""

        async def mock_check():
            return True

        check = DependencyCheck(
            name="test_service",
            type="service",
            check_function=mock_check,
            timeout_ms=3000,
            required=True,
            details={"endpoint": "http://api.example.com/health"},
        )

        assert check.name == "test_service"
        assert check.type == "service"
        assert check.timeout_ms == 3000
        assert check.required is True
        assert check.details["endpoint"] == "http://api.example.com/health"

    @pytest.mark.asyncio
    async def test_dependency_timeout_handling(self):
        """Test that dependency timeouts are handled correctly."""
        group = ServiceGroup()

        async def slow_check():
            await asyncio.sleep(1.0)  # 1 second delay

        group.add_dependency(
            DependencyCheck(
                name="slow_service",
                type="service",
                check_function=slow_check,
                timeout_ms=100,  # 100ms timeout
                required=True,
            )
        )

        readiness = await group.readiness()

        assert readiness.status == "down"  # Required dependency timed out
        slow_dep = readiness.dependencies[0]
        assert slow_dep.status == "unhealthy"
        assert "Timeout after 100ms" in slow_dep.error
        assert slow_dep.response_time_ms >= 100  # Should be close to timeout value

    @pytest.mark.asyncio
    async def test_concurrent_dependency_checks(self):
        """Test that dependency checks run concurrently."""
        group = ServiceGroup()

        check_order = []

        async def check_1():
            check_order.append("check_1_start")
            await asyncio.sleep(0.1)
            check_order.append("check_1_end")

        async def check_2():
            check_order.append("check_2_start")
            await asyncio.sleep(0.05)
            check_order.append("check_2_end")

        group.add_dependency(
            DependencyCheck(
                name="service_1", type="service", check_function=check_1, required=True
            )
        )
        group.add_dependency(
            DependencyCheck(
                name="service_2", type="service", check_function=check_2, required=True
            )
        )

        start_time = asyncio.get_event_loop().time()
        readiness = await group.readiness()
        end_time = asyncio.get_event_loop().time()

        # Should complete in ~0.1 seconds (concurrent), not 0.15 seconds (sequential)
        assert (end_time - start_time) < 0.15
        assert readiness.status == "ready"
        assert len(readiness.dependencies) == 2

        # Both checks should have started before either finished (concurrent execution)
        check_1_start_idx = check_order.index("check_1_start")
        check_2_start_idx = check_order.index("check_2_start")
        check_2_end_idx = check_order.index("check_2_end")

        assert check_1_start_idx < check_2_end_idx
        assert check_2_start_idx < check_2_end_idx
