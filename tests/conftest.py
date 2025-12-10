"""Pytest configuration and fixtures."""
import pytest
import sqlite3
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to sys.path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db():
    """Create a temporary test database."""
    import database
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Override DB_FILE in database module
    original_db = database.DB_FILE
    database.DB_FILE = db_path
    
    yield db_path
    
    # Restore original DB_FILE
    database.DB_FILE = original_db
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def test_db(temp_db):
    """Initialize test database with schema."""
    import database
    
    # Initialize fresh database with schema
    database.init_db()
    return temp_db


@pytest.fixture(autouse=True)
def reset_db_file():
    """Ensure DB_FILE is reset before each test."""
    import database
    original = database.DB_FILE
    yield
    database.DB_FILE = original


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
