# Contributing

Thanks for helping. Small pull requests are easiest to review.

## Development setup

```bash
git clone https://github.com/nicoleyangcoding/readme-runs
cd readme-runs
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

Tests that need Docker are skipped automatically when it isn't running.

## Guidelines

- No runtime dependencies beyond Python and Docker.
- Call `docker` with argument lists, never through a shell.
- Keep the default output to one line per block.
