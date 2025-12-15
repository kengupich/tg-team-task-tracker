"""
Comprehensive scenario tests for task creation, viewing, and editing with individual assignee statuses.

Tests cover:
- Task creation with title and description
- Multi-assignee task management
- Individual assignee status tracking
- Status aggregation logic
- Task editing and updates
- Task viewing with assignee statuses
"""
import pytest
import json
from database import (
    create_task, get_task_by_id, get_group_tasks,
    update_task_status, update_task_field, delete_task,
    add_user, create_group, add_user_to_group,
    # New assignee status functions
    add_task_assignees, get_task_assignee_statuses,
    get_assignee_status, update_assignee_status,
    calculate_task_status, remove_task_assignee
)


class TestTaskCreationScenarios:
    """Test various task creation scenarios."""
    
    def test_create_task_with_title_and_description(self, test_db):
        """Test creating a task with both title and description."""
        # Setup
        admin_id = 200001
        add_user(admin_id, "Project Manager")
        group_id = create_group("Development Team")
        
        # Create task with title
        task_id = create_task(
            date="2025-12-15",
            time="10:00",
            description="Implement login functionality with JWT tokens and refresh token support",
            group_id=group_id,
            admin_id=admin_id,
            title="User Authentication Feature"
        )
        
        assert task_id is not None
        
        # Verify task
        task = get_task_by_id(task_id)
        assert task['title'] == "User Authentication Feature"
        assert "JWT tokens" in task['description']
        assert task['status'] == "pending"
    
    def test_create_task_multiple_assignees_with_individual_statuses(self, test_db):
        """Test creating task with multiple assignees and verify individual status tracking."""
        # Setup users
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        dev3_id = 200004
        
        add_user(admin_id, "Team Lead")
        add_user(dev1_id, "John Developer")
        add_user(dev2_id, "Mary Developer")
        add_user(dev3_id, "Bob Designer")
        
        group_id = create_group("Product Team")
        add_user_to_group(dev1_id, group_id)
        add_user_to_group(dev2_id, group_id)
        add_user_to_group(dev3_id, group_id)
        
        # Create task with multiple assignees
        task_id = create_task(
            date="2025-12-20",
            time="18:00",
            description="Create landing page with responsive design",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id, dev3_id],
            title="Landing Page Design"
        )
        
        # Verify task creation
        assert task_id is not None
        task = get_task_by_id(task_id)
        assert task is not None
        
        # Verify assigned_to_list
        assigned_list = json.loads(task.get('assigned_to_list', '[]'))
        assert len(assigned_list) == 3
        assert dev1_id in assigned_list
        assert dev2_id in assigned_list
        assert dev3_id in assigned_list
        
        # Verify individual assignee statuses (should all be 'pending' initially)
        assignee_statuses = get_task_assignee_statuses(task_id)
        assert len(assignee_statuses) == 3
        assert assignee_statuses[dev1_id] == 'pending'
        assert assignee_statuses[dev2_id] == 'pending'
        assert assignee_statuses[dev3_id] == 'pending'
        
        # Verify overall task status
        assert task['status'] == 'pending'
    
    def test_create_task_without_assignees(self, test_db):
        """Test creating task without assignees."""
        admin_id = 200001
        add_user(admin_id, "Manager")
        group_id = create_group("Planning")
        
        task_id = create_task(
            date="2025-12-25",
            time="12:00",
            description="Review quarterly reports",
            group_id=group_id,
            admin_id=admin_id,
            title="Quarterly Review"
        )
        
        task = get_task_by_id(task_id)
        assigned_list = json.loads(task.get('assigned_to_list', '[]'))
        assert len(assigned_list) == 0
        
        # No assignees in task_assignees table
        assignee_statuses = get_task_assignee_statuses(task_id)
        assert len(assignee_statuses) == 0


