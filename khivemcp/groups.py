"""Group loading and instantiation logic."""

import importlib
import logging
import sys

from fastmcp.server.auth import AuthProvider

from .types import AuthProviderChoice, GroupConfig, ServiceConfig, ServiceGroup

logger = logging.getLogger(__name__)


def prepare_groups_to_load(
    config: ServiceConfig | GroupConfig,
) -> list[tuple[str, GroupConfig]]:
    """Prepare list of groups to load from configuration.

    Args:
        config: Service or group configuration

    Returns:
        List of (class_path, group_config) tuples
    """
    groups_to_load: list[tuple[str, GroupConfig]] = []

    if isinstance(config, ServiceConfig):
        logger.info(f"Loading groups from ServiceConfig '{config.name}'...")
        group_names = set()

        for group_config in config.groups.values():
            if group_config.name in group_names:
                logger.error(
                    f"Duplicate group name '{group_config.name}'. Group names must be unique."
                )
                sys.exit(1)

            group_names.add(group_config.name)
            groups_to_load.append((group_config.class_path, group_config))

    elif isinstance(config, GroupConfig):
        logger.info(f"Loading single group from GroupConfig '{config.name}'...")
        if not hasattr(config, "class_path") or not config.class_path:
            logger.error(f"GroupConfig '{config.name}' needs 'class_path'.")
            sys.exit(1)

        groups_to_load.append((config.class_path, config))

    else:
        logger.error("Invalid config type.")
        sys.exit(1)

    logger.info(f"Found {len(groups_to_load)} group configuration(s)")
    return groups_to_load


def instantiate_single_group(
    class_path: str, group_config: GroupConfig
) -> ServiceGroup | None:
    """Instantiate a single service group.

    Args:
        class_path: Python import path to the group class
        group_config: Group configuration

    Returns:
        Instantiated ServiceGroup or None if failed
    """
    group_name = group_config.name
    logger.debug(f"Instantiating group '{group_name}' from {class_path}")

    try:
        # Dynamic import
        module_path, class_name = class_path.rsplit(":", 1)
        module = importlib.import_module(module_path)
        group_cls = getattr(module, class_name)

        # Validate inheritance
        if not issubclass(group_cls, ServiceGroup):
            logger.error(f"Class '{class_name}' must inherit from ServiceGroup.")
            return None

        # Instantiate with config
        group_instance = group_cls(config=group_config.config)
        logger.debug(f"Successfully instantiated group '{group_name}'")
        return group_instance

    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(f"Import failed for group '{group_name}' ({class_path}): {e}")
    except Exception as e:
        logger.error(f"Instantiation failed for group '{group_name}': {e}")

    return None


def collect_auth_providers(
    group_instances: list[tuple[ServiceGroup, GroupConfig]],
) -> list[AuthProvider]:
    """Collect all auth providers from instantiated groups.

    Args:
        group_instances: List of (group_instance, group_config) tuples

    Returns:
        List of AuthProvider instances found
    """
    auth_providers = []

    for group_instance, group_config in group_instances:
        group_auth = group_instance.get_fastmcp_auth_provider()
        if group_auth:
            auth_providers.append(group_auth)
            logger.debug(f"Found auth provider from group '{group_config.name}'")

    return auth_providers


def resolve_auth_provider(
    auth_candidates: list[AuthProvider],
    auth_choice: AuthProviderChoice,
) -> AuthProvider | None:
    """Resolve which auth provider to use based on candidates and CLI choice.

    Args:
        auth_candidates: List of available auth providers
        auth_choice: User's auth provider choice

    Returns:
        Selected AuthProvider or None
    """
    if not auth_candidates:
        if auth_choice != "none":
            logger.warning("No auth providers found, but auth was requested")
        return None

    if auth_choice == "none":
        logger.info("Auth disabled by user choice")
        return None

    if auth_choice == "auto":
        # Use first available provider
        provider = auth_candidates[0]
        logger.info(f"Auto-selected first auth provider: {type(provider).__name__}")
        if len(auth_candidates) > 1:
            logger.warning(
                "Multiple auth providers available, using first one. "
                "Use --auth-provider to select explicitly."
            )
        return provider

    # For other auth_choice values, this should not be reached due to CLI validation
    # But handle gracefully by using the first available provider
    logger.warning(
        f"Unexpected auth provider choice '{auth_choice}', using first available provider"
    )
    return auth_candidates[0]


def load_and_instantiate_groups(
    config: ServiceConfig | GroupConfig,
) -> tuple[list[tuple[ServiceGroup, GroupConfig]], list[AuthProvider]]:
    """Load and instantiate all groups from configuration.

    Args:
        config: Service or group configuration

    Returns:
        Tuple of (instantiated_groups, auth_candidates)
    """
    # Prepare groups to load
    groups_to_load = prepare_groups_to_load(config)

    # Instantiate each group
    instantiated_groups = []
    for class_path, group_config in groups_to_load:
        group_instance = instantiate_single_group(class_path, group_config)
        if group_instance:
            instantiated_groups.append((group_instance, group_config))

    logger.info(f"Successfully instantiated {len(instantiated_groups)} group(s)")

    # Collect auth providers
    auth_candidates = collect_auth_providers(instantiated_groups)
    if auth_candidates:
        logger.info(f"Found {len(auth_candidates)} auth provider(s)")

    return instantiated_groups, auth_candidates
