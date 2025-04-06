"""Testing-specific schema definitions for AutoMCP.

This module provides schema definitions that are specifically used for testing
AutoMCP operations and components.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TestConfigSchema(BaseModel):
    """Schema for test configuration.

    This schema is used to configure test parameters such as timeout,
    retry count, and verbosity.
    """

    timeout_seconds: float = Field(
        5.0, description="Timeout in seconds for test operations"
    )
    retry_count: int = Field(
        3, description="Number of retries for failed operations", ge=0, le=10
    )
    verbose: bool = Field(
        False, description="Whether to enable verbose logging"
    )


class TestCaseSchema(BaseModel):
    """Schema for a test case.

    This schema represents a single test case with input parameters,
    expected output, and optional metadata.
    """

    name: str = Field(..., description="Name of the test case")
    input_params: Dict[str, Any] = Field(
        ..., description="Input parameters for the test case"
    )
    expected_output: Any = Field(
        ..., description="Expected output for the test case"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for the test case"
    )


class TestSuiteSchema(BaseModel):
    """Schema for a test suite.

    This schema represents a collection of test cases with configuration
    and metadata.
    """

    name: str = Field(..., description="Name of the test suite")
    description: str = Field("", description="Description of the test suite")
    config: TestConfigSchema = Field(
        default_factory=TestConfigSchema,
        description="Test suite configuration",
    )
    test_cases: List[TestCaseSchema] = Field(
        ..., description="List of test cases in the suite"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata for the test suite",
    )