class TestIndividualAssigneeStatusScenarios:
    """Test individual assignee status tracking and aggregation."""
    
    def test_single_assignee_status_change_in_progress(self, test_db):
        """Test one assignee changing status to in_progress."""
        # Setup
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        
        add_user(admin_id, "Lead")
        add_user(dev1_id, "Developer 1")
        add_user(dev2_id, "Developer 2")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-16",
            time="15:00",
            description="Fix authentication bug",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id],
            title="Bug Fix"
        )
        
        # Dev1 starts working (changes to in_progress)
        result = update_assignee_status(task_id, dev1_id, 'in_progress')
        assert result is True
        
        # Verify Dev1 status changed
        dev1_status = get_assignee_status(task_id, dev1_id)
        assert dev1_status == 'in_progress'
        
        # Verify Dev2 still pending
        dev2_status = get_assignee_status(task_id, dev2_id)
        assert dev2_status == 'pending'
        
        # Verify task overall status is in_progress (because at least one is in_progress)
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
    
    def test_multiple_assignees_progress_to_completion(self, test_db):
        """Test scenario where multiple assignees progress through statuses."""
        # Setup
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        dev3_id = 200004
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Alice")
        add_user(dev2_id, "Bob")
        add_user(dev3_id, "Charlie")
        
        group_id = create_group("Dev Team")
        task_id = create_task(
            date="2025-12-18",
            time="17:00",
            description="Implement payment gateway integration",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id, dev3_id],
            title="Payment Gateway"
        )
        
        # Initial state: all pending
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        
        # Step 1: Alice starts working
        update_assignee_status(task_id, dev1_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'  # At least one in_progress
        
        # Step 2: Bob also starts working
        update_assignee_status(task_id, dev2_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'  # Still in_progress
        
        # Step 3: Alice completes her part
        update_assignee_status(task_id, dev1_id, 'completed')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'  # Still in_progress (Bob and Charlie not done)
        
        # Step 4: Bob completes his part
        update_assignee_status(task_id, dev2_id, 'completed')
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'  # Back to pending (Charlie still pending)
        
        # Step 5: Charlie starts and completes
        update_assignee_status(task_id, dev3_id, 'in_progress')
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        update_assignee_status(task_id, dev3_id, 'completed')
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'  # All completed!
        
        # Verify all individual statuses
        statuses = get_task_assignee_statuses(task_id)
        assert statuses[dev1_id] == 'completed'
        assert statuses[dev2_id] == 'completed'
        assert statuses[dev3_id] == 'completed'
    
    def test_status_aggregation_rules(self, test_db):
        """Test all status aggregation rules comprehensively."""
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        dev3_id = 200004
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Dev1")
        add_user(dev2_id, "Dev2")
        add_user(dev3_id, "Dev3")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-19",
            time="14:00",
            description="Test task for aggregation",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id, dev3_id],
            title="Aggregation Test"
        )
        
        # Rule 1: All pending → task pending
        assert calculate_task_status(task_id) == 'pending'
        
        # Rule 2: At least one in_progress → task in_progress
        update_assignee_status(task_id, dev1_id, 'in_progress')
        assert calculate_task_status(task_id) == 'in_progress'
        
        # Rule 3: Mix of completed and pending (no in_progress) → task pending
        update_assignee_status(task_id, dev1_id, 'completed')
        assert calculate_task_status(task_id) == 'pending'
        
        # Rule 4: All completed → task completed
        update_assignee_status(task_id, dev2_id, 'completed')
        update_assignee_status(task_id, dev3_id, 'completed')
        assert calculate_task_status(task_id) == 'completed'
        
        # Rule 5: All cancelled → task cancelled
        update_assignee_status(task_id, dev1_id, 'cancelled')
        update_assignee_status(task_id, dev2_id, 'cancelled')
        update_assignee_status(task_id, dev3_id, 'cancelled')
        assert calculate_task_status(task_id) == 'cancelled'
    
    def test_assignee_status_independent_of_others(self, test_db):
        """Test that changing one assignee's status doesn't affect others."""
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        
        add_user(admin_id, "Lead")
        add_user(dev1_id, "John")
        add_user(dev2_id, "Jane")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-17",
            time="11:00",
            description="Independent status test",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id],
            title="Status Independence"
        )
        
        # Change Dev1 status
        update_assignee_status(task_id, dev1_id, 'in_progress')
        
        # Verify Dev2 unaffected
        dev2_status = get_assignee_status(task_id, dev2_id)
        assert dev2_status == 'pending'
        
        # Change Dev1 to completed
        update_assignee_status(task_id, dev1_id, 'completed')
        
        # Dev2 still pending
        dev2_status = get_assignee_status(task_id, dev2_id)
        assert dev2_status == 'pending'


