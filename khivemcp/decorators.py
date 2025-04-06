"""Decorators for khivemcp Service Groups."""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

# Internal metadata attribute key
_KHIVEMCP_OP_META = "__khivemcp_op_meta__"


def operation(
    name: str | None = None,
    description: str | None = None,
    schema: type[BaseModel] = None,
):
    """
    Decorator to mark an async method in an khivemcp group class as an operation.

    This attaches metadata used by the khivemcp server during startup to register
    the method as an MCP tool.

    Args:
        name: The local name of the operation within the group. If None, the
            method's name is used. The final MCP tool name will be
            'group_config_name.local_name'.
        description: A description for the MCP tool. If None, the method's
            docstring is used.
    """
    if name is not None and not isinstance(name, str):
        raise TypeError("operation 'name' must be a string or None.")
    if description is not None and not isinstance(description, str):
        raise TypeError("operation 'description' must be a string or None.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not inspect.isfunction(func):
            # This might happen if applied to non-methods, although intended for methods
            raise TypeError("@khivemcp.operation can only decorate functions/methods.")
        if not inspect.iscoroutinefunction(func):
            raise TypeError(
                f"@khivemcp.operation requires an async function (`async def`), but got '{func.__name__}'."
            )

        op_name = name or func.__name__
        op_desc = (
            description
            or inspect.getdoc(func)
            or f"Executes the '{op_name}' operation."
        )
        if schema is not None:
            # Ensure the schema is a valid BaseModel subclass
            op_desc += f"Input schema: {schema.model_json_schema()}."

        # Store metadata directly on the function object
        setattr(
            func,
            _KHIVEMCP_OP_META,
            {
                "local_name": op_name,
                "description": op_desc,
                "is_khivemcp_operation": True,  # Explicit marker
            },
        )

        # The wrapper primarily ensures metadata is attached.
        # The original function (`func`) is what gets inspected for signature/hints.
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # We don't need complex logic here anymore. The registration process
            # will call the original bound method.
            request = kwargs.get("request")
            if request and schema:
                if isinstance(request, dict):
                    request = schema.model_validate(request)
                if isinstance(request, str):
                    request = schema.model_validate_json(request)

            return await func(*args, request=request)

        # Copy metadata to the wrapper as well, just in case something inspects the wrapper directly
        # (though registration should ideally look at the original func via __wrapped__)
        # setattr(wrapper, _khivemcp_OP_META, getattr(func, _khivemcp_OP_META))
        # Update: functools.wraps should handle copying attributes like __doc__, __name__
        # Let's ensure our custom attribute is also copied if needed, though maybe redundant.
        if hasattr(func, _KHIVEMCP_OP_META):
            setattr(wrapper, _KHIVEMCP_OP_META, getattr(func, _KHIVEMCP_OP_META))

        wrapper.doc = func.__doc__
        return wrapper

    return decorator
