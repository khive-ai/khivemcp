Okay, Aether. Let's dive deep into a detailed, exhaustive guide for your LLM team on refactoring the AutoMCP framework. This will involve restructuring the core package, integrating essential functions previously shown in examples/verification, removing redundancies, and enhancing robustness, all aimed at creating a solid foundation for building agent-focused MCP servers within the Khive-Code project.

---

**Khive-Code: Comprehensive AutoMCP Framework Refactoring Guide**

**Version:** 1.0
**Date:** 2024-07-28

**Document Purpose:**
This document provides a detailed plan and implementation guidance for refactoring the core `automcp` package. The goal is to create a more robust, maintainable, and developer-friendly (especially for AI agents) framework by centralizing essential logic, removing redundancy, and clarifying component roles based on the provided initial code snippets and best practices. This guide is intended for the Khive-Code LLM development team (@automcp-implementer, @automcp-tester, @automcp-designer, @automcp-orchestrator).

**Table of Contents:**

1.  **Motivation for Refactoring**
2.  **Analysis of Current Structure (Based on Snippets)**
3.  **High-Level Refactoring Goals**
4.  **Proposed Core Package Structure (`automcp/`)**
5.  **Detailed Refactoring Steps:**
    *   5.1. Deprecate and Remove `ServiceManager` (`manager.py`)
    *   5.2. Enhance `AutoMCPServer` (`server.py`)
        *   Integrate Timeout Handling
        *   Refine Initialization (Config Handling)
        *   Improve Error Reporting
    *   5.3. Centralize Configuration Loading (`config.py`, formerly `utils.py`)
    *   5.4. Create Core Server Runner (`runner.py`)
    *   5.5. Define Custom Exceptions (`exceptions.py`)
    *   5.6. Refine Core Types (`types.py`)
    *   5.7. Solidify `ServiceGroup` and `@operation` (`group.py`, `operation.py`)
    *   5.8. Structure `__init__.py` for Public API
    *   5.9. Update the CLI (`cli.py`) - Make it a Thin Wrapper
    *   5.10. Adapt Verification & Example Code
6.  **Testing Strategy for Refactoring**
7.  **Guidance for LLM Team Roles During Refactoring**
8.  **Expected Benefits**

---

**1. Motivation for Refactoring**

The initial code snippets demonstrate a functional AutoMCP concept but distribute core server lifecycle management (config loading, server instantiation, running) across CLI tools and verification scripts. The `ServiceManager` introduces potential redundancy with `AutoMCPServer`. To build scalable and maintainable microservices for Khive-Code, especially those used by AI agents, we need a cleaner, more centralized, and programmatically accessible core framework.

**2. Analysis of Current Structure (Based on Snippets)**

*   **Core Logic:** `ServiceGroup`, `@operation`, `AutoMCPServer`, `GroupConfig`, `ServiceConfig`, `load_config` are clearly essential.
*   **Redundancy:** `ServiceManager` appears to duplicate execution and timeout logic potentially better handled within `AutoMCPServer`.
*   **Scattered Startup:** Server creation and execution logic resides in `cli.py` and example runners (`verification/run_*.py`), making programmatic server management difficult.
*   **Testing Utilities:** `MockContext` is necessary for testing but shouldn't be intertwined with core runtime logic (`group.py`).

**3. High-Level Refactoring Goals**

*   Consolidate all essential server lifecycle logic within the core `automcp` package.
*   Provide a simple, high-level function (e.g., `automcp.run_server`) as the primary entry point for starting servers.
*   Eliminate redundancy by removing `ServiceManager` and integrating its necessary features (timeout) into `AutoMCPServer`.
*   Clearly separate the core framework from examples, verification code, and testing utilities.
*   Improve error handling and reporting within the server.
*   Make the framework more intuitive for both human developers and AI agents to use for building and running services.

**4. Proposed Core Package Structure (`automcp/`)**

