"""
Integration tests for complete task workflows.

Tests realistic user scenarios from task creation to completion,
including multiple users interacting with the same tasks.
"""
import pytest
import json
from database import (
    create_task, get_task_by_id, get_group_tasks,
    update_task_field, delete_task,
    add_user, create_group, add_user_to_group,
    update_assignee_status, get_task_assignee_statuses,
    get_assignee_status, calculate_task_status
)


class TestCompleteTaskWorkflow:
    """Test complete workflow from creation to completion."""
    
    def test_full_task_lifecycle(self, test_db):
        """
        Test complete task lifecycle:
        1. Manager creates task
        2. Assigns to multiple developers
        3. Developers work on it (change statuses)
        4. Task gets completed
        5. Manager reviews
        """
        # Setup team
        manager_id = 300001
        dev1_id = 300002
        dev2_id = 300003
        dev3_id = 300004
        
        add_user(manager_id, "Sarah Manager")
        add_user(dev1_id, "John Developer")
        add_user(dev2_id, "Alice Developer")
        add_user(dev3_id, "Bob Tester")
        
        group_id = create_group("Backend Team")
        add_user_to_group(dev1_id, group_id)
        add_user_to_group(dev2_id, group_id)
        add_user_to_group(dev3_id, group_id)
        
        # Step 1: Manager creates task
        task_id = create_task(
            date="2025-12-30",
            time="18:00",
            description="Implement REST API endpoints for user management: "
                       "GET /users, POST /users, PUT /users/:id, DELETE /users/:id. "
                       "Include authentication, validation, and tests.",
            group_id=group_id,
            admin_id=manager_id,
            assigned_to_list=[dev1_id, dev2_id, dev3_id],
            title="User Management API"
        )
        
        assert task_id is not None
        
        # Verify initial state
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        assert task['created_by'] == manager_id
        
        statuses = get_task_assignee_statuses(task_id)
        assert len(statuses) == 3
        assert all(s == 'pending' for s in statuses.values())
        
        # Step 2: John starts working
        update_assignee_status(task_id, dev1_id, 'in_progress')
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        assert get_assignee_status(task_id, dev1_id) == 'in_progress'
        assert get_assignee_status(task_id, dev2_id) == 'pending'
        
        # Step 3: Alice also starts working
        update_assignee_status(task_id, dev2_id, 'in_progress')
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Step 4: John completes his part
        update_assignee_status(task_id, dev1_id, 'completed')
        
        # Task still in progress (Alice and Bob not done)
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Step 5: Alice completes her part
        update_assignee_status(task_id, dev2_id, 'completed')
        
        # Task back to pending (Bob hasn't started)
        task = get_task_by_id(task_id)
        assert task['status'] == 'pending'
        
        # Step 6: Bob starts testing
        update_assignee_status(task_id, dev3_id, 'in_progress')
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # Step 7: Bob completes testing
        update_assignee_status(task_id, dev3_id, 'completed')
        
        # All done! Task completed
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'
        
        # Verify final state
        statuses = get_task_assignee_statuses(task_id)
        assert statuses[dev1_id] == 'completed'
        assert statuses[dev2_id] == 'completed'
        assert statuses[dev3_id] == 'completed'


class TestMultipleTasksWorkflow:
    """Test managing multiple tasks simultaneously."""
    
    def test_developer_works_on_multiple_tasks(self, test_db):
        """Test developer assigned to multiple tasks with different statuses."""
        manager_id = 300001
        dev_id = 300002
        
        add_user(manager_id, "Manager")
        add_user(dev_id, "Developer")
        
        group_id = create_group("Development")
        add_user_to_group(dev_id, group_id)
        
        # Create 3 tasks for the same developer
        task1_id = create_task(
            date="2025-12-25", time="10:00",
            description="Task 1: Login page",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev_id], title="Login Page"
        )
        
        task2_id = create_task(
            date="2025-12-26", time="12:00",
            description="Task 2: Dashboard",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev_id], title="Dashboard"
        )
        
        task3_id = create_task(
            date="2025-12-27", time="14:00",
            description="Task 3: Settings page",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev_id], title="Settings"
        )
        
        # Developer works on tasks in sequence
        # Start task 1
        update_assignee_status(task1_id, dev_id, 'in_progress')
        assert get_task_by_id(task1_id)['status'] == 'in_progress'
        assert get_task_by_id(task2_id)['status'] == 'pending'
        assert get_task_by_id(task3_id)['status'] == 'pending'
        
        # Complete task 1, start task 2
        update_assignee_status(task1_id, dev_id, 'completed')
        update_assignee_status(task2_id, dev_id, 'in_progress')
        
        assert get_task_by_id(task1_id)['status'] == 'completed'
        assert get_task_by_id(task2_id)['status'] == 'in_progress'
        assert get_task_by_id(task3_id)['status'] == 'pending'
        
        # Complete task 2, start task 3
        update_assignee_status(task2_id, dev_id, 'completed')
        update_assignee_status(task3_id, dev_id, 'in_progress')
        
        assert get_task_by_id(task1_id)['status'] == 'completed'
        assert get_task_by_id(task2_id)['status'] == 'completed'
        assert get_task_by_id(task3_id)['status'] == 'in_progress'


