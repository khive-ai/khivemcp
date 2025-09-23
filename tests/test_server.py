"""Unit tests for server health and readiness aggregation."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import JSONResponse, PlainTextResponse

from khivemcp.server import add_health_routes, create_fastmcp_server
from khivemcp.types import Readiness, ServiceConfig, ServiceGroup
from tests.dummies import BadGroup, DegradedGroup, GoodGroup


class MockFastMCP:
    """Mock FastMCP server for testing."""

    def __init__(self, name="test", auth=None):
        self.name = name
        self.auth = auth
        self.routes = []
        self.custom_routes = {}

    def custom_route(self, path, methods=None):
        """Mock custom route decorator."""

        def decorator(func):
            self.custom_routes[path] = func
            return func

        return decorator


class TestServerCreation:
    """Test FastMCP server creation."""

    def test_create_server_with_service_config(self):
        """Test server creation with ServiceConfig."""
        config = ServiceConfig(
            name="test_service", description="Test service", groups={}
        )

        # Mock the FastMCP constructor for testing
        with pytest.MonkeyPatch.context() as mp:
            mock_fastmcp = MagicMock()
            mp.setattr("khivemcp.server.FastMCP", lambda **kwargs: mock_fastmcp)

            server = create_fastmcp_server(config)
            assert server is mock_fastmcp

    def test_create_server_with_auth_provider(self):
        """Test server creation with auth provider."""
        config = ServiceConfig(name="test", groups={})
        auth_provider = MagicMock()

        with pytest.MonkeyPatch.context() as mp:
            mock_fastmcp = MagicMock()
            mp.setattr("khivemcp.server.FastMCP", lambda **kwargs: mock_fastmcp)

            server = create_fastmcp_server(config, auth_provider)
            assert server is mock_fastmcp


class TestHealthRoutes:
    """Test health and readiness endpoint functionality."""

    def test_add_health_routes_basic(self):
        """Test that health routes are added to server."""
        mock_server = MockFastMCP()
        add_health_routes(mock_server)

        assert "/health" in mock_server.custom_routes
        assert "/ready" in mock_server.custom_routes

    async def test_health_endpoint_always_ok(self):
        """Test that /health endpoint always returns OK."""
        mock_server = MockFastMCP()
        add_health_routes(mock_server)

        health_handler = mock_server.custom_routes["/health"]
        response = await health_handler(None)

        assert isinstance(response, PlainTextResponse)
        assert response.body == b"OK"
        assert response.status_code == 200

    async def test_ready_endpoint_no_groups(self):
        """Test /ready endpoint with no groups returns simple READY."""
        mock_server = MockFastMCP()
        add_health_routes(mock_server, [])  # Empty groups list

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, PlainTextResponse)
        assert response.body == b"READY"
        assert response.status_code == 200

    async def test_ready_endpoint_all_groups_ready(self):
        """Test /ready endpoint when all groups are ready."""
        good_group1 = GoodGroup()
        good_group2 = GoodGroup()
        groups = [good_group1, good_group2]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

        # Parse response body
        body = json.loads(response.body)
        assert len(body) == 2
        assert all(item["status"] == "ready" for item in body)

    async def test_ready_endpoint_some_groups_down(self):
        """Test /ready endpoint returns 503 when any group is down."""
        good_group = GoodGroup()
        bad_group = BadGroup()
        groups = [good_group, bad_group]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503  # Service unavailable

        body = json.loads(response.body)
        assert len(body) == 2

        # Find the status of each group
        statuses = {item["name"]: item["status"] for item in body}
        assert statuses["GoodGroup"] == "ready"
        assert statuses["BadGroup"] == "down"

    async def test_ready_endpoint_degraded_groups(self):
        """Test /ready endpoint with degraded groups returns 503."""
        good_group = GoodGroup()
        degraded_group = DegradedGroup()

        # Call startup to configure dependencies
        await good_group.startup()
        await degraded_group.startup()

        groups = [good_group, degraded_group]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

        body = json.loads(response.body)
        statuses = {item["name"]: item["status"] for item in body}
        assert statuses["GoodGroup"] == "ready"
        assert statuses["DegradedGroup"] == "degraded"

    async def test_ready_endpoint_group_readiness_exception(self):
        """Test /ready endpoint handles exceptions in group readiness checks."""

        class FailingGroup(ServiceGroup):
            async def readiness(self):
                raise Exception("Readiness check failed")

        failing_group = FailingGroup()
        good_group = GoodGroup()
        groups = [good_group, failing_group]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

        body = json.loads(response.body)
        assert len(body) == 2

        # Check that exception is handled properly
        failing_item = next(item for item in body if item["name"] == "FailingGroup")
        assert failing_item["status"] == "down"
        assert "error" in failing_item

    async def test_ready_endpoint_mixed_group_states(self):
        """Test /ready endpoint with groups in various states."""
        good_group = GoodGroup()
        bad_group = BadGroup()
        degraded_group = DegradedGroup()

        # Call startup to configure dependencies (BadGroup will fail)
        await good_group.startup()
        try:
            await bad_group.startup()
        except RuntimeError:
            pass  # Expected failure
        await degraded_group.startup()

        groups = [good_group, bad_group, degraded_group]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

        body = json.loads(response.body)
        assert len(body) == 3

        statuses = {item["name"]: item["status"] for item in body}
        assert statuses["GoodGroup"] == "ready"
        assert statuses["BadGroup"] == "down"
        assert statuses["DegradedGroup"] == "degraded"

    async def test_ready_endpoint_group_without_readiness_method(self):
        """Test groups without readiness() method are treated as ready."""

        class MinimalGroup(ServiceGroup):
            """Group without readiness method."""

            pass

        minimal_group = MinimalGroup()
        good_group = GoodGroup()
        groups = [minimal_group, good_group]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]
        response = await ready_handler(None)

        assert isinstance(response, JSONResponse)
        assert (
            response.status_code == 200
        )  # Should be OK since both are considered ready

        body = json.loads(response.body)
        assert len(body) == 2

        # Minimal group should be treated as ready
        minimal_item = next(item for item in body if item["name"] == "MinimalGroup")
        assert minimal_item["status"] == "ready"

    def test_readiness_model_validation(self):
        """Test that Readiness model validates properly."""
        # Valid readiness
        readiness = Readiness(name="test", status="ready")
        assert readiness.name == "test"
        assert readiness.status == "ready"
        assert readiness.details == {}

        # With details
        readiness_with_details = Readiness(
            name="test2", status="degraded", details={"db": "slow", "cache": "down"}
        )
        assert readiness_with_details.details["db"] == "slow"

        # Invalid status should fail validation
        with pytest.raises(ValueError):
            Readiness(name="test", status="invalid_status")

    async def test_ready_endpoint_performance_with_many_groups(self):
        """Test readiness check performance with many groups."""
        # Create many groups
        groups = [GoodGroup() for _ in range(20)]

        mock_server = MockFastMCP()
        add_health_routes(mock_server, groups)

        ready_handler = mock_server.custom_routes["/ready"]

        # Time the readiness check
        import time

        start_time = time.time()
        response = await ready_handler(None)
        end_time = time.time()

        # Should complete reasonably quickly
        assert (end_time - start_time) < 1.0  # Less than 1 second

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

        body = json.loads(response.body)
        assert len(body) == 20
        assert all(item["status"] == "ready" for item in body)
