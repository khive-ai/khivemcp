from typing import List

from mcp.types import TextContent as Context

from automcp.group import ServiceGroup
from automcp.operation import operation
from automcp.schemas import ListProcessingSchema, MessageSchema, PersonSchema


class SchemaGroup(ServiceGroup):
    """Group demonstrating the use of Pydantic schemas for input validation."""

    @operation(schema=PersonSchema)
    async def greet_person(self, person: PersonSchema) -> str:
        """Greet a person based on their information."""
        greeting = f"Hello, {person.name}! "
        if person.age:
            greeting += f"You are {person.age} years old. "
        if person.email:
            greeting += f"Your email is {person.email}."
        return greeting

    @operation(schema=MessageSchema)
    async def repeat_message(
        self, message: MessageSchema, ctx: Context
    ) -> str:
        """Repeat a message a specified number of times with progress reporting."""
        ctx.info(f"Repeating message {message.repeat} times")
        result = []
        for i in range(message.repeat):
            await ctx.report_progress(i + 1, message.repeat)
            result.append(message.text)
        return " ".join(result)

    @operation(schema=ListProcessingSchema)
    async def process_list(self, data: ListProcessingSchema) -> list[str]:
        """Process a list of items according to the parameters."""
        result = []
        for item in data.items:
            processed = item
            if data.uppercase:
                processed = processed.upper()
            result.append(f"{data.prefix} {processed}")
        return result
