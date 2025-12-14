# sqlacrossover

Cross-database migration tool based on SQLAlchemy

## Features

* Copy data and schema between SQLAlchemy-supported databases
* Table ordering - taking the foreign keys dependencies in consideration
* Data processing in batches
* Wrap the process in transaction to get consistent results
* Dump schema and data to SQL file

## Installation

Using [uv](https://github.com/astral-sh/uv) (recommended):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install sqlacrossover as a tool
uv tool install sqlacrossover
```

Or with pip:

```bash
pip install sqlacrossover
```

### Database Support

SQLite is supported out of the box (built-in with Python). For other databases, install with the appropriate extras:

**PostgreSQL:**
```bash
uv tool install "sqlacrossover[postgresql]"
```

**MySQL/MariaDB:**
```bash
uv tool install "sqlacrossover[mysql]"
```

**SQL Server:**
```bash
uv tool install "sqlacrossover[mssql]"
```

**Oracle:**
```bash
uv tool install "sqlacrossover[oracle]"
```

**Multiple databases:**
```bash
# PostgreSQL + MySQL
uv tool install "sqlacrossover[postgresql,mysql]"

# All supported databases
uv tool install "sqlacrossover[all]"
```

If you're using uv for project dependency management:

```bash
uv add "sqlacrossover[postgresql,mysql]"
```

## Usage

### Basic database-to-database migration

```bash
sqlacrossover 'mysql+pymysql:///sourcedatabase?charset=utf8' postgresql:///targetdatabase
```

### Create tables in target database

```bash
sqlacrossover --create-all 'sqlite:///source.db' postgresql:///targetdb
```

### Export to SQL file

```bash
sqlacrossover --create-all 'postgresql:///mydb' file://dump.sql
```

Or output to stdout:

```bash
sqlacrossover --create-all 'postgresql:///mydb' -
```

### Advanced Options

* `--create-all` - Create tables in target database before copying data
* `--batch-size N` - Process data in batches of N rows (default: 10000)
* `--no-transaction` - Don't wrap inserts in a single transaction

## Development

### Setup Development Environment

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/ei-grad/sqlacrossover.git
cd sqlacrossover

# Create .venv and install dependencies
uv sync

# Run tests
uv run -m pytest
```

### Running Tests

The test suite includes integration tests against SQLite, MySQL, and PostgreSQL.

**Quick tests (SQLite only):**
```bash
TEST_MYSQL=false TEST_POSTGRES=false uv run -m pytest
```

**Full integration tests (requires Docker):**
```bash
# Run all tests (automatically starts containers)
make test-all

# Or manually
docker-compose up -d
uv run -m pytest
docker-compose down
```

For detailed testing instructions, see [TESTING.md](TESTING.md).

## TODO

* Write comprehensive documentation
* Implement additional options:
  * `--no-data`
  * `--tables`
  * `--exclude-tables`
  * `--truncate-non-empty`
  * `--skip-non-empty`
* Implement efficient driver-dependent insert methods:
  * PostgreSQL `COPY FROM` / `COPY TO`
  * MySQL `LOAD DATA LOCAL INFILE`

## Contributing

Pull requests implementing new features, adding tests, docs and fixing bugs are welcome.

Feel free to open an issue with any feedback or ideas.

## License

Apache License 2.0
