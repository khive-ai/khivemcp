"""Core configuration data models for khivemcp."""

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    name: str = Field(..., description="Name of the dependency")
    type: str = Field(
        ..., description="Type of dependency (database, api, service, etc.)"
    )
    status: Literal["healthy", "degraded", "unhealthy", "unknown"] = Field(
        ..., description="Dependency health status"
    )
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional dependency details"
    )


class DependencyCheck(BaseModel):
    """Configuration for a dependency health check."""

    name: str = Field(..., description="Name of the dependency")
    type: str = Field(
        ..., description="Type of dependency (database, api, service, etc.)"
    )
    check_function: Optional[Callable] = Field(
        None, description="Async function to check dependency health"
    )
    timeout_ms: int = Field(
        5000, description="Timeout for dependency check in milliseconds"
    )
    required: bool = Field(
        True, description="Whether this dependency is required for readiness"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional dependency configuration"
    )

    model_config = {"arbitrary_types_allowed": True}


class Readiness(BaseModel):
    """Enhanced readiness status for a service group with dependency validation."""

    name: str = Field(..., description="Name of the service group")
    status: Literal["ready", "degraded", "down"] = Field(
        ..., description="Overall readiness status"
    )
    dependencies: List[DependencyStatus] = Field(
        default_factory=list, description="Status of all dependencies"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional status details"
    )
    check_duration_ms: Optional[float] = Field(
        None, description="Total time taken for readiness check"
    )

    @property
    def healthy_dependencies(self) -> List[DependencyStatus]:
        """Get list of healthy dependencies."""
        return [dep for dep in self.dependencies if dep.status == "healthy"]

    @property
    def unhealthy_dependencies(self) -> List[DependencyStatus]:
        """Get list of unhealthy dependencies."""
        return [
            dep for dep in self.dependencies if dep.status in ["degraded", "unhealthy"]
        ]

    @property
    def dependency_summary(self) -> Dict[str, int]:
        """Get summary count of dependencies by status."""
        from collections import Counter

        return dict(Counter(dep.status for dep in self.dependencies))


class GroupConfig(BaseModel):
    """Configuration for a single service group instance."""

    name: str = Field(
        ...,
        description="Unique name for this specific group instance (used in MCP tool names like 'name.operation').",
    )
    class_path: str = Field(
        ...,
        description="Full Python import path to the ServiceGroup class (e.g., 'my_module.submodule:MyGroupClass').",
    )
    description: str | None = Field(
        None, description="Optional description of this group instance."
    )
    packages: list[str] = Field(
        default_factory=list,
        description="List of additional Python packages required specifically for this group.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Group-specific configuration dictionary passed to the group's __init__ if it accepts a 'config' argument.",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables specific to this group (currently informational, not automatically injected).",
    )
    # Auth configuration (optional for backward compatibility)
    auth_required: bool = Field(
        default=False,
        description="Whether this group requires authentication. If True, khivemcp will check that the group provides a FastMCP auth provider.",
    )
    auth_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional auth-specific configuration passed to the group for auth setup (e.g., permissions, rate limits).",
    )

    @field_validator("class_path")
    def check_class_path_format(cls, v):
        if ":" not in v or v.startswith(".") or ":" not in v.split(".")[-1]:
            raise ValueError("class_path must be in the format 'module.path:ClassName'")
        return v


class ServiceConfig(BaseModel):
    """Configuration for a service containing multiple named group instances."""

    name: str = Field(..., description="Name of the overall service.")
    description: str | None = Field(
        None, description="Optional description of the service."
    )
    groups: dict[str, GroupConfig] = Field(
        ...,
        description="Dictionary of group configurations. The keys are logical identifiers for the instances within this service config.",
    )
    packages: list[str] = Field(
        default_factory=list,
        description="List of shared Python packages required across all groups in this service.",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Shared environment variables for all groups (currently informational, not automatically injected).",
    )


