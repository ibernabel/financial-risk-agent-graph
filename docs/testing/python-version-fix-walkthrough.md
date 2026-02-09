# Walkthrough - Python Version PIN (3.12)

Fixed compatibility issues with Pydantic V1 and LangChain by pinning the project to Python 3.12.

## Changes

1.  **`.python-version`**: Updated from `3.14` to `3.12`.
2.  **`pyproject.toml`**: Restricted `requires-python` from `~=3.12` to `>=3.12,<3.14` to prevent automatic upgrades to incompatible versions.
3.  **Environment**: Rebuilt `.venv` using Python 3.12.7 via `uv sync`.

## Verification Results

- **Python Version**: `Python 3.12.7` (Verified in `.venv`)
- **Warning Check**: `UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater` is no longer present.
- **Dependency Sync**: `uv sync` completed successfully with all packages installed.

## How to run

```bash
source .venv/bin/activate
python demo_bank_analysis.py
```

**Commit Message:**
`fix: pin python to 3.12 to resolve langchain pydantic v1 compatibility`
