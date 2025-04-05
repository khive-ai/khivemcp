"""
Custom exception hierarchy for the AutoMCP framework.

This module defines the exception classes used throughout the AutoMCP framework,
providing a structured hierarchy for error handling and reporting.
"""


class AutoMCPError(Exception):
    """Base exception for all AutoMCP errors.

    All other exceptions in the framework inherit from this class,
    allowing for catch-all error handling when needed.
    """

    pass


class ConfigError(AutoMCPError):
    """Base class for configuration-related errors.

    This serves as the parent class for more specific configuration
    error types like missing files or format issues.
    """

    pass


class ConfigNotFoundError(ConfigError):
    """Raised when a configuration file cannot be found.

    This exception is raised when attempting to load a configuration
    file that doesn't exist at the specified path.
    """

    pass


class ConfigFormatError(ConfigError):
    """Raised when a configuration file has invalid format or fails validation.

    This can occur due to:
    - Invalid JSON or YAML syntax
    - Missing required fields
    - Type mismatches in configuration values
    - Other validation errors
    """

    pass


class ServerError(AutoMCPError):
    """Errors related to the AutoMCPServer runtime.

    This exception class covers errors that occur during server
    initialization, operation, or shutdown.
    """

    pass


class OperationError(AutoMCPError):
    """Errors that occur during the execution of a specific operation.

    This is raised when an operation fails to execute correctly
    but the error is not covered by more specific exception types.
    """

    pass


class OperationTimeoutError(OperationError):
    """Raised when an operation exceeds its allowed execution time.

    This exception is typically raised by the server when an operation
    takes longer than the configured timeout period to complete.
    """

    pass
