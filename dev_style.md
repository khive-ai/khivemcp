---
title: Dev Style Guide
created_at: 2025-04-05
updated_at: 2025-04-05
tools: ["ChatGPT O1-pro", "ChatGPT DeepResearch", "Gemini-2.5-pro"]
by: Ocean
version: 1.2
description: |
    A style guide for developers contributing to the khivemcp project.
---

# khivemcp Core Development Style Guide

This **Dev Style Guide** outlines the coding conventions, testing patterns,
documentation practices, and recommended workflows for contributing directly to
the **khivemcp** core library (`khivemcp/` directory).

## 1. General Philosophy

1. **Clarity Over Cleverness**: Write readable and straightforward code. Comment
   complex sections where necessary.
2. **Consistency**: Follow existing patterns in the codebase for file layout,
   naming, docstrings, and tests. This aids collaboration, especially with LLM
   contributors.
3. **Small, Focused Commits**: Each commit should ideally address one issue or
   add one distinct piece of functionality. Use Conventional Commits format (see
   Section 7).
4. **Leverage FastMCP**: Utilize the underlying FastMCP server for core MCP
   functionality. khivemcp focuses on orchestration, configuration, dynamic
   loading, and the decorator interface.

---

## 2. Language & Framework

### 2.1 Python

- **Version**: Target Python 3.10+ (Verify based on `pyproject.toml`).
- **Formatting**: Use **Black** with default settings (`ruff format .`).
  Configuration is in `pyproject.toml`.
- **Linting**: Use **Ruff** (`ruff check . --fix`). Enforce rules defined in
  `pyproject.toml`. Code must pass linting.
- **Imports**:
  - Sorted via Ruff's integrated `isort` functionality.
  - Group standard library, third-party libraries, and local `khivemcp` modules.
- **Typing**:
  - Use Python type hints for all function/method signatures (arguments and
    return types).
  - Use standard types from the `typing` module.
  - Type variables where ambiguity exists. Check with `mypy .` or Ruff's type
    checking capabilities periodically.
- **Docstrings**:
  - Use **Google style** docstrings for modules, classes, functions, and
    methods. Ensure they cover purpose, Args, Returns, and Raises where
    applicable.

### 2.2 Core Libraries

- **Typer**: Used for the command-line interface (`cli.py`).
- **Pydantic**: Used for configuration validation (`types.py`) and potentially
  internal data structures.
- **PyYAML**: Used for parsing YAML configuration files (`utils.py`).
- **FastMCP**: The underlying server library khivemcp orchestrates.
- **Pytest**: Used for all testing.

---

## 3. Directory Structure (Core Package)

Focus is on the `khivemcp` library code and associated project files:

```
repo-root/
│
├── khivemcp/               # Main library source code
│   ├── __init__.py
│   ├── cli.py             # Typer CLI application, orchestration logic
│   ├── decorators.py      # @operation decorator definition and logic
│   ├── types.py           # Pydantic models for ServiceConfig, GroupConfig
│   └── utils.py           # Config loading, validation utilities
│
├── tests/                 # Pytest tests for the core library
│   ├── test_cli.py
│   ├── test_decorators.py
│   ├── test_types.py
│   └── test_utils.py
│   └── conftest.py        # Shared fixtures
│
├── docs/                  # User-facing documentation (Markdown)
├── .github/               # CI/CD workflows (e.g., GitHub Actions)
├── dev_style.md           # This style guide
├── pyproject.toml         # Dependencies, build config, tool settings (ruff, pytest)
├── README.md              # Main project user readme
└── LICENSE                # Project license
```

---

## 4. Coding Conventions

1. **Naming**:
   - Classes: `PascalCase`
   - Functions, Methods, Variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Internal Helpers: Prefix with `_` (e.g., `_load_yaml_file`).
2. **Decorators**:
   - The `@khivemcp.operation` decorator is defined in `decorators.py`. Its
     primary role is attaching metadata. Keep runtime logic within it minimal.
