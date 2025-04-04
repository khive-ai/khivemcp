"""Example service group implementation for AutoMCP verification."""

from automcp.group import ServiceGroup
from automcp.operation import operation


class ExampleGroup(ServiceGroup):
    """A basic example group with simple operations."""

    @operation()
    async def hello_world(self) -> str:
        """Return a simple hello world message.

        Returns:
            str: A hello world message.
        """
        return "Hello, World!"

    @operation()
    async def echo(self, text: str) -> str:
        """Echo the provided text back to the user.

        Args:
            text: The text to echo back.

        Returns:
            str: The echoed text with a prefix.
        """
        return f"Echo: {text}"

    @operation()
    async def count_to(self, number: int) -> str:
        """Return a string with numbers from 1 to the provided number.

        Args:
            number: The number to count up to.

        Returns:
            str: A comma-separated string of numbers from 1 to number.
        """
        return ", ".join(str(i) for i in range(1, number + 1))
