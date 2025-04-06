"""Common schema definitions for AutoMCP.

This module provides common schema definitions that can be reused across
different AutoMCP operations and tests.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PersonSchema(BaseModel):
    """Schema representing a person.

    This schema is used for operations that require information about a person,
    such as name, age, and optional email address.
    """

    name: str = Field(..., description="Person's name")
    age: int = Field(..., description="Person's age")
    email: str | None = Field(None, description="Person's email address")


class MessageSchema(BaseModel):
    """Schema for a message with repetition.

    This schema is used for operations that involve repeating a message
    a specified number of times.
    """

    text: str = Field(..., description="Message text")
    repeat: int = Field(
        1, description="Number of times to repeat the message", ge=1, le=10
    )


class ListProcessingSchema(BaseModel):
    """Schema for processing a list of items.

    This schema is used for operations that process a list of items with
    optional prefix and case transformation.
    """

    items: list[str] = Field(..., description="List of items to process")
    prefix: str | None = Field(
        "Item:", description="Prefix to add to each item"
    )
    uppercase: bool = Field(
        False, description="Whether to convert items to uppercase"
    )