3. **Error Handling**:
   - Raise specific exceptions where appropriate (e.g., `FileNotFoundError`,
     `ValueError` for bad config, `TypeError`).
   - The CLI (`cli.py`) should catch top-level exceptions during setup/startup
     and report them clearly to `stderr`, exiting non-zero.
   - Use Pydantic's `ValidationError` for configuration structure issues.
4. **Logging**:
   - Use `print("...", file=sys.stderr)` for internal operational logging during
     startup and execution within the core library. Prefix messages logically
     (e.g., `[Config Loader]`, `[Register]`).

---

## 5. Testing

1. **Framework**: Use **Pytest**. Store tests in the top-level `tests/`
   directory, mirroring the `khivemcp/` structure.
2. **Test Types**:
   - **Unit Tests**: Verify individual functions and methods in isolation (e.g.,
     test `load_config` in `test_utils.py`, test Pydantic models in
     `test_types.py`). Use mocking (`unittest.mock` or `pytest-mock`)
     extensively.
   - **Integration Tests**: Test interactions between modules (e.g., test
     `cli.py`'s orchestration logic by mocking file loading, imports, and
     FastMCP interactions).
   - **End-to-End (Optional/Minimal)**: For the core library, full E2E might
     involve complex process management. Focus primarily on robust unit and
     integration tests. CLI command invocation can be tested using
     `typer.testing.CliRunner` or `subprocess`.
3. **Fixtures**: Use `pytest` fixtures (`@pytest.fixture` in `conftest.py` or
   test files) for reusable setup code (e.g., temporary config files, mock
   objects).
4. **Coverage**:
   - Aim for high test coverage (>80-90%) for core library code. Use
     `pytest-cov` (`pytest --cov=khivemcp`). Critical paths must be tested.

---

## 6. Documentation

1. **README (`README.md`)**: User-focused. Quick start, installation, basic
   usage example. Links to detailed docs.
2. **User Docs (`docs/`)**: Detailed user guides in Markdown. Covers
   configuration options (`ServiceConfig`, `GroupConfig`), how to create service
   groups, CLI usage, etc. This is separate from internal code documentation.
3. **Code Docs (Docstrings)**: Use Google-style docstrings within the code for
   all public modules, classes, functions, and methods. These explain the _how_
   and _why_ of the code itself.
4. **Style Guide (`dev_style.md`)**: This document, guiding internal development
   practices.

---

## 7. Commit & PR Process

1. **Branching**:
   - Use descriptive branch names: `feat/yaml-config-support`,
     `fix/cli-error-handling`.
2. **Commits**:
   - Follow the **Conventional Commits** specification (e.g., `feat:`, `fix:`,
     `refactor:`, `test:`, `docs:`, `style:`, `chore:`). This aids automated
     changelogs and semantic versioning.
   - Keep commits focused and atomic.
3. **Pull Requests (PRs)**:
   - Must pass all CI checks (linting, testing).
   - Include a clear description of the changes and link relevant issues.
   - Ensure tests covering the changes are included.
4. **Merging**:
   - Prefer squash merges for feature branches to keep the main history clean,
     but use judgment based on the PR's complexity.
   - Ensure CI is green before merging.

---

## 8. Guidelines for LLM Contributors

1. **Context is Key**: State the file(s) being modified and the specific goal.
   Reference this guide if applicable.
2. **Adhere to Standards**: Explicitly follow formatting (Black/Ruff), linting
   (Ruff), typing, testing, and commit conventions outlined here.
3. **Focused Changes**: Address one specific task per PR.
4. **Testing**: Provide `pytest` tests for all new/modified logic. Explain test
   coverage.
5. **Reasoning**: Briefly explain _why_ a particular approach was chosen if
   non-obvious.
6. **Diff Format**: Use `diff` format for proposing changes unless providing a
   new file.
7. **Verification**: State that you have reviewed the logic/tests for
   correctness.

---

## 9. Final Notes

- This style guide is a **living document**. Update it via PRs as our practices
  evolve.
- When in doubt, refer to existing patterns in the codebase or ask a senior
  contributor.
