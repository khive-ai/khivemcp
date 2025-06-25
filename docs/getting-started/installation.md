# Installation

Below is how to install khivemcp and set up your environment.

## Requirements

- Python 3.10 or newer
- pip (or uv) for installation

## Basic Installation

```bash
pip install khivemcp
```

Or, using [uv](https://github.com/astral-sh/uv):

```bash
uv venv
source .venv/bin/activate
uv pip install khivemcp
```

## Development Installation

If you need the latest from source:

```bash
git clone https://github.com/your-org/khivemcp.git
cd khivemcp
pip install -e ".[dev]"
```

This installs `khivemcp` in editable mode with development dependencies.

## Verifying Installation

```bash
khivemcp --version
```

You should see the installed `khivemcp` version.
