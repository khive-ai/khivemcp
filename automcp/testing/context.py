"""Mock context for testing operations with progress reporting."""

import mcp.types as types


class MockContext(types.TextContent):
    """Mock context for testing operations with progress reporting.

    This class provides a mock implementation of the Context interface
    used in MCP operations, allowing for testing of operations that
    require context functionality like progress reporting and logging.

    Attributes:
        progress_updates: A list of (current, total) tuples representing progress updates.
        info_messages: A list of info messages logged during operation execution.
    """

    def __init__(self):
        """Initialize the mock context with empty progress and info lists."""
        super().__init__(type="text", text="")
        self.progress_updates = []
        self.info_messages = []
        self.request_id = None  # Added for compatibility with tests

    def info(self, message: str) -> None:
        """Record an info message.

        Args:
            message: The info message to record.
        """
        self.info_messages.append(message)

    async def report_progress(self, current: int, total: int) -> None:
        """Record a progress update.

        Args:
            current: The current progress value.
            total: The total progress value.
        """
        self.progress_updates.append((current, total))
