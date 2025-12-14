"""Integration tests for sqlacrossover"""

from __future__ import annotations

import io
import os
import socket

import pytest
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, ForeignKey, Table, MetaData, Text

from sqlacrossover import (
    GenericSource,
    GenericTarget,
    FileTarget,
    Crossover,
)


# Database connection URLs from environment variables or defaults
MYSQL_URL = os.getenv(
    'MYSQL_URL',
    'mysql+pymysql://root:testpassword@localhost:3306/testdb'
)
POSTGRES_URL = os.getenv(
    'POSTGRES_URL',
    'postgresql://postgres:testpassword@localhost:5432/testdb'
)

# Determine which databases to test
TEST_SQLITE = True
TEST_MYSQL = os.getenv('TEST_MYSQL', 'true').lower() in ('true', '1', 'yes')
TEST_POSTGRES = os.getenv('TEST_POSTGRES', 'true').lower() in ('true', '1', 'yes')


def _sqlite_engine(*, foreign_keys: bool) -> sa.Engine:
    engine = sa.create_engine("sqlite:///:memory:")

    if foreign_keys:
        @sa.event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-redef]
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()

    return engine


def _default_port_for_driver(drivername: str) -> int | None:
    if drivername.startswith("mysql"):
        return 3306
    if drivername.startswith("postgresql"):
        return 5432
    return None


def _can_open_tcp(url: str) -> bool:
    parsed = sa.engine.make_url(url)
    host = parsed.host or "localhost"
    port = parsed.port or _default_port_for_driver(parsed.drivername)
    if port is None:
        return True
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (OSError, PermissionError):
        return False


def get_database_configs():
    """Return list of database configurations to test"""
    configs: list[object] = []
    
    if TEST_SQLITE:
        configs.append(pytest.param(('sqlite', 'sqlite:///:memory:'), id='sqlite'))
    
    if TEST_MYSQL:
        mark = ()
        if not _can_open_tcp(MYSQL_URL):
            mark = (
                pytest.mark.skip(
                    reason="MySQL not reachable (set TEST_MYSQL=false to disable explicitly)."
                ),
            )
        configs.append(pytest.param(('mysql', MYSQL_URL), id='mysql', marks=mark))
    
    if TEST_POSTGRES:
        mark = ()
        if not _can_open_tcp(POSTGRES_URL):
            mark = (
                pytest.mark.skip(
                    reason="Postgres not reachable (set TEST_POSTGRES=false to disable explicitly)."
                ),
            )
        configs.append(pytest.param(('postgresql', POSTGRES_URL), id='postgresql', marks=mark))
    
    return configs


def create_test_schema(dialect_name='sqlite'):
    """Create test schema compatible with different database dialects"""
    metadata = MetaData()
    
    # Use Text for larger fields to be compatible with all databases
    content_type = Text if dialect_name == 'postgresql' else String(1000)
    
    # Create tables with foreign key relationship
    Table(
        'users',
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('name', String(50)),
        Column('email', String(100)),
    )
    
    Table(
        'posts',
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('user_id', Integer, ForeignKey('users.id')),
        Column('title', String(200)),
        Column('content', content_type),
    )

    return metadata


def populate_test_data(engine, metadata):
    """Insert test data into the database"""
    users_table = metadata.tables['users']
    posts_table = metadata.tables['posts']
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(
                users_table.insert(),
                [
                    {'name': 'Alice', 'email': 'alice@example.com'},
                    {'name': 'Bob', 'email': 'bob@example.com'},
                    {'name': 'Charlie', 'email': 'charlie@example.com'},
                ]
            )
            conn.execute(
                posts_table.insert(),
                [
                    {'user_id': 1, 'title': 'First Post', 'content': 'Hello World'},
                    {'user_id': 1, 'title': 'Second Post', 'content': 'More content'},
                    {'user_id': 2, 'title': 'Bob Post', 'content': 'Bob content'},
                ]
            )