```
automcp/                     # Root of the core AutoMCP package
├── __init__.py            # Exposes public API: run_server, ServiceGroup, operation, etc.
├── server.py              # Enhanced AutoMCPServer class
├── group.py               # ServiceGroup base class
├── operation.py           # @operation decorator
├── types.py               # Core Pydantic models: GroupConfig, ServiceConfig, internal request/response if needed
├── config.py              # load_config utility function
├── runner.py              # Core run_server function and async helpers
├── exceptions.py          # Custom exceptions (ConfigError, ServerError, OperationError)
└── testing/               # Optional: Utilities specifically for testing AutoMCP services
    ├── __init__.py
    └── context.py         # MockContext moved here
```

**5. Detailed Refactoring Steps**

---

**5.1. Deprecate and Remove `ServiceManager` (`manager.py`)**

*   **Action:** Delete the file `automcp/manager.py`.
*   **Rationale:** Its core responsibilities (executing group operations, handling timeouts) overlap significantly with `AutoMCPServer`. Centralizing this logic in `AutoMCPServer` simplifies the architecture. The multi-request `ServiceRequest` concept it implies isn't standard for MCP `call_tool`, which typically handles one operation call at a time.
*   **Implications:** Any code currently using `ServiceManager` needs to be updated to use `AutoMCPServer` directly or the new `automcp.run_server` function. Timeout handling logic needs to be added to `AutoMCPServer`.

---

**5.2. Enhance `AutoMCPServer` (`server.py`)**

