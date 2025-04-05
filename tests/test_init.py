"""Tests for the public API exposed in automcp/__init__.py."""

import pytest


def test_public_api_imports():
    """Test that all expected objects are available from the package."""
    # Import all objects directly from automcp
    # Verify objects are of the expected types
    import inspect
    from pathlib import Path

    from automcp import (  # Main functionality; Configuration models; Exception classes; Version information
        AutoMCPError,
        AutoMCPServer,
        ConfigError,
        ConfigFormatError,
        ConfigNotFoundError,
        GroupConfig,
        OperationError,
        OperationTimeoutError,
        ServerError,
        ServiceConfig,
        ServiceGroup,
        __version__,
        load_config,
        operation,
        run_server,
    )

    # Check main functionality
    assert callable(load_config)
    assert inspect.isclass(ServiceGroup)
    assert callable(operation)
    assert callable(run_server)
    assert inspect.isclass(AutoMCPServer)

    # Check configuration models
    assert inspect.isclass(GroupConfig)
    assert inspect.isclass(ServiceConfig)

    # Check exception classes
    assert inspect.isclass(AutoMCPError)
    assert inspect.isclass(ConfigError)
    assert inspect.isclass(ConfigFormatError)
    assert inspect.isclass(ConfigNotFoundError)
    assert inspect.isclass(OperationError)
    assert inspect.isclass(OperationTimeoutError)
    assert inspect.isclass(ServerError)

    # Check version information
    assert isinstance(__version__, str)
    assert (
        len(__version__.split(".")) >= 2
    )  # Ensure it has at least major.minor format


def test_all_attribute():
    """Test that __all__ contains all the expected objects."""
    import automcp

    expected_objects = [
        # Main functionality
        "load_config",
        "ServiceGroup",
        "operation",
        "run_server",
        "AutoMCPServer",
        # Configuration models
        "GroupConfig",
        "ServiceConfig",
        # Exception classes
        "AutoMCPError",
        "ConfigError",
        "ConfigFormatError",
        "ConfigNotFoundError",
        "OperationError",
        "OperationTimeoutError",
        "ServerError",
        # Version information
        "__version__",
    ]

    # Check that all expected objects are in __all__
    for obj in expected_objects:
        assert obj in automcp.__all__, f"{obj} should be in automcp.__all__"

    # Check that __all__ doesn't contain unexpected objects
    for obj in automcp.__all__:
        assert (
            obj in expected_objects
        ), f"{obj} is in automcp.__all__ but not expected"


def test_direct_imports():
    """Test importing objects directly from automcp."""
    # These imports should work without errors
    from automcp import (
        AutoMCPError,
        AutoMCPServer,
        ConfigError,
        ConfigFormatError,
        ConfigNotFoundError,
        GroupConfig,
        OperationError,
        OperationTimeoutError,
        ServerError,
        ServiceConfig,
        ServiceGroup,
        __version__,
        load_config,
        operation,
        run_server,
    )
