"""
Utility functions for the Team Task Management Telegram Bot.
"""

def is_admin(user_id, admin_ids):
    """
    Check if a user is an admin.
    
    Args:
        user_id (int): Telegram user ID to check
        admin_ids (list): List of admin Telegram user IDs
        
    Returns:
        bool: True if user is an admin, False otherwise
    """
    return user_id in admin_ids
