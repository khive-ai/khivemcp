"""Core service group implementation."""

import inspect
import json
import logging
from collections.abc import Callable
from typing import Any, Dict, Optional

import mcp.types as types
from pydantic import BaseModel, ValidationError

from .exceptions import OperationError
from .types import ExecutionRequest, ExecutionResponse


class ServiceGroup:
    """Base class for service groups containing operations.

    A ServiceGroup is a collection of related operations that can be executed
    by an AutoMCPServer. Operations are methods decorated with the @operation
    decorator, which are automatically registered during initialization.

    Attributes:
        registry: A dictionary mapping operation names to their corresponding methods.
        config: A dictionary containing the group's configuration.
    """

    def __init__(self):
        """Initialize the service group and register operations.

        During initialization, all methods decorated with @operation are
        automatically registered in the registry dictionary.
        """
        self.registry: dict[str, Callable] = {}
        self.config: dict[str, Any] = {}  # Store loaded config

        # Register operations
        for name in dir(self):
            method = getattr(self, name)
            if hasattr(method, "is_operation") and method.is_operation:
                self.registry[method.op_name] = method

    @property
    def _is_empty(self) -> bool:
        """Check if group has any registered operations.

        Returns:
            bool: True if the registry is empty, False otherwise.
        """
        return not bool(self.registry)

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute an operation based on the provided request.

        This method looks up the requested operation in the registry,
        executes it with the provided arguments, and returns the result
        as an ExecutionResponse.

        Args:
            request: The execution request containing the operation name and arguments.

        Returns:
            ExecutionResponse: The result of the operation execution.
        """
        operation = self.registry.get(request.operation)
        if not operation:
            error_msg = f"Unknown operation: {request.operation}"
            return ExecutionResponse(
                content=types.TextContent(type="text", text=error_msg),
                error=error_msg,
            )

        # Prepare args
        args = request.arguments or {}

        # If we have a context in the request, add it to the arguments
        if request.context:
            # Find the parameter name that requires context
            sig = inspect.signature(operation)
            for param_name, param in sig.parameters.items():
                if param_name == "ctx" or str(param.annotation).endswith(
                    "Context"
                ):
                    args[param_name] = request.context
                    break

        try:
            # The @operation decorator handles schema validation and ctx injection
            result = await operation(**args)

            # Convert result to TextContent
            response_text = ""
            if isinstance(result, BaseModel):
                response_text = result.model_dump_json()
            elif isinstance(result, (dict, list)):
                response_text = json.dumps(result)
            elif result is not None:
                response_text = str(result)

            return ExecutionResponse(
                content=types.TextContent(type="text", text=response_text),
                error=None,
            )

        except ValidationError as e:
            # Schema validation error from @operation decorator
            error_msg = (
                f"Input validation failed for '{request.operation}': {e}"
            )
            logging.error(error_msg)
            return ExecutionResponse(
                content=types.TextContent(type="text", text=error_msg),
                error=error_msg,
            )
        except Exception as e:
            error_msg = (
                f"Error during '{request.operation}' execution: {str(e)}"
            )
            logging.exception("Operation execution failed:")
            return ExecutionResponse(
                content=types.TextContent(type="text", text=error_msg),
                error=error_msg,
            )
