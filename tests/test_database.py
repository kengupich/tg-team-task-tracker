"""Tests for database.py - Core database operations."""
import pytest
from database import (
    add_user, get_user_by_id, get_all_users,
    ban_user, unban_user, delete_user,
    create_group, get_group, get_all_groups,
    add_user_to_group, remove_user_from_group, get_user_groups,
    has_user_group, get_users_without_group,
    cancel_user_tasks, create_task,
)


class TestUserManagement:
    """Test user CRUD operations."""
    
    def test_add_user(self, test_db):
        """Test adding a new user."""
        result = add_user(100001, "Test User")
        assert result is True
        
        user = get_user_by_id(100001)
        assert user is not None
        assert user['name'] == "Test User"
        assert user['banned'] == 0
    
    def test_add_duplicate_user(self, test_db):
        """Test adding duplicate user fails."""
        add_user(100001, "Test User")
        result = add_user(100001, "Duplicate")
        assert result is False
    
    def test_get_user_by_id(self, test_db):
        """Test retrieving user by ID."""
        add_user(100001, "Test User")
        user = get_user_by_id(100001)
        
        assert user is not None
        assert user['user_id'] == 100001
        assert user['name'] == "Test User"
        assert 'banned' in user
    
    def test_get_nonexistent_user(self, test_db):
        """Test retrieving non-existent user returns None."""
        user = get_user_by_id(999999)
        assert user is None
    
    def test_get_all_users(self, test_db):
        """Test retrieving all users."""
        add_user(100001, "User 1")
        add_user(100002, "User 2")
        
        users = get_all_users()
        assert len(users) == 2
        assert all('user_id' in u for u in users)
        assert all('name' in u for u in users)


class TestUserBanningAndDeletion:
    """Test user banning and deletion."""
    
    def test_ban_user(self, test_db):
        """Test banning a user."""
        add_user(100001, "Test User")
        result = ban_user(100001)
        assert result is True
        
        user = get_user_by_id(100001)
        assert user['banned'] == 1
    
    def test_unban_user(self, test_db):
        """Test unbanning a user."""
        add_user(100001, "Test User")
        ban_user(100001)
        result = unban_user(100001)
        assert result is True
        
        user = get_user_by_id(100001)
        assert user['banned'] == 0
    
    def test_delete_user_hides_from_list(self, test_db):
        """Test deleted users don't appear in get_all_users."""
        add_user(100001, "User 1")
        add_user(100002, "User 2")
        
        delete_user(100001)
        
        users = get_all_users()
        user_ids = [u['user_id'] for u in users]
        assert 100001 not in user_ids
        assert 100002 in user_ids
    
    def test_delete_user_sets_banned_and_deleted(self, test_db):
        """Test delete_user sets both banned and deleted flags."""
        add_user(100001, "Test User")
        result = delete_user(100001)
        assert result is True
        
        # User should still exist in DB but not in list
        user = get_user_by_id(100001)
        assert user is not None
        assert user['banned'] == 1


class TestGroupManagement:
    """Test group CRUD operations."""
    
    def test_create_group(self, test_db):
        """Test creating a new group."""
        group_id = create_group("Test Group")
        assert group_id is not None
        
        group = get_group(group_id)
        assert group is not None
        assert group['name'] == "Test Group"
    
    def test_get_all_groups(self, test_db):
        """Test retrieving all groups."""
        create_group("Group 1")
        create_group("Group 2")
        
        groups = get_all_groups()
        assert len(groups) >= 2
        group_names = [g['name'] for g in groups]
        assert "Group 1" in group_names
        assert "Group 2" in group_names


class TestMultiGroupMembership:
    """Test many-to-many user-group relationships."""
    
    def test_add_user_to_group(self, test_db):
        """Test adding user to a group."""
        add_user(100001, "Test User")
        group_id = create_group("Test Group")
        
        result = add_user_to_group(100001, group_id)
        assert result is True
        
        user_groups = get_user_groups(100001)
        assert len(user_groups) == 1
        assert user_groups[0]['group_id'] == group_id
    
    def test_add_user_to_multiple_groups(self, test_db):
        """Test adding user to multiple groups."""
        add_user(100001, "Test User")
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        
        add_user_to_group(100001, group1)
        add_user_to_group(100001, group2)
        
        user_groups = get_user_groups(100001)
        assert len(user_groups) == 2
        group_ids = [g['group_id'] for g in user_groups]
        assert group1 in group_ids
        assert group2 in group_ids
    
    def test_remove_user_from_group(self, test_db):
        """Test removing user from a group."""
        add_user(100001, "Test User")
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        
        add_user_to_group(100001, group1)
        add_user_to_group(100001, group2)
        
        result = remove_user_from_group(100001, group1)
        assert result is True
        
        user_groups = get_user_groups(100001)
        assert len(user_groups) == 1
        assert user_groups[0]['group_id'] == group2
    
    def test_has_user_group(self, test_db):
        """Test checking if user has any group."""
        add_user(100001, "Test User")
        group_id = create_group("Test Group")
        
        assert has_user_group(100001) is False
        
        add_user_to_group(100001, group_id)
        assert has_user_group(100001) is True
    
    def test_get_users_without_group(self, test_db):
        """Test getting users without any group."""
        add_user(100001, "User With Group")
        add_user(100002, "User Without Group")
        group_id = create_group("Test Group")
        
        add_user_to_group(100001, group_id)
        
        users_without = get_users_without_group()
        user_ids = [u['user_id'] for u in users_without]
        
        assert 100001 not in user_ids
        assert 100002 in user_ids


class TestTaskCancellation:
    """Test task cancellation when user is banned/deleted."""
    
    def test_cancel_user_tasks_as_creator(self, test_db):
        """Test cancelling tasks where user is creator."""
        add_user(100001, "Creator")
        add_user(100002, "Assignee")
        group_id = create_group("Test Group")
        
        # Create task with user as creator
        task_id = create_task("2025-12-10", "10:00", "Test Task", group_id, 100001, [100002])
        
        # Cancel user's tasks
        result = cancel_user_tasks(100001)
        
        assert result['cancelled'] == 1
        assert result['updated'] == 0
    
    def test_cancel_user_tasks_as_sole_assignee(self, test_db):
        """Test cancelling tasks where user is sole assignee."""
        add_user(100001, "Creator")
        add_user(100002, "Assignee")
        group_id = create_group("Test Group")
        
        # Create task with user as sole assignee
        task_id = create_task("2025-12-10", "10:00", "Test Task", group_id, 100001, [100002])
        
        # Cancel assignee's tasks
        result = cancel_user_tasks(100002)
        
        assert result['cancelled'] == 1
        assert result['updated'] == 0
    
    def test_remove_user_from_multi_assignee_task(self, test_db):
        """Test removing user from task with multiple assignees."""
        add_user(100001, "Creator")
        add_user(100002, "Assignee 1")
        add_user(100003, "Assignee 2")
        group_id = create_group("Test Group")
        
        # Create task with multiple assignees
        task_id = create_task("2025-12-10", "10:00", "Test Task", group_id, 100001, [100002, 100003])
        
        # Cancel one assignee's tasks
        result = cancel_user_tasks(100002)
        
        # Task should be updated (removed from list), not cancelled
        assert result['cancelled'] == 0
        assert result['updated'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