class TestTaskEditingScenarios:
    """Test task editing operations."""
    
    def test_edit_task_title(self, test_db):
        """Test editing task title."""
        admin_id = 200001
        add_user(admin_id, "Manager")
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2025-12-20",
            time="10:00",
            description="Original description",
            group_id=group_id,
            admin_id=admin_id,
            title="Original Title"
        )
        
        # Edit title
        result = update_task_field(task_id, 'title', 'Updated Title')
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['title'] == 'Updated Title'
        assert task['description'] == "Original description"  # Unchanged
    
    def test_edit_task_description(self, test_db):
        """Test editing task description."""
        admin_id = 200001
        add_user(admin_id, "Manager")
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2025-12-21",
            time="12:00",
            description="Old description",
            group_id=group_id,
            admin_id=admin_id,
            title="Test Task"
        )
        
        # Edit description
        new_desc = "Updated description with more details"
        result = update_task_field(task_id, 'description', new_desc)
        assert result is True
        
        task = get_task_by_id(task_id)
        assert task['description'] == new_desc
        assert task['title'] == "Test Task"  # Unchanged
    
    def test_edit_task_deadline(self, test_db):
        """Test editing task deadline."""
        admin_id = 200001
        add_user(admin_id, "Manager")
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2025-12-22",
            time="14:00",
            description="Test task",
            group_id=group_id,
            admin_id=admin_id,
            title="Deadline Test"
        )
        
        # Edit date
        update_task_field(task_id, 'date', '2025-12-25')
        update_task_field(task_id, 'time', '18:00')
        
        task = get_task_by_id(task_id)
        assert task['date'] == '2025-12-25'
        assert task['time'] == '18:00'
    
    def test_remove_assignee_recalculates_status(self, test_db):
        """Test that removing an assignee recalculates task status."""
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        
        add_user(admin_id, "Lead")
        add_user(dev1_id, "Dev1")
        add_user(dev2_id, "Dev2")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-23",
            time="16:00",
            description="Assignee removal test",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id],
            title="Removal Test"
        )
        
        # Both in progress
        update_assignee_status(task_id, dev1_id, 'in_progress')
        update_assignee_status(task_id, dev2_id, 'in_progress')
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Remove dev1
        result = remove_task_assignee(task_id, dev1_id)
        assert result is True
        
        # Status should still be in_progress (dev2 still working)
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Complete dev2
        update_assignee_status(task_id, dev2_id, 'completed')
        
        # Now task should be completed (only remaining assignee done)
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'


class TestTaskViewingScenarios:
    """Test task viewing and listing scenarios."""
    
    def test_get_task_with_assignee_statuses(self, test_db):
        """Test retrieving task includes correct assignee information."""
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Alice")
        add_user(dev2_id, "Bob")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-24",
            time="10:00",
            description="View test task",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id],
            title="View Test"
        )
        
        # Set different statuses
        update_assignee_status(task_id, dev1_id, 'in_progress')
        update_assignee_status(task_id, dev2_id, 'pending')
        
        # Get task
        task = get_task_by_id(task_id)
        assert task is not None
        
        # Get assignee statuses
        assignee_statuses = get_task_assignee_statuses(task_id)
        assert assignee_statuses[dev1_id] == 'in_progress'
        assert assignee_statuses[dev2_id] == 'pending'
        
        # Overall status should be in_progress
        assert task['status'] == 'in_progress'
    
    def test_list_group_tasks_with_various_statuses(self, test_db):
        """Test listing multiple tasks with different statuses."""
        admin_id = 200001
        dev1_id = 200002
        dev2_id = 200003
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Dev1")
        add_user(dev2_id, "Dev2")
        
        group_id = create_group("Team")
        
        # Create multiple tasks
        task1 = create_task(
            date="2025-12-25", time="10:00",
            description="Task 1", group_id=group_id, admin_id=admin_id,
            assigned_to_list=[dev1_id], title="Pending Task"
        )
        
        task2 = create_task(
            date="2025-12-26", time="12:00",
            description="Task 2", group_id=group_id, admin_id=admin_id,
            assigned_to_list=[dev1_id, dev2_id], title="In Progress Task"
        )
        update_assignee_status(task2, dev1_id, 'in_progress')
        
        task3 = create_task(
            date="2025-12-27", time="14:00",
            description="Task 3", group_id=group_id, admin_id=admin_id,
            assigned_to_list=[dev2_id], title="Completed Task"
        )
        update_assignee_status(task3, dev2_id, 'completed')
        
        # Get all tasks
        tasks = get_group_tasks(group_id)
        assert len(tasks) >= 3
        
        # Verify statuses
        task_statuses = {t['task_id']: t['status'] for t in tasks}
        assert task_statuses[task1] == 'pending'
        assert task_statuses[task2] == 'in_progress'
        assert task_statuses[task3] == 'completed'