*   **Action 1: Integrate Timeout Handling:** Modify the `_handle_service_request` method (or the point where it calls the group's execute method) to use `asyncio.wait_for`.
*   **Rationale:** Consolidates timeout logic previously in `ServiceManager` into the central server component.
*   **Implementation Snippet (Inside `AutoMCPServer._handle_service_request`):**
    ```python
    # server.py (within AutoMCPServer._handle_service_request)
    import asyncio
    from .exceptions import OperationTimeoutError # Assuming custom exceptions
    # ... other imports ...

    async def _handle_service_request(
        self, group_name: str, request: ServiceRequest # Keep ServiceRequest if handling list internally? Or simplify?
                                                    # Let's assume _handle_service_request now processes a SINGLE ExecutionRequest
                                                    # from handle_call_tool for simplicity aligned with MCP standard.
    ) -> ServiceResponse: # Or ExecutionResponse if handling single call

        # Refined logic assuming handle_call_tool passes a single ExecutionRequest
        group = self.groups.get(group_name)
        if not group:
            # Return ExecutionResponse for a single call error
            error_msg = f"Group not found: {group_name}"
            return ExecutionResponse(
                content=types.TextContent(type="text", text=error_msg),
                error=error_msg
            )

        # Assuming request is now a single ExecutionRequest from handle_call_tool
        single_request = request.requests[0] # Adapt if handling ServiceRequest differently

        try:
            # Wrap the actual execution call with wait_for
            # Assuming group.execute handles a single ExecutionRequest
            response: ExecutionResponse = await asyncio.wait_for(
                group.execute(single_request), # Pass the single request
                timeout=self.timeout
            )
            return response

        except asyncio.TimeoutError:
            error_msg = f"Operation '{group_name}.{single_request.operation}' timed out after {self.timeout} seconds."
            # Return an ExecutionResponse indicating timeout
            return ExecutionResponse(
                content=types.TextContent(type="text", text=error_msg),
                error=error_msg,
                _request_id=single_request._id # Link back to request ID if applicable
            )
        except Exception as e:
            # Handle other execution errors within the operation
            error_msg = f"Error executing operation '{group_name}.{single_request.operation}': {str(e)}"
            logging.exception(f"Operation execution error:") # Log full traceback
            return ExecutionResponse(
                content=types.TextContent(type="text", text=error_msg),
                error=error_msg,
                _request_id=single_request._id
            )

    ```
*   **Action 2: Refine Initialization:** Ensure the `__init__` method correctly handles being passed either a `GroupConfig` or a `ServiceConfig` and calls the appropriate internal initialization (`_init_single_group` or `_init_service_groups`).
*   **Rationale:** Makes server creation more flexible and robust based on the configuration type.
*   **Implementation Snippet (Inside `AutoMCPServer.__init__`):**
    ```python
    # server.py (within AutoMCPServer.__init__)
    from .types import GroupConfig, ServiceConfig
    # ... other imports ...

    def __init__(
        self,
        name: str,
        config: ServiceConfig | GroupConfig, # Accept either type
        timeout: float = 30.0,
    ):
        self.name = name
        # Store raw config for potential reference
        self.raw_config = config
        self.timeout = timeout
        self.server = Server(name) # Assuming Server is from mcp.server
        self.groups: dict[str, ServiceGroup] = {}

        # Initialize groups based on config type
        if isinstance(config, ServiceConfig):
            self._init_service_groups(config) # Pass config explicitly
        elif isinstance(config, GroupConfig):
            self._init_single_group(config) # Pass config explicitly
        else:
            raise TypeError("Configuration must be ServiceConfig or GroupConfig")

        self._setup_handlers() # Setup MCP handlers

    def _init_service_groups(self, service_config: ServiceConfig) -> None:
        """Initialize groups from service config."""
        # ... (Implementation remains similar, but takes service_config as arg) ...
        for class_path, group_config in service_config.groups.items():
             # ... (rest of the logic) ...
             self.groups[group_config.name] = group

    def _init_single_group(self, group_config: GroupConfig) -> None:
        """Initialize single group from group config."""
         # Dynamically load the group class if specified via path,
         # otherwise assume a default or contextually provided group class
         # This part might need adjustment based on how single groups are defined/loaded
         # For now, assuming group needs manual instantiation or default ServiceGroup
        from .group import ServiceGroup # Ensure ServiceGroup is importable
        group = ServiceGroup() # Or dynamically load if path is provided somehow
        group.config = group_config # Attach config
        self.groups[group_config.name] = group
        print(f"Initialized single group: {group_config.name}")


    ```
*   **Action 3: Improve Error Reporting:** Ensure that exceptions during operation execution (`group.execute`) are caught and transformed into structured `ExecutionResponse` objects with the `error` field populated, rather than potentially crashing the `call_tool` handler.
*   **Rationale:** Provides clearer error feedback to the MCP client/agent.
*   **Implementation:** Already incorporated into the timeout handling snippet above (the final `except Exception as e`).

---

**5.3. Centralize Configuration Loading (`config.py`)**

*   **Action:** Move the `load_config` function from `utils.py` to a dedicated `automcp/config.py`. Enhance it with more specific error types.
*   **Rationale:** Groups configuration-related utilities together. Allows for more specific error handling (e.g., `ConfigNotFoundError`, `ConfigFormatError`).
*   **Implementation Snippet (`automcp/config.py`):**
    ```python
    # config.py
    import json
    from pathlib import Path
    import yaml # Add PyYAML dependency if using YAML
    from .types import GroupConfig, ServiceConfig
    from .exceptions import ConfigNotFoundError, ConfigFormatError

    def load_config(path: Path) -> ServiceConfig | GroupConfig:
        """Load configuration from a YAML or JSON file."""
        if not path.exists():
            raise ConfigNotFoundError(f"Configuration file not found: {path}")

        try:
            suffix = path.suffix.lower()
            with open(path, "r", encoding="utf-8") as f:
                if suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                    # Attempt to validate as ServiceConfig first (more complex)
                    try:
                        return ServiceConfig(**data)
                    except Exception: # Fallback to GroupConfig if ServiceConfig fails
                        try:
                           return GroupConfig(**data)
                        except Exception as e_group:
                           raise ConfigFormatError(f"Invalid YAML format for ServiceConfig or GroupConfig: {path}") from e_group
                elif suffix == ".json":
                    data = json.load(f)
                     # Assume JSON is typically for single GroupConfig
                    try:
                         return GroupConfig(**data)
                    except Exception as e_json:
                         raise ConfigFormatError(f"Invalid JSON format for GroupConfig: {path}") from e_json
                else:
                    raise ConfigFormatError(f"Unsupported file format: {suffix}")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigFormatError(f"Invalid configuration file format [{suffix}]: {e}") from e
        except Exception as e:
            # Catch potential Pydantic validation errors or other issues
            if "validation error" in str(e).lower():
                 raise ConfigFormatError(f"Configuration validation error in {path}: {e}") from e
            raise ConfigFormatError(f"Failed to load configuration from {path}: {e}") from e
    ```

---

**5.4. Create Core Server Runner (`runner.py`)**

*   **Action:** Create `automcp/runner.py` containing the primary `run_server` function and its async helper `_run_server_async`.
*   **Rationale:** Provides the clean, programmatic entry point for starting any AutoMCP server based on its config file. Encapsulates the `asyncio`, MCP transport (stdio), and `AutoMCPServer` lifecycle management.
*   **Implementation (`automcp/runner.py`):** (See code provided in Step 2 above). Ensure necessary imports (`asyncio`, `Path`, `mcp.server.stdio`, `.config.load_config`, `.server.AutoMCPServer`, `.exceptions`) are correct relative to the new package structure.

---

**5.5. Define Custom Exceptions (`exceptions.py`)**

*   **Action:** Create `automcp/exceptions.py`. Define custom exception classes.
*   **Rationale:** Allows for more specific error handling by users of the library.
*   **Implementation (`automcp/exceptions.py`):**
    ```python
    # exceptions.py

    class AutoMCPError(Exception):
        """Base exception for AutoMCP errors."""
        pass

    class ConfigError(AutoMCPError):
        """Base class for configuration errors."""
        pass

    class ConfigNotFoundError(ConfigError):
        """Configuration file not found."""
        pass

    class ConfigFormatError(ConfigError):
        """Invalid format or validation error in configuration."""
        pass

    class ServerError(AutoMCPError):
        """Errors related to the AutoMCPServer runtime."""
        pass

    class OperationError(AutoMCPError):
        """Errors during the execution of a specific operation."""
        pass

    class OperationTimeoutError(OperationError):
        """Operation timed out."""
        pass

    ```

---

**5.6. Refine Core Types (`types.py`)**

*   **Action:** Consolidate `GroupConfig`, `ServiceConfig`. Review `ExecutionRequest`/`Response` - are they strictly needed as public types, or mostly internal helpers passed between server components? If internal, perhaps keep them within `server.py` or a private `_types.py`. Let's assume they are useful for understanding the internal flow and keep them in `types.py` for now.
*   **Rationale:** Clean organization of data models central to the framework.
*   **Implementation (`automcp/types.py`):**
    ```python
    # types.py
    from datetime import UTC, datetime
    from typing import Any, Dict, List, Optional
    from uuid import uuid4

    import mcp.types as types # Import MCP base types if needed
    from pydantic import BaseModel, Field, PrivateAttr

    # --- Configuration Models ---

    class GroupConfig(BaseModel):
        name: str = Field(..., description="Group name (must be unique within a service)")
        description: Optional[str] = Field(None, description="Group description")
        packages: List[str] = Field(default_factory=list, description="Required Python packages")
        config: Dict[str, Any] = Field(default_factory=dict, description="Group-specific configuration dictionary")
        env_vars: Dict[str, str] = Field(default_factory=dict, description="Required environment variables (names only)")
        # Optional: Add class_path if single GroupConfig should specify its implementation class
        class_path: Optional[str] = Field(None, description="Optional path to the ServiceGroup implementation (e.g., 'my_service.groups:MyGroup') if loading single group directly.")


    class ServiceConfig(BaseModel):
        name: str = Field(..., description="Service name")
        description: Optional[str] = Field(None, description="Service description")
        # Key is the full python class path (module:ClassName), value is GroupConfig
        groups: Dict[str, GroupConfig] = Field(..., description="Group configurations keyed by class path")
        packages: List[str] = Field(default_factory=list, description="Shared packages across groups")
        env_vars: Dict[str, str] = Field(default_factory=dict, description="Shared environment variables")


    # --- Internal Request/Response (Primarily for Server <-> Group communication) ---
    # These might not need to be exposed in the public __init__.py unless users
    # need to directly interact with them, which is less common.

    class ExecutionRequest(BaseModel):
        """Internal request for executing a single operation within a group."""
        _id: str = PrivateAttr(default_factory=lambda: str(uuid4()))
        _created_at: datetime = PrivateAttr(default_factory=lambda: datetime.now(UTC))
        operation: str = Field(..., description="Operation name to execute")
        arguments: Optional[Dict[str, Any]] = Field(None, description="Operation arguments")

    class ExecutionResponse(BaseModel):
        """Internal response from executing a single operation."""
        _id: str = PrivateAttr(default_factory=lambda: str(uuid4()))
        _request_id: str = PrivateAttr(default="") # Link back to ExecutionRequest._id
        _created_at: datetime = PrivateAttr(default_factory=lambda: datetime.now(UTC))
        # Use the standard MCP TextContent for results
        content: types.TextContent = Field(..., description="Operation result content")
        error: Optional[str] = Field(None, description="Error message if execution failed")

        # Optional: Keep custom dump if complex BaseModel results are returned directly
        # def model_dump(self) -> Dict[str, Any]: ... (as before)
    ```

---

**5.7. Solidify `ServiceGroup` and `@operation` (`group.py`, `operation.py`)**

*   **Action:**
    *   Move `MockContext` to `automcp/testing/context.py`.
    *   Ensure `ServiceGroup`'s `__init__` correctly initializes `self.registry = {}`.
    *   Ensure `ServiceGroup.execute` now handles a single `ExecutionRequest` and returns an `ExecutionResponse`, including internal error handling.
    *   Review `@operation` decorator: It correctly applies metadata (`is_operation`, `op_name`, `schema`, `policy`, `doc`). Ensure the wrapper handles schema validation *before* calling the original function and passes the validated Pydantic model instance.
*   **Rationale:** Clarifies `ServiceGroup`'s role, standardizes the internal execution signature, moves test utilities, and ensures the decorator correctly handles schema validation.
*   **Implementation Snippets:**

    *   **`group.py`:**
        ```python
        # group.py
        import inspect
        from .types import ExecutionRequest, ExecutionResponse
        from .exceptions import OperationError
        import mcp.types as types
        from pydantic import ValidationError

        # Define Context type hint robustly
        try: Context = types.TextContent
        except AttributeError: Context = Any

        class ServiceGroup:
            """Base class for service groups containing operations."""
            def __init__(self):
                self.registry: Dict[str, Callable] = {}
                self.config: Dict[str, Any] = {} # Store loaded config
                # The registry is populated automatically by @operation
                # or can be done manually if needed. Usually done by Server init.

            @property
            def _is_empty(self) -> bool:
                return not bool(self.registry)

            async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
                """Executes a single operation request."""
                operation = self.registry.get(request.operation)
                if not operation:
                    error_msg = f"Unknown operation: {request.operation}"
                    return ExecutionResponse(
                        content=types.TextContent(type="text", text=error_msg),
                        error=error_msg,
                        _request_id=request._id
                    )

                # Prepare args and potential context
                args = request.arguments or {}
                ctx = None # Context is not created here, but passed by @operation wrapper if needed

                try:
                    # The @operation decorator handles schema validation and ctx injection
                    # We call the 'operation' which is the *wrapped* method
                    result = await operation(**args) # The wrapper handles passing self, ctx, etc.

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
                         _request_id=request._id
                    )

                except ValidationError as e:
                     # Schema validation error from @operation decorator
                    error_msg = f"Input validation failed for '{request.operation}': {e}"
                    return ExecutionResponse(
                        content=types.TextContent(type="text", text=error_msg),
                        error=error_msg,
                        _request_id=request._id
                    )
                except Exception as e:
                    error_msg = f"Error during '{request.operation}' execution: {str(e)}"
                    logging.exception("Operation execution failed:") # Log traceback
                    return ExecutionResponse(
                        content=types.TextContent(type="text", text=error_msg),
                        error=error_msg,
                        _request_id=request._id
                    )
        ```

    *   **`operation.py`:** (Enhance wrapper for validation and context)
        ```python
        # operation.py
        import inspect
        from functools import wraps
        from pydantic import BaseModel, ValidationError
        import mcp.types as types
        # Define Context type hint
        try: Context = types.TextContent
        except AttributeError: Context = Any

        def operation(
            schema: type[BaseModel] | None = None,
            name: str | None = None,
            policy: str | None = None, # Policy usage remains undefined by examples
        ):
            """Decorator for service operations."""
            def decorator(func):
                op_name = name or func.__name__
                sig = inspect.signature(func)
                expects_ctx = "ctx" in sig.parameters
                schema_param_name = None
                if schema:
                    # Find the parameter annotated with the schema type
                    for param_name, param in sig.parameters.items():
                         if param.annotation == schema:
                              schema_param_name = param_name
                              break
                    if not schema_param_name:
                        raise TypeError(f"Operation '{op_name}' decorated with schema {schema.__name__} but no matching parameter annotation found.")


                @wraps(func)
                async def wrapper(self, *args, **kwargs): # self is the ServiceGroup instance
                    validated_input = None
                    final_args = list(args) # To potentially modify args list
                    final_kwargs = kwargs.copy()

                    # 1. Inject Context if expected
                    if expects_ctx and "ctx" not in final_kwargs:
                        # Attempt to find context in args or create a default one
                        # This relies on how AutoMCPServer calls the wrapper.
                        # Let's assume ctx might be passed positionally or not at all.
                        # A safer approach is for the caller (AutoMCPServer) to handle ctx.
                        # For now, let's pass None if not provided, user code must handle.
                        # Or look for it positionally? Safer to expect it in kwargs from Server.
                        ctx_instance = final_kwargs.pop("ctx", None) # Assume server passes it here
                        if ctx_instance is None:
                             # Check if passed positionally (less robust)
                             for idx, arg in enumerate(final_args):
                                  if isinstance(arg, Context): # Check type
                                       ctx_instance = final_args.pop(idx)
                                       break
                        # If still None, maybe create a dummy? Or raise error? For now pass None
                        final_kwargs["ctx"] = ctx_instance # Pass ctx explicitly


                    # 2. Validate Schema if provided
                    if schema and schema_param_name:
                        # Extract parameters matching the schema fields from kwargs
                        schema_kwargs = {}
                        remaining_kwargs = {}
                        schema_fields = schema.model_fields.keys()

                        for k, v in final_kwargs.items():
                             if k in schema_fields:
                                  schema_kwargs[k] = v
                             elif k != 'ctx': # Don't pass ctx to schema
                                  remaining_kwargs[k] = v

                        # Add positional arguments if they map to schema fields (less common)
                        # This logic needs care, prioritizing kwargs is safer
                        schema_param_index = list(sig.parameters.keys()).index(schema_param_name)

                        try:
                            validated_input = schema(**schema_kwargs) # Validate using extracted kwargs
                            # Replace the original schema parameter (if positional) or
                            # add/replace it in kwargs with the validated instance.
                            # Assume it's passed via kwargs by AutoMCPServer based on call_tool arguments.
                            final_kwargs[schema_param_name] = validated_input
                             # Remove the original kwargs that were used for validation
                            for k in schema_kwargs.keys():
                                final_kwargs.pop(k, None)

                        except ValidationError as e:
                            # Re-raise to be caught by ServiceGroup.execute
                            raise e
                    # Call the original function with potentially modified args/kwargs
                    return await func(self, *final_args, **final_kwargs)

                # Attach metadata to the wrapper
                wrapper.is_operation = True
                wrapper.op_name = op_name
                wrapper.schema = schema
                wrapper.policy = policy
                wrapper.doc = func.__doc__
                return wrapper
            return decorator
        ```

---

**5.8. Structure `__init__.py` for Public API**

*   **Action:** Create/update `automcp/__init__.py`. Expose the main classes and functions needed by users.
*   **Rationale:** Defines the public interface of the package.
*   **Implementation (`automcp/__init__.py`):**
    ```python
    # automcp/__init__.py
    from .config import load_config
    from .exceptions import (
        AutoMCPError, ConfigError, ConfigFormatError,
        ConfigNotFoundError, OperationError, OperationTimeoutError,
        ServerError
    )
    from .group import ServiceGroup
    from .operation import operation
    from .runner import run_server
    from .server import AutoMCPServer
    from .types import GroupConfig, ServiceConfig

    __all__ = [
        "load_config",
        "AutoMCPError",
        "ConfigError",
        "ConfigFormatError",
        "ConfigNotFoundError",
        "OperationError",
        "OperationTimeoutError",
        "ServerError",
        "ServiceGroup",
        "operation",
        "run_server",
        "AutoMCPServer",
        "GroupConfig",
        "ServiceConfig",
    ]
    ```

---

**5.9. Update the CLI (`cli.py`)**

*   **Action:** Modify `automcp/cli.py` (or wherever it resides) to import and use `automcp.run_server`. Remove internal server creation/running logic.
*   **Rationale:** Makes the CLI a simple front-end, relying on the core library function.
*   **Implementation Snippet (`cli.py` - Simplified `run` command):**
    ```python
    # cli.py (assuming it uses typer)
    import typer
    from pathlib import Path
    from typing import Annotated

    # Import the core runner function
    try:
         # Adjust path based on where cli.py is relative to the automcp package
         from automcp import run_server
         from automcp.exceptions import AutoMCPError
    except ImportError:
         print("Error: Failed to import automcp. Ensure it's installed or accessible.")
         # Handle appropriately, maybe define dummy run_server

    app = typer.Typer(...)

    @app.command()
    def run(
        config: Annotated[Path, typer.Argument(help="Path to config file (YAML/JSON)")],
        # group: Annotated[str | None, typer.Option(...)] = None, # Group selection logic needs careful thought now
        timeout: Annotated[
            float, typer.Option("--timeout", "-t", help="Operation timeout in seconds")
        ] = 30.0,
    ) -> None:
        """Run AutoMCP server using the specified configuration file."""
        try:
            # Core logic is now just calling the library function
            # Note: Group selection from ServiceConfig via CLI needs specific handling
            # in run_server or here, if that feature is retained.
            # For simplicity, assume run_server currently runs *all* groups in a ServiceConfig.
            # if group:
            #     print(f"Warning: Group selection via CLI ('--group {group}') is not fully handled by the core runner yet.")

            run_server(config_path=config, timeout=timeout)

        except AutoMCPError as e: # Catch specific errors from the framework
            typer.echo(f"Error running server: {e}", err=True)
            raise typer.Exit(code=1)
        except Exception as e: # Catch unexpected errors
            typer.echo(f"An unexpected error occurred: {e}", err=True)
            raise typer.Exit(code=1)

    # ... rest of the CLI ...
    ```

---

**5.10. Adapt Verification & Example Code**

*   **Action:**
    *   Remove `verification/run_*.py` scripts.
    *   Modify `verification/verify_automcp.py` and `verification/test_data_processor.py`:
        *   If they need to run a server for testing, they should now manage this themselves, either by:
            1.  Running `python -m servers.run_<service_name>_server` in a **subprocess** and connecting via STDIO (`mcp.client.stdio.stdio_client`). This is closer to real-world usage.
            2.  Importing `AutoMCPServer`, `load_config`, and using `mcp.shared.memory.create_connected_server_and_client_session` for **in-memory testing** (if the MCP library supports this well and operations don't rely heavily on specific STDIO behavior). This is faster but less realistic.
        *   Update tests to use the correct group/operation names.
    *   Move `MockContext` from `group.py` to `automcp/testing/context.py` and update imports in unit tests.
*   **Rationale:** Examples and verification tests should *use* the framework like external clients, not contain core logic. They demonstrate correct usage patterns.

---

**6. Testing Strategy for Refactoring**

*   **Before Refactoring:** Ensure the existing verification tests (`verify_automcp.py`, etc.) pass with the *current* code state to establish a baseline.
*   **During Refactoring:**
    *   As you move logic (e.g., `load_config`, server startup), write *new unit tests* for these core library functions within the `automcp/tests/` directory (create this if it doesn't exist).
    *   Refactor incrementally. After each significant change (like removing `ServiceManager` and adding timeout to `AutoMCPServer`), run the *original verification tests* (adapted to the new startup/connection method if necessary) to ensure no functionality has broken.
*   **After Refactoring:** Run the full suite of adapted verification tests and any new core library unit tests.

---

**7. Guidance for LLM Team Roles During Refactoring**

*   **@automcp-orchestrator:**
    *   Oversee the entire refactoring process.
    *   Break down the steps above into smaller, assignable tasks (e.g., "TASK-REFACTOR-01: Remove ServiceManager and add timeout to AutoMCPServer", "TASK-REFACTOR-02: Implement automcp.run_server function").
    *   Assign tasks to @automcp-implementer.
    *   Review the implemented code and **especially the new/updated tests** for the core framework components.
    *   Assign @automcp-tester to adapt and run the *original* verification tests against the *refactored* framework to ensure backward compatibility and correctness.
*   **@automcp-implementer:**
    *   Execute assigned refactoring tasks.
    *   **Write new unit tests** for the refactored/new core components (`runner.py`, modified `server.py`, `config.py`, etc.).
    *   Ensure all *new* unit tests pass (`uv run pytest automcp/tests/`).
    *   Modify existing files (`server.py`, `types.py`, `__init__.py`, etc.) according to the plan.
    *   Remove deprecated files (`manager.py`).
    *   Update the `cli.py` to use the new `run_server`.
*   **@automcp-tester:**
    *   **Adapt existing verification tests** (like those in `verify_automcp.py` and `test_data_processor.py`) to work with the refactored framework. This mainly involves changing how the test server is started (subprocess or in-memory) and how the client connects.
    *   Run the adapted tests against the refactored code provided by the Implementer.
    *   Report detailed pass/fail status and any regressions found.
*   **@automcp-designer:**
    *   Review the proposed refactored structure and API (`automcp.run_server` signature, public exports in `__init__.py`) for clarity and usability from a service *designer's* perspective. Does the refactored framework make it easier to design *new* services?

---

**8. Expected Benefits**

*   **Cleaner Core Library:** A well-defined `automcp` package with clear responsibilities.
*   **Simplified Server Startup:** A single function `automcp.run_server(config)` is all that's needed to launch a service.
*   **Improved Testability:** Core functions like `load_config` and potentially parts of `AutoMCPServer` can be unit tested more easily.
*   **Reduced Redundancy:** `ServiceManager` removal simplifies the mental model.
*   **Better Agent Integration:** The programmatic `run_server` is ideal for agent orchestrators to manage service lifecycles.
*   **Enhanced Maintainability:** Centralized logic is easier to debug and update.

---

This detailed guide provides the roadmap for refactoring the AutoMCP framework. Each step should be implemented carefully, with associated tests to ensure the core functionality remains robust while the structure and usability are significantly improved.