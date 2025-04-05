---
title: Dev Style Guide
created_at: 2025-04-05
updated_at: 2025-04-05
tools: ["ChatGPT O1-pro", "ChatGPT DeepResearch", "Gemini-2.5-pro"]
by: Ocean
version: 1.0
description: |
    A style guide for developers contributing to the AutoMCP project.
---

```
Below is a sample `dev_style.md` document that you can adapt or refine for your specific project needs. It aims to provide a central place for developers to understand coding conventions, formatting rules, naming standards, documentation styles, and testing guidelines. By adhering to these guidelines, your team ensures consistency, maintainability, and clarity across the entire codebase.
```

# Dev Style Guide

This document outlines our **coding standards and practices** for all
contributors to the AutoMCP project. By following these guidelines, we maintain
a clean, consistent, and predictable codebase.

## 1. General Philosophy

1. **Readability First**\
   Code should be self-explanatory, well-structured, and consistently formatted.
   Even if a particular code path is “clever,” prioritize clarity over
   cleverness.

2. **Consistency**\
   When in doubt, match the style already established in the codebase.
   Consistency makes the project easier to navigate and maintain.

3. **Small, Focused Commits**\
   Each commit should address a single concern. Avoid mixing refactors, feature
   additions, and unrelated fixes in one commit.

---

## 2. Language & Framework Conventions

### 2.1 Python

- **Python Version**: We target Python 3.10+ unless otherwise specified.
- **Formatting**: Use **Black** (version pinned in `pyproject.toml`) for code
  formatting.
  - Run `black .` (or via pre-commit hooks) before pushing.
- **Imports**:
  - Order imports as recommended by **isort** with `--profile black`.
  - Group standard library, third-party, and local imports separately.
- **Typing**:
  - Use modern Python type hints.
  - For new code, prefer explicit types for function arguments and return
    values.