class TestTaskReassignmentWorkflow:
    """Test reassigning tasks and status preservation."""
    
    def test_partial_team_change_during_work(self, test_db):
        """Test what happens when team composition changes mid-task."""
        manager_id = 300001
        dev1_id = 300002
        dev2_id = 300003
        dev3_id = 300004  # New person joining
        
        add_user(manager_id, "Manager")
        add_user(dev1_id, "Original Dev 1")
        add_user(dev2_id, "Original Dev 2")
        add_user(dev3_id, "New Dev 3")
        
        group_id = create_group("Team")
        
        # Create task with 2 developers
        task_id = create_task(
            date="2025-12-28", time="15:00",
            description="Complex feature requiring multiple people",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev1_id, dev2_id],
            title="Complex Feature"
        )
        
        # Both start working
        update_assignee_status(task_id, dev1_id, 'in_progress')
        update_assignee_status(task_id, dev2_id, 'in_progress')
        
        assert get_task_by_id(task_id)['status'] == 'in_progress'
        
        # Dev1 completes their part
        update_assignee_status(task_id, dev1_id, 'completed')
        
        # Task still in progress (Dev2 working)
        assert get_task_by_id(task_id)['status'] == 'in_progress'
        
        # Dev2 also completes
        update_assignee_status(task_id, dev2_id, 'completed')
        
        # Task should be completed
        assert get_task_by_id(task_id)['status'] == 'completed'


class TestTaskEditingDuringWork:
    """Test editing task details while work is in progress."""
    
    def test_edit_task_details_without_affecting_status(self, test_db):
        """Test editing task title/description doesn't affect assignee statuses."""
        manager_id = 300001
        dev_id = 300002
        
        add_user(manager_id, "Manager")
        add_user(dev_id, "Developer")
        
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2025-12-29", time="10:00",
            description="Original description",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev_id],
            title="Original Title"
        )
        
        # Developer starts working
        update_assignee_status(task_id, dev_id, 'in_progress')
        
        assert get_task_by_id(task_id)['status'] == 'in_progress'
        assert get_assignee_status(task_id, dev_id) == 'in_progress'
        
        # Manager updates task details
        update_task_field(task_id, 'title', 'Updated Title')
        update_task_field(task_id, 'description', 'Updated description with more details')
        update_task_field(task_id, 'date', '2025-12-30')
        
        # Verify task updated but status preserved
        task = get_task_by_id(task_id)
        assert task['title'] == 'Updated Title'
        assert task['description'] == 'Updated description with more details'
        assert task['date'] == '2025-12-30'
        assert task['status'] == 'in_progress'
        
        # Developer status also preserved
        assert get_assignee_status(task_id, dev_id) == 'in_progress'
        
        # Developer completes
        update_assignee_status(task_id, dev_id, 'completed')
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'


class TestConcurrentStatusChanges:
    """Test multiple assignees changing status at similar times."""
    
    def test_simultaneous_status_changes(self, test_db):
        """Test multiple assignees changing status in quick succession."""
        manager_id = 300001
        dev1_id = 300002
        dev2_id = 300003
        dev3_id = 300004
        
        add_user(manager_id, "Manager")
        add_user(dev1_id, "Dev1")
        add_user(dev2_id, "Dev2")
        add_user(dev3_id, "Dev3")
        
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2025-12-30", time="16:00",
            description="Concurrent work task",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev1_id, dev2_id, dev3_id],
            title="Concurrent Task"
        )
        
        # All start at once
        update_assignee_status(task_id, dev1_id, 'in_progress')
        update_assignee_status(task_id, dev2_id, 'in_progress')
        update_assignee_status(task_id, dev3_id, 'in_progress')
        
        task = get_task_by_id(task_id)
        assert task['status'] == 'in_progress'
        
        # All complete at once (rapid fire)
        update_assignee_status(task_id, dev1_id, 'completed')
        update_assignee_status(task_id, dev2_id, 'completed')
        update_assignee_status(task_id, dev3_id, 'completed')
        
        # Verify all completed
        task = get_task_by_id(task_id)
        assert task['status'] == 'completed'
        
        statuses = get_task_assignee_statuses(task_id)
        assert all(s == 'completed' for s in statuses.values())


