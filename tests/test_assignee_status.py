"""
Tests for individual assignee status functionality.
Tests the new task_assignees table and status aggregation logic.
"""
import sqlite3
import pytest
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from database import (
    create_task, get_task_by_id, add_task_assignees,
    get_task_assignee_statuses, get_assignee_status,
    update_assignee_status, calculate_task_status,
    remove_task_assignee, add_user, create_group,
    get_group_users, DB_FILE, add_user_to_group, init_db
)


class TestAssigneeStatus:
    """Test individual assignee status tracking."""
    
    def setup_method(self):
        """Setup test database."""
        # Initialize database
        init_db()
        
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Create test group
        self.group_id = create_group("Test Group", "test_group")
        
        # Create test users
        self.user_ids = []
        for i in range(3):
            uid = 1000000 + i
            add_user(uid, f"test_user_{i}", f"user_{i}")
            add_user_to_group(uid, self.group_id)
            self.user_ids.append(uid)
        
        # Create admin
        self.admin_id = 2000000
        add_user(self.admin_id, "test_admin", "test_admin")
        add_user_to_group(self.admin_id, self.group_id)
    
    def teardown_method(self):
        """Cleanup."""
        self.conn.close()
    
    def test_add_task_assignees(self):
        """Test adding assignees to a task."""
        # Create task
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        assert task_id is not None
        
        # Verify assignees were added
        self.cursor.execute(
            "SELECT COUNT(*) as count FROM task_assignees WHERE task_id = ?",
            (task_id,)
        )
        count = self.cursor.fetchone()['count']
        assert count == 3, f"Expected 3 assignees, got {count}"
    
    def test_get_task_assignee_statuses(self):
        """Test retrieving all assignee statuses."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        statuses = get_task_assignee_statuses(task_id)
        
        # All should start as pending
        assert len(statuses) == 3
        for user_id in self.user_ids:
            assert statuses[user_id] == 'pending'
    
    def test_get_assignee_status(self):
        """Test getting individual assignee status."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=[self.user_ids[0]],
            title="Test Title"
        )
        
        status = get_assignee_status(task_id, self.user_ids[0])
        assert status == 'pending'
        
        # Non-existent assignee
        status = get_assignee_status(task_id, 999999)
        assert status is None
    
    def test_update_assignee_status(self):
        """Test updating individual assignee status."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # Update first user to in_progress
        result = update_assignee_status(task_id, self.user_ids[0], 'in_progress')
        assert result is True
        
        # Verify update
        status = get_assignee_status(task_id, self.user_ids[0])
        assert status == 'in_progress'
        
        # Other users should still be pending
        status = get_assignee_status(task_id, self.user_ids[1])
        assert status == 'pending'
    
    def test_invalid_status_update(self):
        """Test that invalid statuses are rejected."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=[self.user_ids[0]],
            title="Test Title"
        )
        
        # Try to set invalid status
        result = update_assignee_status(task_id, self.user_ids[0], 'invalid_status')
        assert result is False
        
        # Status should remain unchanged
        status = get_assignee_status(task_id, self.user_ids[0])
        assert status == 'pending'
    
    def test_calculate_task_status_all_pending(self):
        """Test task status when all assignees are pending."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        status = calculate_task_status(task_id)
        assert status == 'pending'
    
    def test_calculate_task_status_one_in_progress(self):
        """Test task status when one assignee is in_progress."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # One user starts working
        update_assignee_status(task_id, self.user_ids[0], 'in_progress')
        
        status = calculate_task_status(task_id)
        assert status == 'in_progress'
    
    def test_calculate_task_status_all_completed(self):
        """Test task status when all assignees complete."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # All users complete
        for user_id in self.user_ids:
            update_assignee_status(task_id, user_id, 'completed')
        
        status = calculate_task_status(task_id)
        assert status == 'completed'
    
    def test_calculate_task_status_mixed_completed_pending(self):
        """Test task status with mixed completed and pending."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # Two users complete, one pending
        update_assignee_status(task_id, self.user_ids[0], 'completed')
        update_assignee_status(task_id, self.user_ids[1], 'completed')
        # user_ids[2] stays pending
        
        status = calculate_task_status(task_id)
        # Should be pending (not all completed)
        assert status == 'pending'
    
    def test_calculate_task_status_all_cancelled(self):
        """Test task status when all assignees cancel."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # All users cancel
        for user_id in self.user_ids:
            update_assignee_status(task_id, user_id, 'cancelled')
        
        status = calculate_task_status(task_id)
        assert status == 'cancelled'
    
    def test_remove_task_assignee(self):
        """Test removing an assignee from a task."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # Remove one assignee
        result = remove_task_assignee(task_id, self.user_ids[0])
        assert result is True
        
        # Verify removal
        status = get_assignee_status(task_id, self.user_ids[0])
        assert status is None
        
        # Others should still exist
        status = get_assignee_status(task_id, self.user_ids[1])
        assert status == 'pending'
    
    def test_task_status_updates_in_database(self):
        """Test that task status is updated in tasks table."""
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Test task",
            group_id=self.group_id,
            admin_id=self.admin_id,
            assigned_to_list=self.user_ids,
            title="Test Title"
        )
        
        # Initial status should be pending
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        
        # One user starts working
        update_assignee_status(task_id, self.user_ids[0], 'in_progress')
        
        # Task status should be updated
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # All users complete
        update_assignee_status(task_id, self.user_ids[1], 'completed')
        update_assignee_status(task_id, self.user_ids[2], 'completed')
        update_assignee_status(task_id, self.user_ids[0], 'completed')
        
        # Task status should be completed
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'


