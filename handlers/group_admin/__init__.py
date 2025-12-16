"""Group admin handlers - manage users and tasks within their groups."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_group_users, get_admin_groups
from utils.permissions import get_user_group_id

# Import filter handlers to reuse for backwards compatibility
from handlers.tasks.filters import filter_tasks_select_group, filter_tasks_group, filter_tasks_all

logger = logging.getLogger(__name__)


async def admin_view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Redirect to filter_tasks_group for backward compatibility if single group."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Set task view source to admin_view_tasks (for proper back navigation from task details)
    context.user_data['task_view_source'] = 'admin_view_tasks'
    
    admin_groups = get_admin_groups(user_id)
    
    if len(admin_groups) == 1:
        # Single group - show tasks directly by setting temp_group_id and calling filter_tasks_group
        context.user_data['temp_group_id'] = admin_groups[0]['group_id']
        # Just call filter_tasks_group with the same update - it will use temp_group_id
        return await filter_tasks_group(update, context)
    else:
        # Multiple groups or super admin - show selection
        return await filter_tasks_select_group(update, context)


async def super_manage_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Redirect to filter_tasks_all for backward compatibility."""
    # Set task view source to super_manage_tasks (for proper back navigation from task details)
    context.user_data['task_view_source'] = 'super_manage_tasks'
    return await filter_tasks_all(update, context)


async def admin_manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show manage users menu."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    group_id = get_user_group_id(user_id)
    users = get_group_users(group_id)
    
    user_list = f"👥 работников в отделе ({len(users)}):\n\n"
    for u in users:
        user_list += f"• {u['name']}\n"
    
    keyboard = [
        [InlineKeyboardButton("🆕 Добавить работника", callback_data="admin_add_user")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")],
    ]
    
    await query.edit_message_text(user_list, reply_markup=InlineKeyboardMarkup(keyboard))