- **Docstrings**:
  - Follow either
    [Google Style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
    or reStructuredText style that is Sphinx-compatible.
  - Every public function/class **must** have a docstring describing usage,
    parameters, return types, and exceptions raised.
- **Async/Concurrency**:
  - If a function performs I/O or blocking tasks, consider using `async` or
    spawning sub-tasks in a way that doesn’t block the main event loop.
  - Where relevant (e.g., CPU-bound tasks), yield control frequently
    (`await asyncio.sleep(0)`) if not using a separate thread/process.

### 2.2 Other Languages

- **Rust / TypeScript**: If you commit Rust or TypeScript code, follow official
  style or the community standard lints (e.g., `cargo fmt`, `tsc` checks).
- Keep these style guidelines **aligned in spirit** with our Python guidelines
  (e.g., consistent naming, doc comments).

---

## 3. Naming Conventions

1. **Filenames & Modules**:
   - All Python modules should use lowercase, underscores if necessary (e.g.,
     `my_module.py`).
2. **Classes**:
   - Use `CamelCase` for class names: `ExampleGroup`, `MySchema`.
3. **Functions and Methods**:
   - Use `snake_case` for function and method names: `process_data()`.
4. **Constants**:
   - Use `UPPER_SNAKE_CASE` for module-level constants: `MAX_CONNECTIONS`.
5. **Variables**:
   - Use `snake_case` in Python for local variables and parameters: `max_count`,
     `timeout_seconds`.
6. **Operation Decorators**:
   - If using `@operation(name="...")`, ensure the `name` is a short, clear
     identifier that matches the operation’s purpose.

---

## 4. Documentation & Comments

1. **Inline Comments**:
   - Use inline comments sparingly, and only to clarify non-obvious logic.
   - For obvious or straightforward code, rely on descriptive variable/function
     names and docstrings instead.
2. **Function Docstrings**:
   - Provide a high-level description of what the function does.
   - List and describe function parameters (especially if they have non-trivial
     behavior).
   - Document return types and any exceptions.
   - For `@operation` functions, reference the relevant Pydantic schema or
     context usage (if `ctx` is utilized).
3. **Class Docstrings**:
   - Summarize the class’s purpose, highlight any special initialization
     parameters or usage constraints.
4. **Readme / High-Level Docs**:
   - Keep the top-level `README.md` or `docs/` up to date with new features or
     major changes.

---

## 5. Testing & QA

1. **Test Coverage**:
   - All new features should come with unit tests.
   - For complex or user-facing logic, also include integration tests.
   - For concurrency or timeouts, add robust test cases simulating heavy loads
     or CPU-bound tasks.
2. **Test Organization**:
   - Store tests in `tests/` or a similarly named directory.
   - Group them logically by feature or module (e.g., `test_server_config.py`,
     `test_timeout_handling.py`).
3. **Pytest Usage**:
   - We standardize on **pytest** for Python testing.
   - Keep test functions short and descriptive, e.g.,
     `test_schema_validation_failure()`.
4. **Verification Suite**:
   - For advanced end-to-end or environment checks, see the `verification/`
     folder and scripts like `run_tests.py`.
5. **CI Integration**:
   - Ensure tests run automatically in CI.
   - Blocks merges if tests fail or coverage drops below an acceptable
     threshold.

---

## 6. Code Review & Pull Requests

1. **PR Scope**:
   - A PR should address a single feature, bug fix, or refactor. Avoid bundling
     unrelated changes.
2. **PR Description**:
   - Provide a concise summary of **what** was changed and **why**.
   - List any dependencies or environment changes required.
3. **Review Focus**:
   - Code clarity, correctness, performance, and security.
   - Avoid unproductive discussions about personal style preferences if the code
     already fits established guidelines.
4. **Approval Criteria**:
   - All tests pass.
   - Adheres to style guidelines.
   - Contains appropriate docstrings/comments.
   - No major architectural or performance issues.

---

## 7. File & Directory Structure

A typical project layout might look like:

```
repo-root/
│
├── automcp/               # Main library or package code
│   ├── __init__.py
│   ├── cli.py
│   ├── group.py
│   ├── operation.py
│   ├── server.py
│   ├── types.py
│   └── utils.py
│
├── tests/                 # Unit & integration tests
│   ├── test_server.py
│   ├── test_operation.py
│   ├── test_schema_validation.py
│   └── ...
│
├── verification/          # Extended verification suite (integration, coverage)
│   ├── run_tests.py
│   ├── ...
│   └── groups/
│
├── docs/                  # Documentation files (Sphinx or Markdown)
│   └── ...
│
├── .pre-commit-config.yaml
├── pyproject.toml         # Project config (dependencies, style, etc.)
├── README.md
└── dev_style.md           # This style guide
```

---

## 8. Versioning & Release Management

1. **Version Bumps**:
   - Update `__version__` (in `version.py` or similar) with **semantic
     versioning** (MAJOR.MINOR.PATCH).
2. **Release Notes**:
   - Summarize new features, fixes, and possible breaking changes in the
     changelog or GitHub release notes.
3. **Tagging**:
   - Tag releases in Git with the version number (`vX.Y.Z`).

---

## 9. Additional Notes

- **Performance Considerations**:
  - If performance is critical, profile code (e.g., `pytest --profile`) or use
    tools like `cProfile` and `line_profiler`.
- **Security**:
  - Follow best practices for input validation (Pydantic helps).
  - Carefully handle external I/O or untrusted data.

---

## 10. Future Evolution

This style guide should be a **living document**:

- When new coding patterns or technologies are introduced, update it.
- If any guidelines become irrelevant or conflict with evolving best practices,
  refine them.
- Encourage team members to propose changes or clarifications via pull requests.

---

**Thank you for adhering to these conventions!** By following this style guide,
we ensure that the AutoMCP codebase remains consistent, robust, and welcoming to
both current and future contributors.
