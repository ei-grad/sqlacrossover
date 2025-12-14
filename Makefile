.PHONY: help test test-sqlite test-all test-mysql test-postgres lint format clean docker-up docker-down

help:
	@echo "Available targets:"
	@echo "  test          - Run SQLite-only tests (fast, no Docker)"
	@echo "  test-all      - Run all tests including MySQL and Postgres (requires Docker)"
	@echo "  test-mysql    - Run tests with SQLite and MySQL"
	@echo "  test-postgres - Run tests with SQLite and Postgres"
	@echo "  lint          - Run ruff linter"
	@echo "  format        - Run ruff formatter"
	@echo "  docker-up     - Start MySQL and Postgres containers"
	@echo "  docker-down   - Stop and remove containers"
	@echo "  clean         - Remove Python cache files"

test:
	@echo "Running SQLite-only tests (30s timeout)..."
	TEST_MYSQL=false TEST_POSTGRES=false timeout 30 uv run -m pytest tests/ -v

test-sqlite: test

test-mysql:
	@echo "Running tests with MySQL (60s timeout)..."
	TEST_POSTGRES=false timeout 60 uv run -m pytest tests/ -v

test-postgres:
	@echo "Running tests with Postgres (60s timeout)..."
	TEST_MYSQL=false timeout 60 uv run -m pytest tests/ -v

test-all: docker-up
	@echo "Running all tests (90s timeout)..."
	timeout 90 uv run -m pytest tests/ -v

lint:
	uv run -m ruff check .

format:
	uv run -m ruff format .

docker-up:
	docker compose up -d
	@echo "Waiting for databases to be ready..."
	@uv run -m python -c "import socket, time, sys; [time.sleep(1) if any(socket.socket().connect_ex(('127.0.0.1', p)) == 0 for _ in [None]) else None for p in [3306, 5432] for _ in range(30)]" || true

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
