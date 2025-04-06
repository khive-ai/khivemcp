"""Schema registry for AutoMCP.

This module provides a central registry for Pydantic schemas used in AutoMCP operations,
allowing for schema reuse and discovery.
"""

import inspect
from typing import Any, Dict, List, Optional, Type, get_type_hints

from pydantic import BaseModel


class SchemaRegistry:
    """Registry for Pydantic schemas.

    This class provides a central registry for Pydantic schemas used in
    AutoMCP operations, allowing for schema reuse and discovery.
    """

    def __init__(self):
        """Initialize the schema registry."""
        self.schemas: Dict[str, Type[BaseModel]] = {}

    def register(self, schema: Type[BaseModel], name: str = None) -> None:
        """Register a schema.

        Args:
            schema: The Pydantic schema class
            name: Optional name for the schema, defaults to the schema class name
        """
        if not issubclass(schema, BaseModel):
            raise TypeError(
                f"Schema must be a subclass of BaseModel, got {type(schema)}"
            )

        name = name or schema.__name__
        self.schemas[name] = schema

    def get(self, name: str) -> Optional[Type[BaseModel]]:
        """Get a schema by name.

        Args:
            name: The name of the schema

        Returns:
            The schema class, or None if not found
        """
        return self.schemas.get(name)

    def register_all_from_module(self, module) -> List[str]:
        """Register all schemas from a module.

        This method finds all classes in the module that are subclasses of BaseModel
        and registers them with the registry.

        Args:
            module: The module to scan for schemas

        Returns:
            A list of names of registered schemas
        """
        registered = []
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseModel)
                and obj != BaseModel
            ):
                self.register(obj)
                registered.append(name)
        return registered

    def create_transformer(
        self, schema_name: str, param_name: str = None
    ) -> Any:
        """Create a parameter transformer for a registered schema.

        This method creates a SchemaParameterTransformer for a registered schema,
        which can be used to transform parameters for operations.

        Args:
            schema_name: The name of the registered schema
            param_name: Optional parameter name, defaults to the schema name in lowercase

        Returns:
            A SchemaParameterTransformer instance

        Raises:
            ValueError: If the schema is not found in the registry
        """
        schema = self.get(schema_name)
        if not schema:
            raise ValueError(f"Schema '{schema_name}' not found in registry")

        # Import here to avoid circular imports
        from automcp.testing.transforms import SchemaParameterTransformer

        return SchemaParameterTransformer(schema, param_name)

    def list_schemas(self) -> List[str]:
        """List all registered schema names.

        Returns:
            A list of registered schema names
        """
        return list(self.schemas.keys())

    def get_schema_fields(self, schema_name: str) -> Dict[str, Any]:
        """Get the fields of a registered schema.

        Args:
            schema_name: The name of the registered schema

        Returns:
            A dictionary mapping field names to their types

        Raises:
            ValueError: If the schema is not found in the registry
        """
        schema = self.get(schema_name)
        if not schema:
            raise ValueError(f"Schema '{schema_name}' not found in registry")

        return get_type_hints(schema)
