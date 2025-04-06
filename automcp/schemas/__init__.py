"""Schema management for AutoMCP.

This package provides utilities for schema management, validation, and parameter extraction.
It centralizes schema definitions and provides a registry for schema discovery and reuse.
"""

# Import common schemas
from automcp.schemas.common import (
    ListProcessingSchema,
    MessageSchema,
    PersonSchema,
)

# Import registry and validation utilities
from automcp.schemas.registry import SchemaRegistry

# Import testing schemas
from automcp.schemas.testing import (
    TestCaseSchema,
    TestConfigSchema,
    TestSuiteSchema,
)
from automcp.schemas.validation import (
    create_schema_instance,
    extract_schema_parameters,
    validate_schema,
)

__all__ = [
    # Common schemas
    "ListProcessingSchema",
    "MessageSchema",
    "PersonSchema",
    # Testing schemas
    "TestCaseSchema",
    "TestConfigSchema",
    "TestSuiteSchema",
    # Registry
    "SchemaRegistry",
    # Validation utilities
    "create_schema_instance",
    "extract_schema_parameters",
    "validate_schema",
]