class TestTaskDeletionScenarios:
    """Test task deletion with assignees."""
    
    def test_delete_task_removes_assignee_records(self, test_db):
        """Test that deleting a task also removes assignee records."""
        admin_id = 200001
        dev1_id = 200002
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Developer")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-28",
            time="16:00",
            description="Task to delete",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id],
            title="Delete Test"
        )
        
        # Verify assignee exists
        assignee_statuses = get_task_assignee_statuses(task_id)
        assert len(assignee_statuses) == 1
        
        # Delete task
        result = delete_task(task_id)
        assert result is True
        
        # Verify task deleted
        task = get_task_by_id(task_id)
        assert task is None
        
        # Verify assignee records also removed (should return empty)
        assignee_statuses = get_task_assignee_statuses(task_id)
        assert len(assignee_statuses) == 0


class TestEdgeCasesAndValidation:
    """Test edge cases and validation scenarios."""
    
    def test_update_nonexistent_assignee_status(self, test_db):
        """Test updating status for non-existent assignee."""
        admin_id = 200001
        add_user(admin_id, "Manager")
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2025-12-29",
            time="10:00",
            description="Edge case test",
            group_id=group_id,
            admin_id=admin_id,
            title="Edge Case"
        )
        
        # Try to update status for non-assigned user
        result = update_assignee_status(task_id, 999999, 'completed')
        assert result is False
    
    def test_get_status_for_unassigned_user(self, test_db):
        """Test getting status for user not assigned to task."""
        admin_id = 200001
        dev1_id = 200002
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Developer")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-30",
            time="12:00",
            description="Unassigned test",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id],
            title="Unassigned Test"
        )
        
        # Try to get status for different user
        status = get_assignee_status(task_id, 999999)
        assert status is None
    
    def test_invalid_status_value(self, test_db):
        """Test that invalid status values are rejected."""
        admin_id = 200001
        dev1_id = 200002
        
        add_user(admin_id, "Manager")
        add_user(dev1_id, "Developer")
        
        group_id = create_group("Team")
        task_id = create_task(
            date="2025-12-31",
            time="14:00",
            description="Invalid status test",
            group_id=group_id,
            admin_id=admin_id,
            assigned_to_list=[dev1_id],
            title="Invalid Status"
        )
        
        # Try invalid status
        result = update_assignee_status(task_id, dev1_id, 'invalid_status')
        assert result is False
        
        # Verify status unchanged
        status = get_assignee_status(task_id, dev1_id)
        assert status == 'pending'
    
    def test_task_with_no_assignees_has_pending_status(self, test_db):
        """Test that task with no assignees defaults to pending."""
        admin_id = 200001
        add_user(admin_id, "Manager")
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2026-01-01",
            time="16:00",
            description="No assignees task",
            group_id=group_id,
            admin_id=admin_id,
            title="No Assignees"
        )
        
        calculated_status = calculate_task_status(task_id)
        assert calculated_status == 'pending'
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
