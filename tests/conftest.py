"""Pytest configuration and fixtures for PostgreSQL tests."""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    raise ImportError("psycopg2 is required for tests. Install with: pip install psycopg2-binary")

# Add parent directory to sys.path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test database configuration
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/task_management_test"
)

# Use main database for local testing if TEST_DATABASE_URL not set
if "TEST_DATABASE_URL" not in os.environ:
    os.environ["LOCAL_DATABASE_URL"] = TEST_DB_URL


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment once per session."""
    try:
        # Test PostgreSQL connection
        conn = psycopg2.connect(TEST_DB_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        print(f"\nPostgreSQL test database available: {TEST_DB_URL.split('@')[1] if '@' in TEST_DB_URL else 'local'}")
    except psycopg2.Error as e:
        # Only skip if test file is not a mock test
        # Mock tests don't require PostgreSQL
        print(f"\nPostgreSQL not available: {e}")
        print("Mock and unit tests can still run without PostgreSQL")
    
    yield


@pytest.fixture
def test_db(request):
    """Create a fresh test database for each test."""
    # Check if test requires PostgreSQL (marker or file name)
    is_mock_test = "mock" in request.node.nodeid
    is_async_mock_test = "test_db_async_mock" in request.node.fspath.basename
    
    if not is_mock_test and not is_async_mock_test:
        # Set environment to use test database
        os.environ["DATABASE_URL"] = TEST_DB_URL
        
        import database
        from db_postgres import DatabaseConnection
        
        # Clear any cached connection
        import db_postgres
        db_postgres._db_connection = None
        
        # Initialize database schema
        try:
            database.init_db()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
        
        # Verify database is ready
        db_conn = db_postgres.get_db_connection()
        conn = db_conn.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='tasks'")
        if not cursor.fetchone()[0]:
            conn.close()
            raise RuntimeError("Task table not created properly")
        
        # Clear all data from tables before test
        cursor.execute("TRUNCATE TABLE task_assignees CASCADE")
        cursor.execute("TRUNCATE TABLE user_groups CASCADE")
        cursor.execute("TRUNCATE TABLE group_admins CASCADE")
        cursor.execute("TRUNCATE TABLE task_history CASCADE")
        cursor.execute("TRUNCATE TABLE task_media CASCADE")
        cursor.execute("TRUNCATE TABLE tasks CASCADE")
        cursor.execute("TRUNCATE TABLE registration_requests CASCADE")
        cursor.execute("TRUNCATE TABLE users CASCADE")
        cursor.execute("TRUNCATE TABLE groups CASCADE")
        
        conn.close()
    
    yield TEST_DB_URL


@pytest.fixture
def db_connection(test_db):
    """Provide a database connection for testing."""
    import db_postgres
    db_conn = db_postgres.get_db_connection()
    conn = db_conn.get_connection()
    yield conn
    conn.close()


# Test data fixtures
@pytest.fixture
def test_admin_user():
    """Test admin user data."""
    return {
        "user_id": 111111111,
        "name": "Test Admin",
        "username": "testadmin",
        "registered": 1,
        "banned": 0,
        "deleted": 0,
    }


@pytest.fixture
def test_user_1():
    """Test user 1 data."""
    return {
        "user_id": 222222222,
        "name": "Test User 1",
        "username": "testuser1",
        "registered": 1,
        "banned": 0,
        "deleted": 0,
    }


@pytest.fixture
def test_user_2():
    """Test user 2 data."""
    return {
        "user_id": 333333333,
        "name": "Test User 2",
        "username": "testuser2",
        "registered": 1,
        "banned": 0,
        "deleted": 0,
    }


@pytest.fixture
def test_group():
    """Test group data."""
    return {
        "name": "Test Group",
        "admin_id": 111111111,
    }


@pytest.fixture
def test_task():
    """Test task data."""
    return {
        "title": "Test Task",
        "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "time": "10:00",
        "description": "This is a test task",
        "group_id": 1,
        "assigned_to_list": '[222222222, 333333333]',
        "status": "pending",
        "created_by": 111111111,
    }


@pytest.fixture
def sample_users():
    """Sample user data for testing."""
    return [
        {"user_id": 100001, "name": "Test Admin"},
        {"user_id": 100002, "name": "Test User 1"},
        {"user_id": 100003, "name": "Test User 2"},
    ]


@pytest.fixture
def sample_groups():
    """Sample group data for testing."""
    return [
        {"name": "Test Group 1"},
        {"name": "Test Group 2"},
    ]