class ServiceGroup:
    """Base class for khivemcp service groups.

    ServiceGroups can optionally provide:
    - FastMCP authentication via get_fastmcp_auth_provider() method
    - Lifecycle methods (startup/shutdown) for initialization
    - Operation methods decorated with @operation
    """

    def __init__(self, config: dict[str, Any] = None):
        self.group_config = config or {}
        # Optional: Groups can set self.fastmcp_auth_provider to provide auth
        self.fastmcp_auth_provider: AuthProvider | None = None
        # Dependency validation support
        self.dependencies: List[DependencyCheck] = []

    async def startup(self) -> None:
        """Optional lifecycle hook called when the MCP server starts.

        Override this method to initialize resources, connections, or services
        that need to be ready before handling requests.
        """
        pass

    async def shutdown(self) -> None:
        """Optional lifecycle hook called when the MCP server shuts down.

        Override this method to clean up resources, close connections,
        or perform any cleanup tasks.
        """
        pass

    def add_dependency(self, dependency: DependencyCheck) -> None:
        """Add a dependency check to this service group.

        Args:
            dependency: DependencyCheck configuration
        """
        self.dependencies.append(dependency)

    def add_database_dependency(
        self,
        name: str,
        check_function: Callable,
        required: bool = True,
        timeout_ms: int = 5000,
    ) -> None:
        """Convenience method to add a database dependency.

        Args:
            name: Name of the database
            check_function: Async function that checks database connectivity
            required: Whether this database is required for readiness
            timeout_ms: Timeout for the check in milliseconds
        """
        self.add_dependency(
            DependencyCheck(
                name=name,
                type="database",
                check_function=check_function,
                required=required,
                timeout_ms=timeout_ms,
            )
        )

    def add_api_dependency(
        self,
        name: str,
        check_function: Callable,
        required: bool = True,
        timeout_ms: int = 5000,
    ) -> None:
        """Convenience method to add an external API dependency.

        Args:
            name: Name of the external API
            check_function: Async function that checks API availability
            required: Whether this API is required for readiness
            timeout_ms: Timeout for the check in milliseconds
        """
        self.add_dependency(
            DependencyCheck(
                name=name,
                type="api",
                check_function=check_function,
                required=required,
                timeout_ms=timeout_ms,
            )
        )

    async def _check_dependency(self, dependency: DependencyCheck) -> DependencyStatus:
        """Check a single dependency and return its status.

        Args:
            dependency: DependencyCheck to validate

        Returns:
            DependencyStatus with health information
        """
        start_time = asyncio.get_event_loop().time()

        try:
            if dependency.check_function is None:
                return DependencyStatus(
                    name=dependency.name,
                    type=dependency.type,
                    status="unknown",
                    error="No check function provided",
                )

            # Run the check with timeout
            await asyncio.wait_for(
                dependency.check_function(), timeout=dependency.timeout_ms / 1000.0
            )

            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return DependencyStatus(
                name=dependency.name,
                type=dependency.type,
                status="healthy",
                response_time_ms=response_time,
                details=dependency.details,
            )

        except asyncio.TimeoutError:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            return DependencyStatus(
                name=dependency.name,
                type=dependency.type,
                status="unhealthy",
                response_time_ms=response_time,
                error=f"Timeout after {dependency.timeout_ms}ms",
            )

        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            return DependencyStatus(
                name=dependency.name,
                type=dependency.type,
                status="unhealthy",
                response_time_ms=response_time,
                error=str(e),
            )

    async def readiness(self) -> Readiness:
        """Enhanced readiness check with dependency validation.

        This method checks all registered dependencies and determines the overall
        readiness status. Override this method for custom readiness logic,
        or use add_dependency() to register dependency checks.

        Returns:
            Enhanced Readiness status with dependency information
        """
        start_time = asyncio.get_event_loop().time()

        # Check all dependencies concurrently
        dependency_statuses = []
        if self.dependencies:
            dependency_statuses = await asyncio.gather(
                *(self._check_dependency(dep) for dep in self.dependencies),
                return_exceptions=True,
            )

            # Handle any exceptions from dependency checks
            processed_statuses = []
            for i, status in enumerate(dependency_statuses):
                if isinstance(status, Exception):
                    processed_statuses.append(
                        DependencyStatus(
                            name=self.dependencies[i].name,
                            type=self.dependencies[i].type,
                            status="unhealthy",
                            error=f"Dependency check failed: {str(status)}",
                        )
                    )
                else:
                    processed_statuses.append(status)
            dependency_statuses = processed_statuses

        # Determine overall status
        overall_status = "ready"
        required_unhealthy = [
            dep
            for dep, check in zip(dependency_statuses, self.dependencies)
            if check.required and dep.status in ["unhealthy", "unknown"]
        ]

        if required_unhealthy:
            overall_status = "down"
        elif any(
            dep.status in ["degraded", "unhealthy"] for dep in dependency_statuses
        ):
            overall_status = "degraded"

        check_duration = (asyncio.get_event_loop().time() - start_time) * 1000

        # Build summary details
        details = {
            "dependency_count": len(dependency_statuses),
            "required_dependencies": len([d for d in self.dependencies if d.required]),
            "optional_dependencies": len(
                [d for d in self.dependencies if not d.required]
            ),
        }

        if dependency_statuses:
            healthy_count = len(
                [d for d in dependency_statuses if d.status == "healthy"]
            )
            details["healthy_dependencies"] = healthy_count

        return Readiness(
            name=self.__class__.__name__,
            status=overall_status,
            dependencies=dependency_statuses,
            details=details,
            check_duration_ms=check_duration,
        )

    def get_fastmcp_auth_provider(self) -> Optional["AuthProvider"]:
        """Get the FastMCP auth provider for this group.

        Groups can override this method or set self.fastmcp_auth_provider
        to provide authentication. The CLI will use this to configure
        FastMCP server authentication.

        Returns:
            FastMCP AuthProvider instance or None if no auth required
        """
        return self.fastmcp_auth_provider


# CLI Types for better type checking
AuthProviderChoice = Literal["auto", "none"]
TransportType = Literal["stdio", "http", "sse"]
DeploymentMode = Literal["server", "lambda", "worker"]
