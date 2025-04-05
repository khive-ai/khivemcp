"""
Tests for the custom exception hierarchy in automcp/exceptions.py.
"""

import pytest

from automcp.exceptions import (
    AutoMCPError,
    ConfigError,
    ConfigFormatError,
    ConfigNotFoundError,
    OperationError,
    OperationTimeoutError,
    ServerError,
)


def test_exception_hierarchy():
    """Test that the exception inheritance hierarchy is correct."""
    # Test base exception
    assert issubclass(AutoMCPError, Exception)

    # Test first-level exceptions
    assert issubclass(ConfigError, AutoMCPError)
    assert issubclass(ServerError, AutoMCPError)
    assert issubclass(OperationError, AutoMCPError)

    # Test second-level exceptions
    assert issubclass(ConfigNotFoundError, ConfigError)
    assert issubclass(ConfigFormatError, ConfigError)
    assert issubclass(OperationTimeoutError, OperationError)


def test_exception_instantiation():
    """Test that exceptions can be instantiated with messages."""
    # Test with message
    error_msg = "Test error message"
    exc = AutoMCPError(error_msg)
    assert str(exc) == error_msg

    # Test child classes with message
    config_exc = ConfigError("Configuration error")
    assert str(config_exc) == "Configuration error"

    not_found_exc = ConfigNotFoundError("Config file not found: config.yaml")
    assert str(not_found_exc) == "Config file not found: config.yaml"


def test_exception_catching():
    """Test that exceptions can be caught at different levels of the hierarchy."""
    # Test catching specific exception
    try:
        raise ConfigNotFoundError("Missing config")
    except ConfigNotFoundError as e:
        assert str(e) == "Missing config"

    # Test catching parent exception
    try:
        raise ConfigFormatError("Invalid YAML")
    except ConfigError as e:
        assert str(e) == "Invalid YAML"

    # Test catching base exception
    try:
        raise OperationTimeoutError("Operation timed out after 30s")
    except AutoMCPError as e:
        assert str(e) == "Operation timed out after 30s"


def test_exception_with_cause():
    """Test exceptions with a cause (using from ... raise syntax)."""
    try:
        try:
            raise ValueError("Original error")
        except ValueError as original_error:
            raise ConfigFormatError(
                "Config validation failed"
            ) from original_error
    except ConfigFormatError as e:
        assert str(e) == "Config validation failed"
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "Original error"
