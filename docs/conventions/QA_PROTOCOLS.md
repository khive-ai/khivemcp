# TDD Specification

This project follows a pragmatic Test-Driven Development (TDD) or Test-Augmented
Development approach:

1. **Write Failing Test:** Before implementing a new piece of logic (or fixing a
   bug), write a minimal `pytest` test case that clearly defines the expected
   outcome and currently fails.
2. **Implement to Pass:** Write only the necessary production code required to
   make the failing test pass. Avoid adding extra functionality not yet covered
   by a test.
3. **Refactor (If Necessary):** Once the test passes, refactor the
   implementation code _and_ the test code for clarity, simplicity, and
   maintainability, ensuring tests continue to pass.
4. **Verify:** Regularly run the test suite using `uv run pytest` (or equivalent
   `pytest` command) to ensure all tests pass.

**Goal:** Ensure code correctness, facilitate refactoring, and maintain an
elegant, robust codebase with good test coverage. Focus on clear, targeted
tests.
