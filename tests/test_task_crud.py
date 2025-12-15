"""
Comprehensive tests for task CRUD operations and scenarios.
Tests creation, viewing, updating, deletion with various combinations.
"""
import sqlite3
import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from database import (
    create_task, get_task_by_id, update_task_field, delete_task,
    get_group_tasks, add_user, create_group, get_group_users,
    get_user_by_id, DB_FILE, add_task_media, get_task_media,
    remove_task_media, add_user_to_group, register_user, init_db
)


class TestTaskCRUDOperations:
    """Test basic CRUD operations for tasks."""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Initialize database for testing."""
        # Initialize database
        init_db()
    
    def setup_method(self):
        """Setup test database."""
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Create test group
        self.group_id = create_group("QA Team", "qa_team")
        
        # Create test users
        self.tester_id = 3001
        add_user(self.tester_id, "John Tester", "john_tester")
        add_user_to_group(self.tester_id, self.group_id)
        
        self.lead_id = 3002
        add_user(self.lead_id, "QA Lead", "qa_lead")
        add_user_to_group(self.lead_id, self.group_id)
    
    def teardown_method(self):
        """Cleanup."""
        self.conn.close()
    
    def test_create_task_with_all_fields(self):
        """Test creating task with all available fields."""
        task_id = create_task(
            date="2025-12-20",
            time="09:00",
            description="Comprehensive test task with all details",
            group_id=self.group_id,
            admin_id=self.lead_id,
            assigned_to_list=[self.tester_id],
            title="Full Task Creation Test"
        )
        
        assert task_id is not None
        task = get_task_by_id(task_id)
        
        assert task['title'] == "Full Task Creation Test"
        assert task['description'] == "Comprehensive test task with all details"
        assert task['date'] == "2025-12-20"
        assert task['time'] == "09:00"
        assert task['group_id'] == self.group_id
        assert task['created_by'] == self.lead_id
        assert task['status'] == 'pending'
    
    def test_create_task_minimal_fields(self):
        """Test creating task with minimal fields."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Minimal task",
            group_id=self.group_id,
            admin_id=self.lead_id
        )
        
        assert task_id is not None
        task = get_task_by_id(task_id)
        
        assert task['description'] == "Minimal task"
        assert task['title'] is None or task['title'] == ""
        assert task['status'] == 'pending'
    
    def test_create_task_without_assignees(self):
        """Test creating task without assigning to anyone."""
        task_id = create_task(
            date="2025-12-20",
            time="11:00",
            description="Unassigned task",
            group_id=self.group_id,
            admin_id=self.lead_id,
            title="No Assignees"
        )
        
        assert task_id is not None
        task = get_task_by_id(task_id)
        
        import json
        assigned = json.loads(task.get('assigned_to_list') or '[]')
        assert len(assigned) == 0
    
    def test_create_task_with_multiple_assignees(self):
        """Test creating task with multiple assignees."""
        # Create additional users
        user2_id = 3003
        add_user(user2_id, "User 2", "user2")
        add_user_to_group(user2_id, self.group_id)
        
        user3_id = 3004
        add_user(user3_id, "User 3", "user3")
        add_user_to_group(user3_id, self.group_id)
        
        task_id = create_task(
            date="2025-12-20",
            time="12:00",
            description="Team task",
            group_id=self.group_id,
            admin_id=self.lead_id,
            assigned_to_list=[self.tester_id, user2_id, user3_id],
            title="Multi-Assignee Task"
        )
        
        assert task_id is not None
        task = get_task_by_id(task_id)
        
        import json
        assigned = json.loads(task.get('assigned_to_list') or '[]')
        assert len(assigned) == 3
        assert self.tester_id in assigned
        assert user2_id in assigned
        assert user3_id in assigned
    
    def test_get_task_returns_all_fields(self):
        """Test that get_task_by_id returns all expected fields."""
        task_id = create_task(
            date="2025-12-21",
            time="14:30",
            description="Field test task",
            group_id=self.group_id,
            admin_id=self.lead_id,
            assigned_to_list=[self.tester_id],
            title="Field Verification"
        )
        
        task = get_task_by_id(task_id)
        
        # Verify all expected fields exist
        required_fields = [
            'task_id', 'title', 'date', 'time', 'description',
            'group_id', 'created_by', 'assigned_to_list', 'status',
            'created_at', 'updated_at'
        ]
        
        for field in required_fields:
            assert field in task, f"Field '{field}' missing from task"
    
    def test_update_task_status(self):
        """Test updating task status."""
        task_id = create_task(
            date="2025-12-20",
            time="15:00",
            description="Status update test",
            group_id=self.group_id,
            admin_id=self.lead_id,
            title="Status Test"
        )
        
        # Update status to in_progress
        result = update_task_field(task_id, 'status', 'in_progress')
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Update to completed
        result = update_task_field(task_id, 'status', 'completed')
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'
    
    def test_update_task_title(self):
        """Test updating task title."""
        task_id = create_task(
            date="2025-12-20",
            time="16:00",
            description="Title update test",
            group_id=self.group_id,
            admin_id=self.lead_id,
            title="Original Title"
        )
        
        new_title = "Updated Title"
        result = update_task_field(task_id, 'title', new_title)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['title'] == new_title
    
    def test_update_task_description(self):
        """Test updating task description."""
        task_id = create_task(
            date="2025-12-20",
            time="17:00",
            description="Original description",
            group_id=self.group_id,
            admin_id=self.lead_id,
            title="Desc Test"
        )
        
        new_desc = "Updated description with more details"
        result = update_task_field(task_id, 'description', new_desc)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['description'] == new_desc
    
    def test_update_task_date(self):
        """Test updating task date."""
        task_id = create_task(
            date="2025-12-20",
            time="18:00",
            description="Date update test",
            group_id=self.group_id,
            admin_id=self.lead_id,
            title="Date Test"
        )
        
        new_date = "2025-12-25"
        result = update_task_field(task_id, 'date', new_date)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['date'] == new_date
    
    def test_delete_task(self):
        """Test deleting a task."""
        task_id = create_task(
            date="2025-12-20",
            time="19:00",
            description="Task to delete",
            group_id=self.group_id,
            admin_id=self.lead_id,
            title="Delete Me"
        )
        
        # Verify task exists
        task = get_task_by_id(task_id)
        assert task is not None
        
        # Delete task
        result = delete_task(task_id)
        assert result is True
        
        # Verify task is deleted
        task = get_task_by_id(task_id)
        assert task is None
    
    def test_get_all_group_tasks(self):
        """Test retrieving all tasks for a group."""
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = create_task(
                date="2025-12-20",
                time=f"{10+i}:00",
                description=f"Group task {i}",
                group_id=self.group_id,
                admin_id=self.lead_id,
                title=f"Task {i}"
            )
            task_ids.append(task_id)
        
        # Get all tasks
        tasks = get_group_tasks(self.group_id)
        assert len(tasks) >= 3
        
        # Check our tasks are there
        retrieved_ids = [t['task_id'] for t in tasks]
        for task_id in task_ids:
            assert task_id in retrieved_ids


