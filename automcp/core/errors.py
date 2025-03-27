"""Error types for AutoMCP."""

from typing import Any, Dict, Optional


class AutoMCPError(Exception):
    """Base class for AutoMCP errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}
        super().__init__(message)


class ConfigurationError(AutoMCPError):
    """Configuration-related errors."""

    pass


class ConnectionError(AutoMCPError):
    """Connection-related errors."""

    pass


class OperationError(AutoMCPError):
    """Operation execution errors."""

    pass


class ValidationError(AutoMCPError):
    """Validation-related errors."""

    pass


class ResourceError(AutoMCPError):
    """Resource management errors."""

    pass


class RetryableError(AutoMCPError):
    """Errors that can be retried."""

    pass


class ResourceExhaustedError(ResourceError):
    """Resource pool exhaustion errors."""

    pass
