"""
Tests for task CRUD operations.
All tests use test database (test_task_management.db) and never modify production database.
"""
import pytest
import json
from datetime import datetime, timedelta
from database import (
    create_group,
    create_task,
    get_task_by_id,
    update_task_field,
    delete_task,
    get_all_tasks,
    get_group_tasks,
)


class TestTaskCreation:
    """Tests for task creation operations."""
    
    def test_create_task_basic(self, test_db, test_group, test_task, db_connection):
        """Test creating a basic task."""
        # Setup: Create group
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        assert group_id is not None, "Failed to create test group"
        
        # Prepare task data
        task_data = test_task.copy()
        task_data["group_id"] = group_id
        
        # Create task
        task_id = create_task(
            date=task_data["date"],
            time=task_data["time"],
            description=task_data["description"],
            group_id=task_data["group_id"],
            admin_id=task_data["created_by"],
            assigned_to_list=task_data["assigned_to_list"],
            title=task_data["title"],
        )
        
        # Assert
        assert task_id is not None, "Failed to create task"
        assert isinstance(task_id, int), "Task ID should be integer"
        
        # Verify task exists
        task = get_task_by_id(task_id)
        assert task is not None, "Task not found after creation"
        assert task["title"] == task_data["title"]
        assert task["date"] == task_data["date"]
        assert task["time"] == task_data["time"]
    
    def test_create_task_with_no_assignees(self, test_db, test_group, db_connection):
        """Test creating a task with no assignees."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        
        # Create task (with empty list)
        task_id = create_task(
            date=datetime.now().strftime("%Y-%m-%d"),
            time="14:00",
            description="No one assigned",
            group_id=group_id,
            admin_id=test_group["admin_id"],
            assigned_to_list=[],  # Pass empty list instead of string
            title="Task with no assignees",
        )
        
        # Assert
        assert task_id is not None
        task = get_task_by_id(task_id)
        # Check that assigned_to_list is either None or empty list JSON
        assigned = task["assigned_to_list"]
        if assigned is None:
            # Empty list stored as None is acceptable
            pass
        else:
            # Or it should be JSON encoded empty list
            task_assignees = json.loads(assigned)
            assert task_assignees == []
    
    def test_create_task_with_multiple_assignees(self, test_db, test_group, db_connection):
        """Test creating a task with multiple assignees."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        assignees = [222222222, 333333333, 444444444]
        
        # Create task (pass list, not JSON string)
        task_id = create_task(
            date=datetime.now().strftime("%Y-%m-%d"),
            time="12:00",
            description="Multiple people assigned",
            group_id=group_id,
            admin_id=test_group["admin_id"],
            assigned_to_list=assignees,  # Pass list directly
            title="Multi-assignee task",
        )
        
        # Assert
        assert task_id is not None
        task = get_task_by_id(task_id)
        task_assignees = json.loads(task["assigned_to_list"])
        assert set(task_assignees) == set(assignees)


class TestTaskReading:
    """Tests for task reading/retrieval operations."""
    
    def test_get_nonexistent_task(self, test_db):
        """Test retrieving a non-existent task."""
        task = get_task_by_id(99999)
        assert task is None, "Should return None for non-existent task"
    
    def test_get_task_by_id(self, test_db, test_group, db_connection):
        """Test retrieving a task by ID."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        task_id = create_task(
            date=datetime.now().strftime("%Y-%m-%d"),
            time="11:00",
            description="Find me",
            group_id=group_id,
            admin_id=test_group["admin_id"],
            assigned_to_list="[]",
            title="Get me",
        )
        
        # Retrieve
        task = get_task_by_id(task_id)
        
        # Assert
        assert task is not None
        assert task["task_id"] == task_id
        assert task["title"] == "Get me"
    
    def test_get_all_tasks(self, test_db, test_group, db_connection):
        """Test retrieving all tasks."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = create_task(
                date=datetime.now().strftime("%Y-%m-%d"),
                time="10:00",
                description=f"Description {i}",
                group_id=group_id,
                admin_id=test_group["admin_id"],
                assigned_to_list=[],  # Pass empty list
                title=f"Task {i}",
            )
            task_ids.append(task_id)
        
        # Get all tasks
        all_tasks = get_all_tasks()
        
        # Assert
        assert len(all_tasks) >= 3
        # Some tasks might not have 'title' column in results, so check what we created
        created_task_ids = [t.get("task_id") for t in all_tasks if "task_id" in t]
        for task_id in task_ids:
            assert task_id in created_task_ids


class TestTaskUpdating:
    """Tests for task update operations."""
    
    def test_update_task_title(self, test_db, test_group, db_connection):
        """Test updating task title."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        task_id = create_task(
            date=datetime.now().strftime("%Y-%m-%d"),
            time="10:00",
            description="Desc",
            group_id=group_id,
            admin_id=test_group["admin_id"],
            assigned_to_list="[]",
            title="Original title",
        )
        
        # Update
        new_title = "Updated title"
        result = update_task_field(task_id, "title", new_title)
        assert result, "Failed to update task title"
        
        # Verify
        task = get_task_by_id(task_id)
        assert task["title"] == new_title
    
    def test_update_task_description(self, test_db, test_group, db_connection):
        """Test updating task description."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        task_id = create_task(
            date=datetime.now().strftime("%Y-%m-%d"),
            time="10:00",
            description="Original description",
            group_id=group_id,
            admin_id=test_group["admin_id"],
            assigned_to_list="[]",
            title="Task",
        )
        
        # Update
        new_desc = "Updated description"
        result = update_task_field(task_id, "description", new_desc)
        assert result, "Failed to update task description"
        
        # Verify
        task = get_task_by_id(task_id)
        assert task["description"] == new_desc


class TestTaskDeletion:
    """Tests for task deletion operations."""
    
    def test_delete_task(self, test_db, test_group, db_connection):
        """Test deleting a task."""
        # Setup
        group_id = create_group(test_group["name"], admin_id=test_group["admin_id"])
        task_id = create_task(
            date=datetime.now().strftime("%Y-%m-%d"),
            time="10:00",
            description="Desc",
            group_id=group_id,
            admin_id=test_group["admin_id"],
            assigned_to_list="[]",
            title="To be deleted",
        )
        
        # Verify it exists
        assert get_task_by_id(task_id) is not None
        
        # Delete
        result = delete_task(task_id)
        assert result, "Failed to delete task"
        
        # Verify it's deleted
        assert get_task_by_id(task_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