class TestTaskListingAndFiltering:
    """Test viewing and filtering tasks with various statuses."""
    
    def test_group_tasks_with_mixed_statuses(self, test_db):
        """Test retrieving all group tasks shows correct aggregated statuses."""
        manager_id = 300001
        dev1_id = 300002
        dev2_id = 300003
        
        add_user(manager_id, "Manager")
        add_user(dev1_id, "Dev1")
        add_user(dev2_id, "Dev2")
        
        group_id = create_group("Team")
        
        # Create various tasks
        # Task 1: All pending
        task1 = create_task(
            date="2025-12-25", time="10:00",
            description="Not started", group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev1_id, dev2_id], title="Task 1"
        )
        
        # Task 2: One in progress
        task2 = create_task(
            date="2025-12-26", time="12:00",
            description="Partially started", group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev1_id, dev2_id], title="Task 2"
        )
        update_assignee_status(task2, dev1_id, 'in_progress')
        
        # Task 3: All completed
        task3 = create_task(
            date="2025-12-27", time="14:00",
            description="Finished", group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev1_id], title="Task 3"
        )
        update_assignee_status(task3, dev1_id, 'completed')
        
        # Task 4: Mixed completion
        task4 = create_task(
            date="2025-12-28", time="16:00",
            description="Half done", group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev1_id, dev2_id], title="Task 4"
        )
        update_assignee_status(task4, dev1_id, 'completed')
        # dev2 still pending
        
        # Get all tasks
        all_tasks = get_group_tasks(group_id)
        assert len(all_tasks) >= 4
        
        # Build status map
        status_map = {t['task_id']: t['status'] for t in all_tasks}
        
        # Verify statuses
        assert status_map[task1] == 'pending'  # All pending
        assert status_map[task2] == 'in_progress'  # One in progress
        assert status_map[task3] == 'completed'  # All completed
        assert status_map[task4] == 'pending'  # Mixed: completed + pending = pending
        
        # Verify assignee details for task4
        task4_assignees = get_task_assignee_statuses(task4)
        assert task4_assignees[dev1_id] == 'completed'
        assert task4_assignees[dev2_id] == 'pending'


class TestErrorHandlingInWorkflow:
    """Test error handling in real-world scenarios."""
    
    def test_graceful_handling_of_missing_data(self, test_db):
        """Test system handles missing or invalid data gracefully."""
        manager_id = 300001
        add_user(manager_id, "Manager")
        group_id = create_group("Team")
        
        # Try to get status for non-existent task
        status = get_assignee_status(99999, manager_id)
        assert status is None
        
        # Try to update non-existent task
        result = update_assignee_status(99999, manager_id, 'completed')
        assert result is False
        
        # Get statuses for non-existent task
        statuses = get_task_assignee_statuses(99999)
        assert statuses == {}
        
        # Calculate status for non-existent task
        calc_status = calculate_task_status(99999)
        assert calc_status == 'pending'  # Default
    
    def test_robust_status_calculation(self, test_db):
        """Test status calculation handles all edge cases."""
        manager_id = 300001
        dev_id = 300002
        
        add_user(manager_id, "Manager")
        add_user(dev_id, "Developer")
        
        group_id = create_group("Team")
        
        # Task with no assignees
        task_no_assignees = create_task(
            date="2025-12-31", time="10:00",
            description="No assignees", group_id=group_id, admin_id=manager_id,
            title="Unassigned"
        )
        assert calculate_task_status(task_no_assignees) == 'pending'
        
        # Task with one assignee
        task_one = create_task(
            date="2025-12-31", time="12:00",
            description="One assignee", group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev_id], title="Single"
        )
        update_assignee_status(task_one, dev_id, 'completed')
        assert calculate_task_status(task_one) == 'completed'


class TestBackwardCompatibility:
    """Test backward compatibility with old data structures."""
    
    def test_task_works_with_assigned_to_list(self, test_db):
        """Test tasks still work with assigned_to_list field."""
        manager_id = 300001
        dev_id = 300002
        
        add_user(manager_id, "Manager")
        add_user(dev_id, "Developer")
        
        group_id = create_group("Team")
        
        task_id = create_task(
            date="2026-01-01", time="10:00",
            description="Compatibility test",
            group_id=group_id, admin_id=manager_id,
            assigned_to_list=[dev_id],
            title="Backward Compat"
        )
        
        task = get_task_by_id(task_id)
        
        # Verify assigned_to_list still exists and is valid JSON
        assigned_list = json.loads(task.get('assigned_to_list', '[]'))
        assert dev_id in assigned_list
        
        # Verify task_assignees also populated
        assignee_statuses = get_task_assignee_statuses(task_id)
        assert dev_id in assignee_statuses
        assert assignee_statuses[dev_id] == 'pending'
