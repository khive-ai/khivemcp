"""Simple test group for validating khivemcp implementation."""

import logging

from pydantic import BaseModel

from khivemcp.decorators import operation
from khivemcp.types import ServiceGroup

logger = logging.getLogger(__name__)


class SimpleRequest(BaseModel):
    """Simple request schema for testing."""

    message: str
    count: int = 1


class SimpleGroup(ServiceGroup):
    """A simple test group with basic operations."""

    async def startup(self) -> None:
        """Initialize the simple group."""
        logger.info("SimpleGroup starting up...")

    async def shutdown(self) -> None:
        """Cleanup the simple group."""
        logger.info("SimpleGroup shutting down...")

    @operation(
        name="echo",
        description="Echo a message back with optional repetition",
        schema=SimpleRequest,
    )
    async def echo_message(self, request: SimpleRequest) -> dict:
        """Echo the message back."""
        result = {
            "original_message": request.message,
            "count": request.count,
            "echoed": [request.message] * request.count,
        }
        logger.info(f"Echoing message: {request.message} (x{request.count})")
        return result

    @operation(name="ping", description="Simple ping operation")
    async def ping(self, request: dict) -> dict:
        """Simple ping operation."""
        return {"status": "ok", "message": "pong", "received": request}
