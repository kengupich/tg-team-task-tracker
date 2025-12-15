"""
Simplified task CRUD tests using isolated test database.
"""
import pytest
import sys
import os
import tempfile
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    create_task, get_task_by_id, update_task_field, delete_task,
    get_group_tasks, add_user, create_group, get_group_users,
    get_user_by_id, DB_FILE, add_user_to_group, init_db
)


@pytest.fixture(scope='function')
def isolated_db():
    """Create isolated database for each test."""
    import database
    
    # Create temporary database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Save original DB_FILE
    original_db = database.DB_FILE
    
    # Switch to temp database
    database.DB_FILE = db_path
    
    # Initialize schema
    database.init_db()
    
    yield db_path
    
    # Restore original
    database.DB_FILE = original_db
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


class TestTaskCreation:
    """Test task creation."""
    
    def test_create_simple_task(self, isolated_db):
        """Test creating a basic task."""
        # Create group and user
        group_id = create_group("Test Group", "test_group")
        user_id = 1001
        add_user(user_id, "Test User", "testuser")
        add_user_to_group(user_id, group_id)
        
        # Create task
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=group_id,
            admin_id=user_id,
            title="Test Title"
        )
        
        assert task_id is not None
        
        # Verify task
        task = get_task_by_id(task_id)
        assert task is not None
        assert task['title'] == "Test Title"
        assert task['status'] == 'pending'
    
    def test_create_task_with_assignees(self, isolated_db):
        """Test creating task with multiple assignees."""
        # Create group
        group_id = create_group("Dev Team", "dev")
        
        # Create users
        admin_id = 2001
        add_user(admin_id, "Admin", "admin")
        add_user_to_group(admin_id, group_id)
        
        user_ids = []
        for i in range(3):
            uid = 3001 + i
            add_user(uid, f"User {i}", f"user{i}")
            add_user_to_group(uid, group_id)
            user_ids.append(uid)
        
        # Create task with assignees
        task_id = create_task(
            date="2025-12-21",
            time="14:00",
            description="Team task",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=user_ids,
            title="Multi-assignee"
        )
        
        assert task_id is not None
        
        task = get_task_by_id(task_id)
        assert task is not None
        
        import json
        assigned = json.loads(task['assigned_to_list'] or '[]')
        assert len(assigned) == 3
        assert all(uid in assigned for uid in user_ids)


class TestTaskUpdate:
    """Test task update operations."""
    
    def test_update_task_status(self, isolated_db):
        """Test updating task status."""
        from database import update_task_status
        
        # Setup
        group_id = create_group("QA Team", "qa")
        user_id = 4001
        add_user(user_id, "QA Lead", "qa_lead")
        add_user_to_group(user_id, group_id)
        
        # Create task
        task_id = create_task(
            date="2025-12-20",
            time="09:00",
            description="QA task",
            group_id=group_id,
            admin_id=user_id,
            title="Testing"
        )
        
        # Update status
        result = update_task_status(task_id, 'in_progress')
        assert result is True
        
        # Verify
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
    
    def test_update_task_title(self, isolated_db):
        """Test updating task title."""
        group_id = create_group("Team", "team")
        user_id = 5001
        add_user(user_id, "Member", "member")
        add_user_to_group(user_id, group_id)
        
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Original desc",
            group_id=group_id,
            admin_id=user_id,
            title="Original"
        )
        
        # Update
        result = update_task_field(task_id, 'title', 'Updated Title')
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['title'] == 'Updated Title'
    
    def test_update_task_date(self, isolated_db):
        """Test updating task deadline date."""
        group_id = create_group("Team", "team")
        user_id = 6001
        add_user(user_id, "Member", "member")
        add_user_to_group(user_id, group_id)
        
        task_id = create_task(
            date="2025-12-20",
            time="15:00",
            description="Dated task",
            group_id=group_id,
            admin_id=user_id,
            title="Deadline"
        )
        
        # Update date
        new_date = "2025-12-25"
        result = update_task_field(task_id, 'date', new_date)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['date'] == new_date


class TestTaskDeletion:
    """Test task deletion."""
    
    def test_delete_task(self, isolated_db):
        """Test deleting a task."""
        group_id = create_group("Team", "team")
        user_id = 7001
        add_user(user_id, "Admin", "admin")
        add_user_to_group(user_id, group_id)
        
        task_id = create_task(
            date="2025-12-20",
            time="11:00",
            description="Deletable task",
            group_id=group_id,
            admin_id=user_id,
            title="Delete Me"
        )
        
        # Delete
        result = delete_task(task_id)
        assert result is True
        
        # Verify deletion
        task = get_task_by_id(task_id)
        assert task is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
