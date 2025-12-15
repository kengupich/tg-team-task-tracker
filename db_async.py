"""
Async wrapper for database operations.
Wraps synchronous DB calls in asyncio.to_thread() to prevent blocking event loop.
Used by async handlers in bot.py and webhook mode.
"""
import asyncio
import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def async_db_operation(func: Callable) -> Callable:
    """
    Decorator to wrap synchronous database operations in asyncio.to_thread().
    Prevents blocking the event loop during webhook processing.
    
    Usage:
        @async_db_operation
        def get_user(user_id):
            return database.get_user_by_id(user_id)
        
        # In async handler:
        user = await get_user(user_id)
    """
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation {func.__name__} failed: {e}")
            raise
    
    return async_wrapper


# ============================================================================
# Async wrappers for critical database operations
# ============================================================================

async def async_get_user_groups(user_id: int) -> list:
    """Non-blocking version of get_user_groups()."""
    import database
    return await asyncio.to_thread(database.get_user_groups, user_id)


async def async_get_group_tasks(group_id: int) -> list:
    """Non-blocking version of get_group_tasks()."""
    import database
    return await asyncio.to_thread(database.get_group_tasks, group_id)


async def async_get_user_tasks(user_id: int) -> list:
    """Non-blocking version of get_user_tasks()."""
    import database
    return await asyncio.to_thread(database.get_user_tasks, user_id)


async def async_get_task_by_id(task_id: int) -> dict:
    """Non-blocking version of get_task_by_id()."""
    import database
    return await asyncio.to_thread(database.get_task_by_id, task_id)


async def async_get_group_users(group_id: int) -> list:
    """Non-blocking version of get_group_users()."""
    import database
    return await asyncio.to_thread(database.get_group_users, group_id)


async def async_get_all_groups() -> list:
    """Non-blocking version of get_all_groups()."""
    import database
    return await asyncio.to_thread(database.get_all_groups)


async def async_get_user_by_id(user_id: int) -> dict:
    """Non-blocking version of get_user_by_id()."""
    import database
    return await asyncio.to_thread(database.get_user_by_id, user_id)


async def async_get_group(group_id: int) -> dict:
    """Non-blocking version of get_group()."""
    import database
    return await asyncio.to_thread(database.get_group, group_id)


async def async_get_task_media(task_id: int) -> list:
    """Non-blocking version of get_task_media()."""
    import database
    return await asyncio.to_thread(database.get_task_media, task_id)


async def async_get_multiple_groups_tasks(group_ids: list) -> list:
    """Non-blocking version of get_multiple_groups_tasks()."""
    import database
    return await asyncio.to_thread(database.get_multiple_groups_tasks, group_ids)


async def async_get_admin_groups(admin_id: int) -> list:
    """Non-blocking version of get_admin_groups()."""
    import database
    return await asyncio.to_thread(database.get_admin_groups, admin_id)


async def async_get_group_admins(group_id: int) -> list:
    """Non-blocking version of get_group_admins()."""
    import database
    return await asyncio.to_thread(database.get_group_admins, group_id)


# ============================================================================
# Async wrappers for write operations
# ============================================================================

async def async_add_user(user_id: int, name: str, username: str = None) -> bool:
    """Non-blocking version of add_user()."""
    import database
    return await asyncio.to_thread(database.add_user, user_id, name, username)


async def async_create_task(title: str, date: str, time: str, description: str, 
                           group_id: int, assigned_to_list: str, created_by: int) -> int:
    """Non-blocking version of create_task()."""
    import database
    return await asyncio.to_thread(
        database.create_task, title, date, time, description, group_id, assigned_to_list, created_by
    )


async def async_update_task_status(task_id: int, new_status: str) -> bool:
    """Non-blocking version of update_task_status()."""
    import database
    return await asyncio.to_thread(database.update_task_status, task_id, new_status)


async def async_update_task_field(task_id: int, field_name: str, value: Any) -> bool:
    """Non-blocking version of update_task_field()."""
    import database
    return await asyncio.to_thread(database.update_task_field, task_id, field_name, value)


async def async_delete_task(task_id: int) -> bool:
    """Non-blocking version of delete_task()."""
    import database
    return await asyncio.to_thread(database.delete_task, task_id)


async def async_create_group(name: str, admin_id: int) -> int:
    """Non-blocking version of create_group()."""
    import database
    return await asyncio.to_thread(database.create_group, name, admin_id)


async def async_rename_group(group_id: int, new_name: str) -> bool:
    """Non-blocking version of rename_group()."""
    import database
    return await asyncio.to_thread(database.rename_group, group_id, new_name)


async def async_delete_group(group_id: int) -> bool:
    """Non-blocking version of delete_group()."""
    import database
    return await asyncio.to_thread(database.delete_group, group_id)


async def async_add_user_to_group(user_id: int, group_id: int) -> bool:
    """Non-blocking version of add_user_to_group()."""
    import database
    return await asyncio.to_thread(database.add_user_to_group, user_id, group_id)


async def async_remove_user_from_group(user_id: int, group_id: int) -> bool:
    """Non-blocking version of remove_user_from_group()."""
    import database
    return await asyncio.to_thread(database.remove_user_from_group, user_id, group_id)


async def async_update_assignee_status(task_id: int, user_id: int, new_status: str) -> bool:
    """Non-blocking version of update_assignee_status()."""
    import database
    return await asyncio.to_thread(database.update_assignee_status, task_id, user_id, new_status)
