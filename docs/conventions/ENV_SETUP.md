# Environment Setup

This project utilizes `uv` for managing Python environments and dependencies:

1. **Installation:**
   - Ensure `uv` is installed
     ([https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)).
   - Create a virtual environment: `uv venv`
   - Install dependencies from `pyproject.toml`: `uv sync` (or
     `uv pip sync requirements.lock` if using lockfiles).
2. **Running Code/Tests:**
   - Execute scripts defined in `pyproject.toml`: `uv run <script_name>` (e.g.,
     `uv run pytest`).
   - Run arbitrary commands within the environment: `uv run -- <command>` (e.g.,
     `uv run -- python src/my_server/main.py`).
3. **Adding Dependencies:**
   - Add a new dependency: `uv add <package_name>`
   - Add a development dependency: `uv add --dev <package_name>`

**Goal:** Maintain a consistent, reproducible development environment using
`uv`. Keep setup streamlined and rely on `pyproject.toml` for dependency
definition.
