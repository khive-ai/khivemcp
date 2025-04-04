# Testing Strategy

Our testing strategy prioritizes automated tests using `pytest`:

1. **Unit Tests (`tests/unit/`)**:
   - Focus: Test individual functions, methods (especially within
     `ServiceGroup`s), or classes in isolation.
   - Techniques: Use mocking (`unittest.mock`, `pytest-mock`) to isolate
     dependencies (e.g., external APIs, database calls,
     `mcp.server.fastmcp.Context`). Verify logic, edge cases, and error
     handling.
   - Goal: Fast feedback, detailed verification of specific logic units.
2. **Integration Tests (`tests/integration/`)**:
   - Focus: Test the interaction between components, particularly the end-to-end
     `automcp` server flow.
   - Techniques: Use
     `mcp.shared.memory.create_connected_server_and_client_session` to
     instantiate an `AutoMCPServer` with a test configuration in memory.
     Simulate client calls (`list_tools`, `call_tool`) and verify responses,
     error handling, context effects (if testable), and timeouts.
   - Goal: Verify that components work together correctly as an MCP server.
3. **Coverage:** Aim for high test coverage of critical logic paths, but
   prioritize meaningful tests over hitting arbitrary percentage targets. Use
   coverage analysis (`pytest-cov`) to identify significant gaps.
4. **Execution:** All tests should be runnable via a single command (e.g.,
   `uv run pytest` or `pytest`). Tests must pass for code to be considered
   complete.

**Goal:** Ensure correctness and robustness through a layered testing approach,
balancing detailed unit checks with realistic integration verification.
