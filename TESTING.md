# Testing Guide

This document explains how to run tests for sqlacrossover, including integration tests against MySQL and PostgreSQL.

## Prerequisites

We manage dependencies with [uv](https://docs.astral.sh/uv/). Install uv once (see their docs), then install all dev/test dependencies in a project-local virtual environment:

```bash
uv sync --extra all --group dev
```

This creates `.venv/` with everything needed for running the full test suite, and all subsequent commands assume you are using `uv run …` to execute tooling inside that environment.

## Running Tests Locally

### Quick Start (SQLite only)

To run tests with SQLite only (no Docker required):

```bash
# Run SQLite-only tests with env vars that skip external DBs
TEST_MYSQL=false TEST_POSTGRES=false uv run -m pytest tests/
```

### Full Integration Tests with Docker

To run tests against MySQL and PostgreSQL, you need Docker installed.

#### 1. Start the databases

```bash
docker-compose up -d
```

This will start:
- MySQL 8.0 on port 3306
- PostgreSQL 16 on port 5432

#### 2. Wait for databases to be ready

```bash
# Wait for MySQL
until docker-compose exec mysql mysqladmin ping -h localhost -ptest password --silent; do
    echo "Waiting for MySQL..."
    sleep 2
done

# Wait for PostgreSQL
until docker-compose exec postgres pg_isready -U postgres; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
```

#### 3. Run the tests

```bash
# Run all tests (SQLite, MySQL, and PostgreSQL)
uv run -m pytest tests/ -v

# Or with coverage (pytest addopts already includes coverage flags)
uv run -m pytest tests/
```

#### 4. Stop the databases when done

```bash
docker-compose down
```

### Alternative: Using Docker Run Commands

If you prefer not to use docker-compose:

```bash
# Start MySQL
docker run -d \
  --name test-mysql \
  -e MYSQL_ROOT_PASSWORD=testpassword \
  -e MYSQL_DATABASE=testdb \
  -p 3306:3306 \
  mysql:8.0

# Start PostgreSQL
docker run -d \
  --name test-postgres \
  -e POSTGRES_PASSWORD=testpassword \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16

# Run tests
uv run -m pytest tests/ -v

# Stop and remove containers
docker stop test-mysql test-postgres
docker rm test-mysql test-postgres
```

## Environment Variables

The test suite supports the following environment variables:

- `TEST_MYSQL`: Set to `true` or `false` to enable/disable MySQL tests (default: `true`)
- `TEST_POSTGRES`: Set to `true` or `false` to enable/disable PostgreSQL tests (default: `true`)
- `MYSQL_URL`: MySQL connection URL (default: `mysql+pymysql://root:testpassword@localhost:3306/testdb`)
- `POSTGRES_URL`: PostgreSQL connection URL (default: `postgresql://postgres:testpassword@localhost:5432/testdb`)

### Examples:

```bash
# Run only SQLite tests
TEST_MYSQL=false TEST_POSTGRES=false uv run -m pytest tests/

# Run only MySQL tests
TEST_POSTGRES=false uv run -m pytest tests/

# Use custom database URLs
MYSQL_URL=mysql+pymysql://user:pass@localhost:3307/mydb uv run -m pytest tests/
```

## GitHub Actions

The GitHub Actions workflow automatically runs tests against all supported databases using service containers. No additional configuration is needed - just push your changes and the workflow will:

1. Start MySQL and PostgreSQL service containers
2. Run tests against SQLite, MySQL, and PostgreSQL
3. Upload coverage reports

See [.github/workflows/test.yml](../.github/workflows/test.yml) for details.

## Troubleshooting

### Connection Refused Errors

If you get connection refused errors, make sure:
1. Docker containers are running: `docker-compose ps`
2. Databases are ready: check the health status
3. Ports are not already in use: `netstat -tuln | grep -E '(3306|5432)'`

### Permission Errors

If you get permission errors with MySQL:
```bash
# Reset MySQL container
docker-compose down -v
docker-compose up -d
```

### Python Dependencies

Make sure you have the database drivers installed:
```bash
uv pip install psycopg2-binary pymysql
```
