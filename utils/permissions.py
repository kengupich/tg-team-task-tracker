"""Permission checking utilities"""
import os
from dotenv import load_dotenv
from database import get_admin_groups, get_task_by_id, get_user_by_id, is_group_admin as db_is_group_admin

# Load environment variables
load_dotenv()

# Parse super admin IDs from environment
SUPER_ADMIN_IDS = [
    int(id.strip()) for id in os.getenv("SUPER_ADMIN_ID", "0").split(",") if id.strip()
]


def is_super_admin(user_id: int) -> bool:
    """Check if user is super admin."""
    return user_id in SUPER_ADMIN_IDS


def is_group_admin(user_id: int, group_id: int = None) -> bool:
    """
    Check if user is a group admin.
    
    Args:
        user_id: Telegram user ID
        group_id: Optional - check if admin of specific group
        
    Returns:
        bool: True if user is admin (of any group or specific group)
    """
    return db_is_group_admin(user_id, group_id)


def get_user_group_id(user_id: int) -> int:
    """
    Get first group ID for a user (if they're admin).
    For backward compatibility - returns first group.
    Use get_admin_groups() to get all groups.
    """
    groups = get_admin_groups(user_id)
    return groups[0]["group_id"] if groups else None


def get_user_group_ids(user_id: int) -> list:
    """Get all group IDs where user is admin."""
    groups = get_admin_groups(user_id)
    return [g["group_id"] for g in groups]


def can_edit_task(user_id: int, task: dict) -> bool:
    """
    Check if user can edit/delete a task.
    
    Rules:
    - Super admin: can edit any task
    - Task creator (постановник): can edit their own tasks
    - Group admin of creator's group: can edit tasks created by users in their group
    - Regular user who is also creator: can edit (covered by creator rule)
    
    Args:
        user_id: ID of user requesting edit
        task: Task dictionary with 'created_by' and 'group_id' fields
        
    Returns:
        True if user can edit/delete, False otherwise
    """
    if not task:
        return False
    
    # Super admin can edit anything
    if is_super_admin(user_id):
        return True
    
    # Task creator can edit their own tasks
    task_creator_id = task.get('created_by')
    if task_creator_id and user_id == task_creator_id:
        return True
    
    # Group admin can edit tasks created by users in their group
    if is_group_admin(user_id):
        admin_group_ids = get_user_group_ids(user_id)
        if admin_group_ids:
            # Get creator's group
            creator = get_user_by_id(task_creator_id)
            if creator and creator.get('group_id') in admin_group_ids:
                return True
    
    return False
