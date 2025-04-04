"""Integration tests for Phase 1: Core FastMCP Integration."""

import asyncio
from typing import Any, Dict, List, Optional

import mcp.types as types
import pytest
from mcp.server.fastmcp import Context, Image
from pydantic import BaseModel

from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.server import AutoMCPServer
from automcp.types import GroupConfig, ServiceConfig

# Use our custom implementation instead of the MCP one
from tests.integration import create_connected_server_and_client_session


# Test schemas
class TextInputSchema(BaseModel):
    """Simple text input schema."""

    text: str
    count: Optional[int] = 1


class ImageInputSchema(BaseModel):
    """Image generation input schema."""

    width: int
    height: int
    color: str = "blue"


class MixedOutputSchema(BaseModel):
    """Schema for mixed output types."""

    text: str
    count: int
    tags: List[str]


# Test service groups
class BasicServiceGroup(ServiceGroup):
    """Basic service group with simple operations."""

    @operation()
    async def simple_text(self, text: str) -> str:
        """Return simple text without using Context."""
        return f"Echo: {text}"

    @operation(schema=TextInputSchema)
    async def schema_text(self, data: TextInputSchema) -> str:
        """Return text using schema validation."""
        result = ""
        for _ in range(data.count):
            result += data.text + " "
        return result.strip()

    @operation()
    async def error_operation(self) -> str:
        """Operation that raises an error."""
        raise ValueError("This is a test error")

    @operation()
    async def slow_operation(self, seconds: float) -> str:
        """Slow operation for testing timeouts."""
        await asyncio.sleep(seconds)
        return f"Completed after {seconds} seconds"


class ContextServiceGroup(ServiceGroup):
    """Service group with Context-aware operations."""

    @operation()
    async def context_aware(self, text: str, ctx: Context) -> str:
        """Operation that uses Context for logging."""
        ctx.info(f"Processing: {text}")
        await ctx.report_progress(50, 100)
        ctx.debug("50% complete")
        await asyncio.sleep(0.1)
        await ctx.report_progress(100, 100)
        ctx.info("Processing complete")
        return f"Processed: {text}"

    @operation(schema=TextInputSchema)
    async def schema_with_context(self, data: TextInputSchema, ctx: Context) -> str:
        """Operation that uses both schema and Context."""
        ctx.info(f"Processing with count: {data.count}")
        result = ""
        for i in range(data.count):
            await ctx.report_progress(i + 1, data.count)
            result += data.text + " "
            await asyncio.sleep(0.05)
        return result.strip()


class ReturnTypesServiceGroup(ServiceGroup):
    """Service group with various return types."""

    @operation()
    async def return_image(self, width: int, height: int, color: str) -> Image:
        """Return an image."""
        # Create a simple colored image
        return Image(
            width=width,
            height=height,
            format="png",
            data=b"mock-image-data",  # In a real test, this would be actual image data
        )

    @operation(schema=ImageInputSchema)
    async def schema_return_image(self, data: ImageInputSchema) -> Image:
        """Return an image using schema validation."""
        return Image(
            width=data.width,
            height=data.height,
            format="png",
            data=b"mock-image-data",  # In a real test, this would be actual image data
        )

    @operation()
    async def return_mixed(self, text: str, count: int) -> MixedOutputSchema:
        """Return a Pydantic model."""
        return MixedOutputSchema(
            text=text, count=count, tags=["test", "mixed", "output"]
        )

    @operation()
    async def return_list(self, items: List[str]) -> List[str]:
        """Return a list of strings."""
        return [item.upper() for item in items]

    @operation()
    async def return_mixed_types(self, text: str, width: int, height: int) -> List[Any]:
        """Return a list with mixed content types (text and image)."""
        return [
            f"Text: {text}",
            Image(width=width, height=height, format="png", data=b"mock-image-data"),
        ]


# Test fixtures
@pytest.fixture
def basic_group_config():
    """Create a basic group configuration."""
    return GroupConfig(
        name="basic",
        description="Basic operations group",
        packages=[],
    )


@pytest.fixture
def context_group_config():
    """Create a context-aware group configuration."""
    return GroupConfig(
        name="context",
        description="Context-aware operations group",
        packages=[],
    )


@pytest.fixture
def return_types_group_config():
    """Create a return types group configuration."""
    return GroupConfig(
        name="return_types",
        description="Various return types group",
        packages=[],
    )


@pytest.fixture
def service_config():
    """Create a service configuration with all test groups."""
    return ServiceConfig(
        name="test-service",
        description="Test service for integration tests",
        packages=[],
        groups={
            "tests.integration.test_phase1_integration:BasicServiceGroup": GroupConfig(
                name="basic",
                description="Basic operations group",
            ),
            "tests.integration.test_phase1_integration:ContextServiceGroup": GroupConfig(
                name="context",
                description="Context-aware operations group",
            ),
            "tests.integration.test_phase1_integration:ReturnTypesServiceGroup": GroupConfig(
                name="return_types",
                description="Various return types group",
            ),
        },
    )


# Integration tests
@pytest.mark.asyncio
async def test_basic_operations():
    """Test basic operations without Context."""
    async with create_connected_server_and_client_session(
        server_factory=lambda: AutoMCPServer(
            name="test-server",
            config=GroupConfig(
                name="basic",
                description="Basic operations group",
            ),
        ),
        server_groups={"basic": BasicServiceGroup()},
    ) as (server, client):
        # Test simple text operation
        response = await client.call_tool("basic.simple_text", {"text": "hello"})
        assert response.content.text == "Echo: hello"

        # Test schema validation
        response = await client.call_tool(
            "basic.schema_text", {"text": "repeat", "count": 3}
        )
        assert response.content.text == "repeat repeat repeat"

        # Test error handling
        response = await client.call_tool("basic.error_operation", {})
        assert "error" in response.content.text.lower()
        assert "test error" in response.content.text

        # Test invalid schema
        response = await client.call_tool("basic.schema_text", {"invalid": "value"})
        assert "error" in response.content.text.lower()


