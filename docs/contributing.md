# Contributing to khivemcp

Contributions are welcome! If you'd like to fix bugs or add features, here's the
recommended workflow:

1. **Fork** the repo & create a feature branch.
2. **Install in dev mode**: `pip install -e ".[dev]"`.
3. **Write tests** for your changes (pytest style).
4. **Format & lint** your code (`ruff`, `black`) if used.
5. Submit a **Pull Request** with a clear explanation.

---

## Code Style

- Follow PEP8 & `black` formatting.
- Use **type hints** and **Pydantic** models where appropriate.
- Document new classes/functions with docstrings.

---

## Testing

We rely on **pytest**:

```bash
pytest
```

All new features or bug fixes must include relevant tests.

---

## Merging

A maintainer reviews PRs, requests any changes, and merges once the PR meets
project requirements.

Thank you for helping improve khivemcp!
