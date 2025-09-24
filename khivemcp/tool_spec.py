"""Tool specification and collection for two-pass initialization."""

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .decorators import _KHIVEMCP_OP_META

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    """Specification for a khivemcp operation to be registered as an MCP tool."""

    group_name: str
    full_tool_name: str
    bound_method: Callable[..., Awaitable[Any]]
    schema_cls: type | None
    accepts_ctx: bool
    description: str
    auth_required: list[str] | None = None
    rate_limited: bool = False


def collect_tools_from_groups(instantiated_groups) -> list[ToolSpec]:
    """Collect all tools from instantiated groups without registering them.

    Args:
        instantiated_groups: List of (group_instance, group_config) tuples

    Returns:
        List of ToolSpec objects ready for registration
    """
    tool_specs = []
    registered_tool_names = set()

    logger.info("Collecting tools from groups...")

    for group_instance, group_config in instantiated_groups:
        group_name = group_config.name
        group_tools = 0

        # Inspect all members of the group instance
        for member_name, member_value in inspect.getmembers(group_instance):
            # Check if it's an async method with our decorator metadata
            if not (
                inspect.iscoroutinefunction(member_value)
                and hasattr(member_value, _KHIVEMCP_OP_META)
            ):
                continue

            op_meta = getattr(member_value, _KHIVEMCP_OP_META, {})
            if op_meta.get("is_khivemcp_operation") is not True:
                continue

            local_op_name = op_meta.get("local_name")
            if not local_op_name:
                logger.warning(
                    f"Method '{member_name}' in group '{group_name}' decorated but missing local name. Skipping."
                )
                continue

            # Check for duplicate tool names across all groups
            if local_op_name in registered_tool_names:
                logger.error(
                    f"Duplicate MCP tool name '{local_op_name}' detected "
                    f"(from group '{group_name}', method '{member_name}'). Skipping."
                )
                continue

            # Create tool specification
            tool_spec = ToolSpec(
                group_name=group_name,
                full_tool_name=local_op_name,
                bound_method=member_value,
                schema_cls=op_meta.get("schema"),
                accepts_ctx=op_meta.get("accepts_context", False),
                description=op_meta.get(
                    "description", f"Executes the '{local_op_name}' operation."
                ),
                auth_required=op_meta.get("auth_required"),
                rate_limited=op_meta.get("rate_limited", False),
            )

            tool_specs.append(tool_spec)
            registered_tool_names.add(local_op_name)
            group_tools += 1

            logger.debug(f"Collected tool '{local_op_name}' from group '{group_name}'")

        if group_tools == 0:
            logger.info(f"No @operation methods found in group '{group_name}'")
        else:
            logger.debug(f"Collected {group_tools} tools from group '{group_name}'")

    logger.info(f"Total tools collected: {len(tool_specs)}")
    return tool_specs