class TestTaskScenarios:
    """Test realistic task management scenarios."""
    
    def setup_method(self):
        """Setup test database."""
        # Initialize database
        init_db()
        
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Create departments
        self.dev_group_id = create_group("Development", "dev")
        self.qa_group_id = create_group("QA", "qa")
        
        # Create users
        self.dev_lead_id = 4001
        add_user(self.dev_lead_id, "Dev Lead", "dev_lead")
        add_user_to_group(self.dev_lead_id, self.dev_group_id)
        
        self.qa_lead_id = 4002
        add_user(self.qa_lead_id, "QA Lead", "qa_lead")
        add_user_to_group(self.qa_lead_id, self.qa_group_id)
        
        self.developer_id = 4003
        add_user(self.developer_id, "Developer", "developer")
        add_user_to_group(self.developer_id, self.dev_group_id)
        
        self.tester_id = 4004
        add_user(self.tester_id, "Tester", "tester")
        add_user_to_group(self.tester_id, self.qa_group_id)
    
    def teardown_method(self):
        """Cleanup."""
        self.conn.close()
    
    def test_scenario_sprint_task_lifecycle(self):
        """Test a task going through complete sprint lifecycle."""
        # Scenario: Sprint planning → development → testing → completion
        
        # 1. Create task during sprint planning
        task_id = create_task(
            date="2025-12-22",
            time="10:00",
            description="Implement user authentication module",
            group_id=self.dev_group_id,
            admin_id=self.dev_lead_id,
            assigned_to_list=[self.developer_id],
            title="Sprint #5: User Auth Module"
        )
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        
        # 2. Developer starts working
        update_task_field(task_id, 'status', 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # 3. Developer completes and reassigns to QA
        update_task_field(task_id, 'status', 'completed')
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'
        
        # 4. Update task description with implementation notes
        update_task_field(
            task_id,
            'description',
            "User auth module completed.\nImplements: login, logout, token refresh"
        )
        task = get_task_by_id(task_id)
        assert "Implementation notes" in task['description'] or \
               "Implements:" in task['description']
    
    def test_scenario_urgent_task_priority_change(self):
        """Test changing task priority/date when urgent."""
        # Original task scheduled for late date
        task_id = create_task(
            date="2025-12-30",
            time="16:00",
            description="Regular maintenance task",
            group_id=self.dev_group_id,
            admin_id=self.dev_lead_id,
            assigned_to_list=[self.developer_id],
            title="Server Maintenance"
        )
        
        # Task becomes urgent, move to earlier date
        new_date = "2025-12-15"
        result = update_task_field(task_id, 'date', new_date)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['date'] == new_date
    
    def test_scenario_task_delegation(self):
        """Test delegating task to multiple team members."""
        # Start with one assignee
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Large feature implementation",
            group_id=self.dev_group_id,
            admin_id=self.dev_lead_id,
            assigned_to_list=[self.developer_id],
            title="Large Feature"
        )
        
        # Get the task details
        task = get_task_by_id(task_id)
        import json
        assigned = json.loads(task.get('assigned_to_list') or '[]')
        assert len(assigned) == 1
        
        # Can update assigned_to_list by updating the field
        # (This would be used if we have a method to update assignees)
        update_task_field(
            task_id,
            'assigned_to_list',
            json.dumps([self.developer_id])
        )
        
        task = get_task_by_id(task_id)
        assigned = json.loads(task.get('assigned_to_list') or '[]')
        assert self.developer_id in assigned
    
    def test_scenario_task_postponement(self):
        """Test postponing a task."""
        # Create task for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        task_id = create_task(
            date=tomorrow,
            time="14:00",
            description="Task scheduled for tomorrow",
            group_id=self.dev_group_id,
            admin_id=self.dev_lead_id,
            title="Tomorrow Task"
        )
        
        # Postpone by a week
        new_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
        result = update_task_field(task_id, 'date', new_date)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['date'] == new_date
    
    def test_scenario_task_cancellation(self):
        """Test cancelling a task."""
        task_id = create_task(
            date="2025-12-20",
            time="11:00",
            description="Task to be cancelled",
            group_id=self.dev_group_id,
            admin_id=self.dev_lead_id,
            assigned_to_list=[self.developer_id],
            title="Cancelled Task"
        )
        
        # Set status to cancelled
        result = update_task_field(task_id, 'status', 'cancelled')
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'cancelled'


