# Agent Guide (sqlacrossover)

## Environment + Dependencies (always use `uv`)

- Use `uv` for all environment and dependency management (do **not** use `pip`, `poetry`, or `conda` in this repo).
- Prefer `uv sync` to create/update the project-local virtualenv at `.venv/`.
- Run all Python tooling via `uv run -m …` so it executes inside `.venv/`.
- If `uv` cache is not writable (common in sandboxed runners), set `UV_CACHE_DIR=/workspaces/sqlacrossover/.uv-cache` (or `UV_CACHE_DIR=.uv-cache`).

Common setup:

- Install deps for development + all DB drivers: `uv sync --all-extras`
- Add a dependency: `uv add <pkg>`

## Tests (always `uv run -m pytest …`)

- Run tests with: `uv run -m pytest …` (do **not** invoke `pytest` directly).
- Default test entrypoint: `uv run -m pytest tests/`
- **CRITICAL**: ALWAYS use `timeout` command when running tests to avoid hanging (e.g., `timeout 30 uv run -m pytest tests/`)

SQLite-only (fast, no Docker):

- `TEST_MYSQL=false TEST_POSTGRES=false timeout 10 uv run -m pytest tests/`

Full integration (Docker MySQL + Postgres):

- Start DBs: `docker compose up -d`
- Run: `timeout 60 uv run -m pytest tests/`
- Stop: `docker compose down`

## Linting / Formatting

- Lint: `uv run -m ruff check --fix .`
- Format: `uv run -m ruff format .`

## Project Layout

- Library / CLI entrypoint: `src/sqlacrossover/__init__.py` (`sqlacrossover = "sqlacrossover:main"`)
- Tests: `tests/`