class TestAssigneeStatusWorkflow:
    """Test real-world workflows with assignee statuses."""
    
    def setup_method(self):
        """Setup test database."""
        # Initialize database
        init_db()
        
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Create test group
        self.group_id = create_group("Dev Team", "dev_team")
        
        # Create team members
        self.alice_id = 1001
        add_user(self.alice_id, "Alice", "alice")
        add_user_to_group(self.alice_id, self.group_id)
        
        self.bob_id = 1002
        add_user(self.bob_id, "Bob", "bob")
        add_user_to_group(self.bob_id, self.group_id)
        
        self.charlie_id = 1003
        add_user(self.charlie_id, "Charlie", "charlie")
        add_user_to_group(self.charlie_id, self.group_id)
        
        # Create project manager
        self.pm_id = 2001
        add_user(self.pm_id, "PM", "pm")
        add_user_to_group(self.pm_id, self.group_id)
    
    def teardown_method(self):
        """Cleanup."""
        self.conn.close()
    
    def test_workflow_team_task_completion(self):
        """Test workflow: Create task, assign to team, track progress to completion."""
        # 1. PM creates task for the team
        task_id = create_task(
            date="2025-12-20",
            time="14:00",
            description="Implement new feature",
            group_id=self.group_id,
            admin_id=self.pm_id,
            assigned_to_list=[self.alice_id, self.bob_id, self.charlie_id],
            title="New Feature Implementation"
        )
        
        assert task_id is not None
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        
        # 2. Alice starts working
        update_assignee_status(task_id, self.alice_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # 3. Bob starts working
        update_assignee_status(task_id, self.bob_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # 4. Alice completes her part
        update_assignee_status(task_id, self.alice_id, 'completed')
        task = get_task_by_id(task_id)
        # Task still in progress (Bob and Charlie not done)
        assert task['status'] == 'in_progress'
        
        # 5. Bob completes his part
        update_assignee_status(task_id, self.bob_id, 'completed')
        task = get_task_by_id(task_id)
        # Task still pending (Charlie hasn't started)
        assert task['status'] == 'pending'
        
        # 6. Charlie starts and completes
        update_assignee_status(task_id, self.charlie_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        update_assignee_status(task_id, self.charlie_id, 'completed')
        task = get_task_by_id(task_id)
        # All done!
        assert task['status'] == 'completed'
        
        # Verify all statuses
        statuses = get_task_assignee_statuses(task_id)
        assert statuses[self.alice_id] == 'completed'
        assert statuses[self.bob_id] == 'completed'
        assert statuses[self.charlie_id] == 'completed'
    
    def test_workflow_partial_cancellation(self):
        """Test workflow: Some team members cancel their part."""
        task_id = create_task(
            date="2025-12-20",
            time="14:00",
            description="Research task",
            group_id=self.group_id,
            admin_id=self.pm_id,
            assigned_to_list=[self.alice_id, self.bob_id],
            title="Research"
        )
        
        # Alice completes
        update_assignee_status(task_id, self.alice_id, 'completed')
        
        # Bob cancels
        update_assignee_status(task_id, self.bob_id, 'cancelled')
        
        # Task should be pending (Alice completed, Bob cancelled, neither all-completed nor all-cancelled)
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
    
    def test_workflow_assignee_reassignment(self):
        """Test workflow: Remove and re-add assignee."""
        task_id = create_task(
            date="2025-12-20",
            time="14:00",
            description="Dev task",
            group_id=self.group_id,
            admin_id=self.pm_id,
            assigned_to_list=[self.alice_id, self.bob_id],
            title="Development"
        )
        
        # Alice starts working
        update_assignee_status(task_id, self.alice_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Alice gets reassigned (removed)
        remove_task_assignee(task_id, self.alice_id)
        
        # Now only Bob is assigned and pending
        task = get_task_by_id(task_id)
        # Bob is still pending
        assert task['status'] == 'pending'
        
        # Add Charlie instead
        add_task_assignees(task_id, [self.charlie_id], initial_status='pending')
        
        # Task still pending (Bob and Charlie both pending)
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        
        # Now Bob and Charlie complete
        update_assignee_status(task_id, self.bob_id, 'completed')
        update_assignee_status(task_id, self.charlie_id, 'completed')
        
        # Task completed
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
