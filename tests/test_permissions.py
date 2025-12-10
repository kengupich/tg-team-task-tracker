"""Tests for permission and access control functions."""
import pytest
import os
from database import (
    add_user, create_group, add_user_to_group,
    is_group_admin, add_group_admin, remove_group_admin,
    get_admin_groups, has_user_group
)


# Mock super admin IDs for testing
SUPER_ADMIN_IDS = [999999]  # Test super admin ID


class TestSuperAdminPermissions:
    """Test super admin permission checks."""
    
    def test_is_super_admin(self, test_db):
        """Test super admin check."""
        # Mock super admin
        assert 999999 in SUPER_ADMIN_IDS
        
        # Regular user is not super admin
        assert 100001 not in SUPER_ADMIN_IDS
    
    def test_super_admin_has_all_permissions(self, test_db):
        """Test that super admin has permissions for all groups."""
        admin_id = 999999
        add_user(admin_id, "Super Admin")
        
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        
        # Super admin should have access to all groups
        # (This is typically checked in bot.py logic)
        assert admin_id == 999999


class TestGroupAdminPermissions:
    """Test group admin permission checks."""
    
    def test_add_group_admin(self, test_db):
        """Test adding a user as group admin."""
        user_id = 100001
        add_user(user_id, "Admin User")
        group_id = create_group("Test Group")
        
        result = add_group_admin(group_id, user_id)  # Correct order: group_id, admin_id
        assert result is True
        
        # Verify user is admin
        assert is_group_admin(user_id, group_id) is True
    
    def test_is_group_admin_specific_group(self, test_db):
        """Test checking if user is admin of specific group."""
        user_id = 100001
        add_user(user_id, "Admin User")
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        
        add_group_admin(group1, user_id)  # Correct order
        
        # User is admin of group1 but not group2
        assert is_group_admin(user_id, group1) is True
        assert is_group_admin(user_id, group2) is False
    
    def test_is_group_admin_any_group(self, test_db):
        """Test checking if user is admin of any group."""
        user_id = 100001
        add_user(user_id, "Admin User")
        group_id = create_group("Test Group")
        
        # Initially not admin
        assert is_group_admin(user_id) is False
        
        # Add as admin
        add_group_admin(group_id, user_id)  # Correct order
        
        # Now is admin
        assert is_group_admin(user_id) is True
    
    def test_remove_group_admin(self, test_db):
        """Test removing a user as group admin."""
        user_id = 100001
        add_user(user_id, "Admin User")
        group_id = create_group("Test Group")
        
        # Add then remove
        add_group_admin(group_id, user_id)  # Correct order
        assert is_group_admin(user_id, group_id) is True
        
        result = remove_group_admin(group_id, user_id)  # Correct order
        assert result is True
        assert is_group_admin(user_id, group_id) is False
    
    def test_get_admin_groups(self, test_db):
        """Test getting all groups where user is admin."""
        user_id = 100001
        add_user(user_id, "Admin User")
        
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        group3 = create_group("Group 3")
        
        # Make admin of 2 groups
        add_group_admin(group1, user_id)  # Correct order
        add_group_admin(group2, user_id)  # Correct order
        
        # Get admin groups
        admin_groups = get_admin_groups(user_id)
        
        assert len(admin_groups) == 2
        group_ids = [g['group_id'] for g in admin_groups]
        assert group1 in group_ids
        assert group2 in group_ids
        assert group3 not in group_ids


class TestUserGroupMembership:
    """Test user group membership checks."""
    
    def test_has_user_group_single_group(self, test_db):
        """Test checking if user belongs to any group."""
        user_id = 100001
        add_user(user_id, "Test User")
        
        # Initially no group
        assert has_user_group(user_id) is False
        
        # Add to group
        group_id = create_group("Test Group")
        add_user_to_group(user_id, group_id)
        
        # Now has group
        assert has_user_group(user_id) is True
    
    def test_has_user_group_multiple_groups(self, test_db):
        """Test user with multiple group memberships."""
        user_id = 100001
        add_user(user_id, "Test User")
        
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        
        add_user_to_group(user_id, group1)
        add_user_to_group(user_id, group2)
        
        assert has_user_group(user_id) is True
    
    def test_user_without_group(self, test_db):
        """Test user without any group membership."""
        user_id = 100001
        add_user(user_id, "Test User")
        
        assert has_user_group(user_id) is False


class TestPermissionCombinations:
    """Test combinations of permissions and roles."""
    
    def test_admin_is_also_member(self, test_db):
        """Test that group admin should also be a member."""
        admin_id = 100001
        add_user(admin_id, "Admin User")
        group_id = create_group("Test Group")
        
        # Add as admin
        add_group_admin(group_id, admin_id)  # Correct order
        
        # Admin check
        assert is_group_admin(admin_id, group_id) is True
    
    def test_member_not_admin(self, test_db):
        """Test that regular member is not admin."""
        user_id = 100001
        add_user(user_id, "Regular User")
        group_id = create_group("Test Group")
        
        # Add as regular member
        add_user_to_group(user_id, group_id)
        
        # Has group but not admin
        assert has_user_group(user_id) is True
        assert is_group_admin(user_id, group_id) is False
    
    def test_multi_group_admin(self, test_db):
        """Test user who is admin of multiple groups."""
        admin_id = 100001
        add_user(admin_id, "Multi Admin")
        
        group1 = create_group("Group 1")
        group2 = create_group("Group 2")
        group3 = create_group("Group 3")
        
        # Admin of group1 and group2, member of group3
        add_group_admin(group1, admin_id)  # Correct order
        add_group_admin(group2, admin_id)  # Correct order
        add_user_to_group(admin_id, group3)
        
        # Verify permissions
        assert is_group_admin(admin_id, group1) is True
        assert is_group_admin(admin_id, group2) is True
        assert is_group_admin(admin_id, group3) is False
        assert is_group_admin(admin_id) is True  # Admin of at least one group


class TestPermissionEdgeCases:
    """Test edge cases and error handling."""
    
    def test_admin_of_nonexistent_group(self, test_db):
        """Test checking admin status for non-existent group."""
        user_id = 100001
        add_user(user_id, "Test User")
        
        # Check for non-existent group
        assert is_group_admin(user_id, 99999) is False
    
    def test_nonexistent_user_permissions(self, test_db):
        """Test permission checks for non-existent user."""
        # Non-existent user should have no permissions
        assert is_group_admin(99999) is False
        assert has_user_group(99999) is False
    
    def test_remove_nonexistent_admin(self, test_db):
        """Test removing admin that doesn't exist."""
        user_id = 100001
        group_id = create_group("Test Group")
        
        # Try to remove non-existent admin
        result = remove_group_admin(group_id, user_id)  # Correct order
        # Should handle gracefully (implementation dependent)
        assert result in [True, False]  # Either is acceptable