@pytest.mark.asyncio
async def test_context_operations():
    """Test operations with Context injection."""
    async with create_connected_server_and_client_session(
        server_factory=lambda: AutoMCPServer(
            name="test-server",
            config=GroupConfig(
                name="context",
                description="Context-aware operations group",
            ),
        ),
        server_groups={"context": ContextServiceGroup()},
    ) as (server, client):
        # Test context-aware operation
        response = await client.call_tool(
            "context.context_aware", {"text": "test message"}
        )
        assert response.content.text == "Processed: test message"

        # Test schema with context
        response = await client.call_tool(
            "context.schema_with_context", {"text": "repeat", "count": 3}
        )
        assert response.content.text == "repeat repeat repeat"


@pytest.mark.asyncio
async def test_return_types():
    """Test various return types."""
    async with create_connected_server_and_client_session(
        server_factory=lambda: AutoMCPServer(
            name="test-server",
            config=GroupConfig(
                name="return_types",
                description="Various return types group",
            ),
        ),
        server_groups={"return_types": ReturnTypesServiceGroup()},
    ) as (server, client):
        # Test image return
        response = await client.call_tool(
            "return_types.return_image", {"width": 100, "height": 100, "color": "red"}
        )
        assert response.content.type == "image"

        # Test schema with image return
        response = await client.call_tool(
            "return_types.schema_return_image",
            {"width": 200, "height": 150, "color": "green"},
        )
        assert response.content.type == "image"
        assert response.content.width == 200
        assert response.content.height == 150

        # Test Pydantic model return
        response = await client.call_tool(
            "return_types.return_mixed", {"text": "test", "count": 5}
        )
        assert response.content.type == "text"
        assert "test" in response.content.text
        assert "5" in response.content.text
        assert "tags" in response.content.text

        # Test list return
        response = await client.call_tool(
            "return_types.return_list", {"items": ["a", "b", "c"]}
        )
        assert response.content.type == "text"
        assert "A" in response.content.text
        assert "B" in response.content.text
        assert "C" in response.content.text

        # Test mixed types return
        response = await client.call_tool(
            "return_types.return_mixed_types",
            {"text": "mixed", "width": 50, "height": 50},
        )
        # This should return a list with text and image
        # The exact format depends on how FastMCP handles mixed returns
        assert response is not None


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout handling."""
    async with create_connected_server_and_client_session(
        server_factory=lambda: AutoMCPServer(
            name="test-server",
            config=GroupConfig(
                name="basic",
                description="Basic operations group",
            ),
            timeout=0.5,  # Short timeout for testing
        ),
        server_groups={"basic": BasicServiceGroup()},
    ) as (server, client):
        # Test operation that completes within timeout
        response = await client.call_tool("basic.slow_operation", {"seconds": 0.1})
        assert "Completed after 0.1 seconds" in response.content.text

        # Test operation that exceeds timeout
        response = await client.call_tool("basic.slow_operation", {"seconds": 1.0})
        assert "timeout" in response.content.text.lower()


@pytest.mark.asyncio
async def test_full_service_integration():
    """Test full service integration with multiple groups."""
    # Create a server with a simple config first, then register groups manually
    async with create_connected_server_and_client_session(
        server_factory=lambda: AutoMCPServer(
            name="test-service",
            config=ServiceConfig(
                name="test-service",
                description="Test service for integration tests",
                packages=[],
                groups={},  # Empty groups, we'll register them manually
            ),
        ),
        server_groups={
            "basic": BasicServiceGroup(),
            "context": ContextServiceGroup(),
            "return_types": ReturnTypesServiceGroup(),
        },
    ) as (server, client):
        # Test tools listing
        tools = await client.list_tools()
        assert len(tools) >= 9  # At least 9 tools across all groups

        # Verify tool names from each group
        tool_names = [tool.name for tool in tools]
        assert "basic.simple_text" in tool_names
        assert "context.context_aware" in tool_names
        assert "return_types.return_image" in tool_names

        # Test one operation from each group
        response = await client.call_tool("basic.simple_text", {"text": "integration"})
        assert response.content.text == "Echo: integration"

        response = await client.call_tool(
            "context.context_aware", {"text": "with context"}
        )
        assert response.content.text == "Processed: with context"

        response = await client.call_tool(
            "return_types.return_mixed", {"text": "pydantic", "count": 42}
        )
        assert "pydantic" in response.content.text
        assert "42" in response.content.text


@pytest.mark.asyncio
async def test_backward_compatibility():
    """Test backward compatibility with operations that don't use Context."""
    # Create a server with both context-aware and non-context operations
    async with create_connected_server_and_client_session(
        server_factory=lambda: AutoMCPServer(
            name="test-server",
            config=GroupConfig(
                name="mixed",
                description="Mixed operations group",
            ),
        ),
        server_groups={
            "mixed": BasicServiceGroup(),  # This group doesn't use Context
        },
    ) as (server, client):
        # Verify that operations without Context still work
        response = await client.call_tool(
            "mixed.simple_text", {"text": "backward compatible"}
        )
        assert response.content.text == "Echo: backward compatible"

        # Verify schema validation still works
        response = await client.call_tool(
            "mixed.schema_text", {"text": "validated", "count": 2}
        )
        assert response.content.text == "validated validated"