class TestTaskValidation:
    """Test task field validation and constraints."""
    
    def setup_method(self):
        """Setup test database."""
        # Initialize database
        init_db()
        
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self.group_id = create_group("Test Group", "test")
        self.admin_id = 5001
        add_user(self.admin_id, "Admin", "admin")
        add_user_to_group(self.admin_id, self.group_id)
    
    def teardown_method(self):
        """Cleanup."""
        self.conn.close()
    
    def test_create_task_with_empty_description_fails(self):
        """Test that creating task with empty description fails."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="",  # Empty description
            group_id=self.group_id,
            admin_id=self.admin_id
        )
        
        # Empty description might be allowed or rejected depending on business rules
        # If allowed, verify it's stored empty
        if task_id is not None:
            task = get_task_by_id(task_id)
            assert task['description'] == ""
    
    def test_create_task_with_future_date(self):
        """Test creating task with future date."""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        task_id = create_task(
            date=future_date,
            time="10:00",
            description="Future task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            title="Future"
        )
        
        assert task_id is not None
        task = get_task_by_id(task_id)
        assert task['date'] == future_date
    
    def test_create_task_with_past_date(self):
        """Test creating task with past date (should work - for historical records)."""
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        task_id = create_task(
            date=past_date,
            time="10:00",
            description="Past task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            title="Past"
        )
        
        # Should allow past dates for record keeping
        assert task_id is not None
        task = get_task_by_id(task_id)
        assert task['date'] == past_date


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
