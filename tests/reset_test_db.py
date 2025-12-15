"""
Script to reset test database.
Removes and reinitializes task_management.db for clean testing.
"""
import os
import sqlite3
from pathlib import Path

# Get database path
db_path = Path(__file__).parent.parent / "task_management.db"

if db_path.exists():
    print(f"Removing old database: {db_path}")
    os.remove(db_path)
else:
    print(f"Database not found: {db_path}")

print("Database reset complete. Run tests to initialize fresh database.")