@pytest.fixture(params=get_database_configs())
def source_db(request):
    """Create a database with test data for each supported database type"""
    db_name, db_url = request.param
    
    # For non-SQLite databases, create a unique schema/database for this test
    if db_name != 'sqlite':
        # Extract base URL and create test-specific database
        import time
        test_db_name = f"test_{int(time.time() * 1000)}"
        
        if db_name == 'mysql':
            # Create test database
            base_engine = sa.create_engine(
                MYSQL_URL.rsplit('/', 1)[0],
                poolclass=sa.pool.NullPool
            )
            with base_engine.connect() as conn:
                conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                    sa.text(f"CREATE DATABASE IF NOT EXISTS {test_db_name}")
                )
            base_engine.dispose()
            db_url = MYSQL_URL.rsplit('/', 1)[0] + f'/{test_db_name}'
        elif db_name == 'postgresql':
            base_engine = sa.create_engine(
                POSTGRES_URL.rsplit("/", 1)[0] + "/postgres",
                poolclass=sa.pool.NullPool,
                isolation_level="AUTOCOMMIT",
            )
            with base_engine.connect() as conn:
                conn.execute(sa.text(f"CREATE DATABASE {test_db_name}"))
            base_engine.dispose()
            db_url = POSTGRES_URL.rsplit("/", 1)[0] + f"/{test_db_name}"

    engine = (
        _sqlite_engine(foreign_keys=True)
        if db_name == "sqlite"
        else sa.create_engine(db_url)
    )
    
    # Create schema
    metadata = create_test_schema(db_name)
    metadata.create_all(engine)
    
    # Populate data
    populate_test_data(engine, metadata)
    
    yield engine
    
    # Cleanup
    metadata.drop_all(engine)
    engine.dispose()

    if db_name == 'mysql':
        base_engine = sa.create_engine(
            MYSQL_URL.rsplit('/', 1)[0],
            poolclass=sa.pool.NullPool,
        )
        with base_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                sa.text(f"DROP DATABASE IF EXISTS {test_db_name}")
            )
        base_engine.dispose()
    elif db_name == "postgresql":
        base_engine = sa.create_engine(
            POSTGRES_URL.rsplit("/", 1)[0] + "/postgres",
            poolclass=sa.pool.NullPool,
            isolation_level="AUTOCOMMIT",
        )
        with base_engine.connect() as conn:
            conn.execute(sa.text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        base_engine.dispose()


@pytest.fixture
def target_db(source_db):
    """Create an empty database of the same type as source"""
    source_url = str(source_db.url)
    
    if 'sqlite' in source_url:
        engine = _sqlite_engine(foreign_keys=True)
        try:
            yield engine
        finally:
            engine.dispose()
    elif 'mysql' in source_url:
        import time
        test_db_name = f"target_{int(time.time() * 1000)}"
        base_engine = sa.create_engine(
            MYSQL_URL.rsplit('/', 1)[0],
            poolclass=sa.pool.NullPool,
        )
        with base_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                sa.text(f"CREATE DATABASE IF NOT EXISTS {test_db_name}")
            )
        base_engine.dispose()
        target_url = MYSQL_URL.rsplit('/', 1)[0] + f'/{test_db_name}'
        target_engine = sa.create_engine(target_url, poolclass=sa.pool.NullPool)
        
        yield target_engine
        
        # Cleanup target database
        target_engine.dispose()
        base_engine = sa.create_engine(
            MYSQL_URL.rsplit('/', 1)[0],
            poolclass=sa.pool.NullPool,
        )
        with base_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                sa.text(f"DROP DATABASE IF EXISTS {test_db_name}")
            )
        base_engine.dispose()
    elif 'postgres' in source_url:
        import time
        test_db_name = f"target_{int(time.time() * 1000)}"
        # Create a separate database for target
        base_engine = sa.create_engine(
            POSTGRES_URL.rsplit('/', 1)[0] + '/postgres',
            poolclass=sa.pool.NullPool,
            isolation_level="AUTOCOMMIT"
        )
        with base_engine.connect() as conn:
            conn.execute(sa.text(f"CREATE DATABASE {test_db_name}"))
        base_engine.dispose()
        
        target_url = POSTGRES_URL.rsplit('/', 1)[0] + f'/{test_db_name}'
        target_engine = sa.create_engine(target_url, poolclass=sa.pool.NullPool)
        
        yield target_engine
        
        # Cleanup target database
        target_engine.dispose()
        base_engine = sa.create_engine(
            POSTGRES_URL.rsplit('/', 1)[0] + '/postgres',
            poolclass=sa.pool.NullPool,
            isolation_level="AUTOCOMMIT"
        )
        with base_engine.connect() as conn:
            conn.execute(sa.text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        base_engine.dispose()


class TestCrossover:
    
    def test_basic_migration(self, source_db, target_db):
        """Test basic data migration between databases"""
        with GenericSource(source_db) as source, GenericTarget(target_db) as target:
            # Create schema in target
            target.create_all(source.meta)
            
            # Run migration
            crossover = Crossover(source, target, batch_size=100)
            crossover.run()
        
        # Verify data was copied (after context manager commits)
        with target_db.connect() as conn:
            users = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
            posts = conn.execute(sa.text("SELECT COUNT(*) FROM posts")).scalar()
            
            assert users == 3
            assert posts == 3
            
            # Verify specific data
            alice = conn.execute(
                sa.text("SELECT name, email FROM users WHERE name = 'Alice'")
            ).first()
            assert alice.email == 'alice@example.com'
    
    def test_transaction_rollback(self, source_db):
        """Test that transaction rolls back on error"""
        target_engine = sa.create_engine("sqlite:///:memory:")
        
        with GenericSource(source_db) as source, GenericTarget(target_engine) as target:
            # Create schema
            target.create_all(source.meta)
            
            # Add a unique constraint that will cause a violation
            with target_engine.connect() as conn:
                with conn.begin():
                    conn.execute(sa.text("CREATE UNIQUE INDEX idx_email ON users(email)"))
                    # Insert one user to cause conflict
                    conn.execute(sa.text("INSERT INTO users (name, email) VALUES ('Test', 'alice@example.com')"))
            
            # Try to run migration (should fail due to unique constraint)
            crossover = Crossover(source, target, batch_size=100)
            
            with pytest.raises(sa.exc.IntegrityError):
                crossover.run_in_transaction()

        with target_engine.connect() as conn:
            users = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
            posts = conn.execute(sa.text("SELECT COUNT(*) FROM posts")).scalar()
            assert users == 1
            assert posts == 0
    
    def test_batch_processing(self, source_db, target_db):
        """Test that batch processing works correctly"""
        with GenericSource(source_db) as source, GenericTarget(target_db) as target:
            target.create_all(source.meta)
            
            # Use small batch size
            crossover = Crossover(source, target, batch_size=1)
            crossover.run()
        
        # Should still copy all data (verify after commit)
        with target_db.connect() as conn:
            users = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
            assert users == 3
    
    def test_file_target_sql_dump(self, source_db):
        """Test dumping to SQL file"""
        with GenericSource(source_db) as source:
            output = io.StringIO()
            target = FileTarget(output, dialect=source_db.dialect)
            
            # Dump schema
            target.create_all(source.meta)
            
            # Dump data
            crossover = Crossover(source, target, batch_size=100)
            crossover.run()
            
            sql_output = output.getvalue()
            
            # Verify SQL contains CREATE TABLE statements
            assert "CREATE TABLE" in sql_output
            assert "users" in sql_output
            assert "posts" in sql_output
            
            # Verify SQL contains INSERT statements
            assert "INSERT" in sql_output
            assert "Alice" in sql_output
            assert "alice@example.com" in sql_output
    
    def test_table_ordering(self, source_db, target_db):
        """Test that tables are created in correct order (respecting foreign keys)"""
        with GenericSource(source_db) as source, GenericTarget(target_db) as target:
            target.create_all(source.meta)
            
            # Verify both tables exist
            inspector = sa.inspect(target_db)
            tables = inspector.get_table_names()
            
            assert 'users' in tables
            assert 'posts' in tables
            
            # Run migration
            crossover = Crossover(source, target, batch_size=100)
            crossover.run()
        
        # Verify foreign key constraint works (after commit)
        with target_db.connect() as conn:
            with pytest.raises(sa.exc.IntegrityError):
                with conn.begin():
                    conn.execute(
                        sa.text(
                            "INSERT INTO posts (id, user_id, title, content) "
                            "VALUES (998, 9999, 'Bad', 'Bad content')"
                        )
                    )

            with conn.begin():
                # This should work (use explicit id to avoid sequence issues)
                conn.execute(
                    sa.text("INSERT INTO posts (id, user_id, title, content) VALUES (999, 1, 'Test', 'Test content')")
                )
            
            # Verify it was inserted
            count = conn.execute(sa.text("SELECT COUNT(*) FROM posts")).scalar()
            assert count == 4  # 3 original + 1 new
    
    def test_empty_database(self):
        """Test migration of empty database"""
        source_engine = sa.create_engine("sqlite:///:memory:")
        target_engine = sa.create_engine("sqlite:///:memory:")
        
        # Create schema without data in source
        metadata = MetaData()
        Table(
            'empty_table',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('data', String(100)),
        )
        metadata.create_all(source_engine)
        
        with GenericSource(source_engine) as source, GenericTarget(target_engine) as target:
            target.create_all(source.meta)

            crossover = Crossover(source, target, batch_size=100)
            crossover.run()

        # Verify table exists but is empty (after commit)
        with target_engine.connect() as conn:
            count = conn.execute(sa.text("SELECT COUNT(*) FROM empty_table")).scalar()
            assert count == 0
    
    def test_cross_database_migration(self):
        """Test migration from one database type to another"""
        # SQLite source
        source_engine = sa.create_engine("sqlite:///:memory:")
        metadata = create_test_schema('sqlite')
        metadata.create_all(source_engine)
        populate_test_data(source_engine, metadata)
        
        # SQLite target
        target_engine = sa.create_engine("sqlite:///:memory:")
        
        with GenericSource(source_engine) as source, GenericTarget(target_engine) as target:
            target.create_all(source.meta)

            crossover = Crossover(source, target, batch_size=100)
            crossover.run()

        # Verify data was copied (after commit)
        with target_engine.connect() as conn:
            users = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
            posts = conn.execute(sa.text("SELECT COUNT(*) FROM posts")).scalar()
            
            assert users == 3
            assert posts == 3
