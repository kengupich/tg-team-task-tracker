"""Tests for task-related database functions."""
import pytest
from database import (
    create_task, get_task_by_id, get_group_tasks, 
    update_task_status, update_task_assignment, delete_task,
    add_user, create_group, add_user_to_group
)


class TestTaskCreation:
    """Test task creation and retrieval."""
    
    def test_create_task(self, test_db):
        """Test creating a task."""
        # Setup
        user_id = 100001
        add_user(user_id, "Admin User")
        group_id = create_group("Test Group")
        
        # Create task
        task_id = create_task(
            date="2025-12-10",
            time="14:00",
            description="Test task description",
            group_id=group_id,
            admin_id=user_id
        )
        
        assert task_id is not None
        assert isinstance(task_id, int)
    
    def test_create_task_with_assignees(self, test_db):
        """Test creating a task with assigned users."""
        # Setup
        admin_id = 100001
        user1_id = 100002
        user2_id = 100003
        
        add_user(admin_id, "Admin")
        add_user(user1_id, "User 1")
        add_user(user2_id, "User 2")
        
        group_id = create_group("Test Group")
        add_user_to_group(user1_id, group_id)
        add_user_to_group(user2_id, group_id)
        
        # Create task with assignees
        task_id = create_task(
            date="2025-12-10",
            time="14:00",
            description="Multi-assignee task",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[user1_id, user2_id]
        )
        
        assert task_id is not None
        
        # Verify task
        task = get_task_by_id(task_id)
        assert task is not None
        assert task['description'] == "Multi-assignee task"
        assert task['group_id'] == group_id
    
    def test_get_task_by_id(self, test_db):
        """Test retrieving task by ID."""
        # Setup
        user_id = 100001
        add_user(user_id, "Admin User")
        group_id = create_group("Test Group")
        
        task_id = create_task("2025-12-10", "14:00", "Test task", group_id, user_id)
        
        # Retrieve task
        task = get_task_by_id(task_id)
        
        assert task is not None
        assert task['task_id'] == task_id
        assert task['description'] == "Test task"
        assert task['date'] == "2025-12-10"
        assert task['time'] == "14:00"
        assert task['status'] == "pending"
    
    def test_get_nonexistent_task(self, test_db):
        """Test retrieving non-existent task."""
        task = get_task_by_id(99999)
        assert task is None
    
    def test_get_group_tasks(self, test_db):
        """Test retrieving all tasks for a group."""
        # Setup
        admin_id = 100001
        add_user(admin_id, "Admin")
        group_id = create_group("Test Group")
        
        # Create multiple tasks
        task1 = create_task("2025-12-10", "10:00", "Task 1", group_id, admin_id)
        task2 = create_task("2025-12-11", "14:00", "Task 2", group_id, admin_id)
        task3 = create_task("2025-12-12", "16:00", "Task 3", group_id, admin_id)
        
        # Get all tasks
        tasks = get_group_tasks(group_id)
        
        assert len(tasks) == 3
        task_ids = [t['task_id'] for t in tasks]
        assert task1 in task_ids
        assert task2 in task_ids
        assert task3 in task_ids


class TestTaskUpdates:
    """Test task update operations."""
    
    def test_update_task_status(self, test_db):
        """Test updating task status."""
        # Setup
        admin_id = 100001
        add_user(admin_id, "Admin")
        group_id = create_group("Test Group")
        task_id = create_task("2025-12-10", "14:00", "Test task", group_id, admin_id)
        
        # Update status
        result = update_task_status(task_id, "completed")
        assert result is True
        
        # Verify
        task = get_task_by_id(task_id)
        assert task['status'] == "completed"
    
    def test_update_task_status_to_cancelled(self, test_db):
        """Test updating task status to cancelled."""
        admin_id = 100001
        add_user(admin_id, "Admin")
        group_id = create_group("Test Group")
        task_id = create_task("2025-12-10", "14:00", "Test task", group_id, admin_id)
        
        result = update_task_status(task_id, "cancelled")
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['status'] == "cancelled"
    
    def test_update_task_assignment(self, test_db):
        """Test updating task assignment list."""
        # Setup
        admin_id = 100001
        user1 = 100002
        user2 = 100003
        
        add_user(admin_id, "Admin")
        add_user(user1, "User 1")
        add_user(user2, "User 2")
        
        group_id = create_group("Test Group")
        task_id = create_task("2025-12-10", "14:00", "Test task", group_id, admin_id)
        
        # Update assignment
        result = update_task_assignment(task_id, [user1, user2])
        assert result is True
        
        # Verify (task should be updated)
        task = get_task_by_id(task_id)
        assert task is not None


class TestTaskDeletion:
    """Test task deletion operations."""
    
    def test_delete_task(self, test_db):
        """Test deleting a task."""
        # Setup
        admin_id = 100001
        add_user(admin_id, "Admin")
        group_id = create_group("Test Group")
        task_id = create_task("2025-12-10", "14:00", "Test task", group_id, admin_id)
        
        # Delete task
        result = delete_task(task_id)
        assert result is True
        
        # Verify task is deleted
        task = get_task_by_id(task_id)
        assert task is None
    
    def test_delete_nonexistent_task(self, test_db):
        """Test deleting non-existent task returns False."""
        result = delete_task(99999)
        assert result is False


class TestTaskFiltering:
    """Test filtering tasks by various criteria."""
    
    def test_get_tasks_by_status(self, test_db):
        """Test getting tasks filtered by status."""
        # Setup
        admin_id = 100001
        add_user(admin_id, "Admin")
        group_id = create_group("Test Group")
        
        # Create tasks with different statuses
        task1 = create_task("2025-12-10", "10:00", "Pending task", group_id, admin_id)
        task2 = create_task("2025-12-11", "14:00", "Completed task", group_id, admin_id)
        update_task_status(task2, "completed")
        
        # Get all tasks
        all_tasks = get_group_tasks(group_id)
        assert len(all_tasks) == 2
        
        # Verify statuses
        statuses = [t['status'] for t in all_tasks]
        assert "pending" in statuses
        assert "completed" in statuses
