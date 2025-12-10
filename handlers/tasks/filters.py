"""Task filtering and viewing handlers."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_all_groups, get_group, get_group_tasks, get_user_tasks,
    get_admin_groups, get_user_by_id, get_group_users
)
from utils.permissions import is_super_admin, is_group_admin

logger = logging.getLogger(__name__)


async def view_tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show unified tasks menu with filters based on user role."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    keyboard = []
    
    # Common filters for all users
    keyboard.append([InlineKeyboardButton("📤 Доручив", callback_data="filter_tasks_created")])
    keyboard.append([InlineKeyboardButton("📥 Виконую", callback_data="filter_tasks_assigned")])
    
    # Admin-specific filters
    if is_group_admin(user_id):
        admin_groups = get_admin_groups(user_id)
        
        if len(admin_groups) > 1:
            # Multiple groups - show selection
            keyboard.append([InlineKeyboardButton("📂 Задачі групи", callback_data="filter_tasks_select_group")])
        elif len(admin_groups) == 1:
            # Single group - direct access
            keyboard.append([InlineKeyboardButton(
                f"📂 Задачі групи: {admin_groups[0]['name']}", 
                callback_data=f"filter_tasks_group_{admin_groups[0]['group_id']}"
            )])
    
    # Super admin filter
    if is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("🌐 Усі задачі", callback_data="filter_tasks_all")])
        keyboard.append([InlineKeyboardButton("📂 Задачі за групами", callback_data="filter_tasks_select_group")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start_menu"),InlineKeyboardButton("🆕 Створити задачу", callback_data="create_task")],)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📋 Задачі\n\nОберіть фільтр:",
        reply_markup=reply_markup
    )


async def filter_tasks_created(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks created by user (постановник)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    from database import get_tasks_created_by_user
    tasks = get_tasks_created_by_user(user_id)
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")]]
        await query.edit_message_text(
            "📤 Доручив\n\nНемає задач, які ви доручили.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for task in tasks[:20]:
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(task['status'], '📌')
        
        desc = task['description'][:40] + '...' if len(task['description']) > 40 else task['description']
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {desc} ({task['date']})",
                callback_data=f"view_task_{task['task_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    await query.edit_message_text(
        f"📤 Доручив ({len(tasks)}):\n\nОберіть задачу для перегляду:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_tasks_assigned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks assigned to user (виконавець)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")]]
        await query.edit_message_text(
            "📥 Виконую\n\nНемає задач, призначених вам.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for task in tasks[:20]:
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(task['status'], '📌')
        
        desc = task['description'][:40] + '...' if len(task['description']) > 40 else task['description']
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {desc} ({task['date']})",
                callback_data=f"view_task_{task['task_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    await query.edit_message_text(
        f"📥 Виконую ({len(tasks)}):\n\nОберіть задачу для перегляду:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_tasks_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show group selection for filtering tasks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Get groups based on user role
    if is_super_admin(user_id):
        groups = get_all_groups()
    else:
        groups = get_admin_groups(user_id)
    
    if not groups:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")]]
        await query.edit_message_text(
            "Немає доступних груп.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for group in groups:
        keyboard.append([
            InlineKeyboardButton(
                f"📂 {group['name']}",
                callback_data=f"filter_tasks_group_{group['group_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Оберіть групу:",
        reply_markup=reply_markup
    )


async def filter_tasks_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show worker selection menu for a specific group."""
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split("_")[-1])
    
    group = get_group(group_id)
    group_name = group['name'] if group else "Невідомо"
    
    # Get users in this group
    users = get_group_users(group_id)
    
    if not users:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="filter_tasks_select_group")]]
        await query.edit_message_text(
            f"📂 {group_name}\n\nНемає працівників у цій групі.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Build keyboard with "All tasks" button and individual workers
    keyboard = []
    
    # Add "All tasks" button
    tasks = get_group_tasks(group_id)
    keyboard.append([InlineKeyboardButton(
        f"📋 Усі задачі ({len(tasks)})",
        callback_data=f"filter_group_all_tasks_{group_id}"
    )])
    
    # Add separator
    keyboard.append([InlineKeyboardButton("👥 Фільтр по виконавцю:", callback_data="ignore")])
    
    # Add worker buttons
    for user in users:
        user_id = user['user_id']
        user_name = user.get('name') or user.get('username', 'Невідомо')
        
        # Count tasks for this user in this group
        user_tasks = get_user_tasks(user_id)
        # Filter to only tasks in this group
        group_tasks_count = len([t for t in user_tasks if t.get('group_id') == group_id])
        
        keyboard.append([InlineKeyboardButton(
            f"👤 {user_name} ({group_tasks_count})",
            callback_data=f"filter_tasks_assignee_{group_id}_{user_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="filter_tasks_select_group")])
    
    await query.edit_message_text(
        f"📂 {group_name}\n\nОберіть фільтр:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_group_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all tasks in a specific group."""
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split("_")[-1])
    
    tasks = get_group_tasks(group_id)
    group = get_group(group_id)
    group_name = group['name'] if group else "Невідомо"
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")]]
        await query.edit_message_text(
            f"📂 {group_name}\n\nНемає задач у цій групі.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for task in tasks[:20]:
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(task['status'], '📌')
        
        desc = task['description'][:40] + '...' if len(task['description']) > 40 else task['description']
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {desc} ({task['date']})",
                callback_data=f"view_task_{task['task_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")])
    await query.edit_message_text(
        f"📂 {group_name} - Усі задачі ({len(tasks)}):\n\nОберіть задачу для перегляду:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_tasks_by_assignee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks for a specific assignee within a group."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: filter_tasks_assignee_{group_id}_{user_id}
    parts = query.data.split("_")
    group_id = int(parts[-2])
    assignee_id = int(parts[-1])
    
    # Get all tasks for this user
    all_user_tasks = get_user_tasks(assignee_id)
    
    # Filter to only tasks in this group
    tasks = [t for t in all_user_tasks if t.get('group_id') == group_id]
    
    group = get_group(group_id)
    group_name = group['name'] if group else "Невідомо"
    
    assignee = get_user_by_id(assignee_id)
    assignee_name = assignee.get('name') or assignee.get('username', 'Невідомо') if assignee else "Невідомо"
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")]]
        await query.edit_message_text(
            f"📂 {group_name}\n👤 {assignee_name}\n\nНемає задач для цього виконавця.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = []
    for task in tasks[:20]:
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(task['status'], '📌')
        
        desc = task['description'][:40] + '...' if len(task['description']) > 40 else task['description']
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {desc} ({task['date']})",
                callback_data=f"view_task_{task['task_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")])
    await query.edit_message_text(
        f"📂 {group_name}\n👤 {assignee_name} ({len(tasks)}):\n\nОберіть задачу для перегляду:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_tasks_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all tasks (super admin only)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Security check
    if not is_super_admin(user_id):
        await query.answer("У вас немає доступу до цієї функції", show_alert=True)
        return
    
    from database import get_all_tasks
    tasks = get_all_tasks()
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")]]
        await query.edit_message_text(
            "🌐 Усі задачі\n\nНемає задач у системі.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Group by status for statistics
    tasks_by_status = {
        'pending': [],
        'in_progress': [],
        'completed': []
    }
    
    for task in tasks:
        status = task.get('status', 'pending')
        if status in tasks_by_status:
            tasks_by_status[status].append(task)
    
    message_text = f"🌐 Усі задачі ({len(tasks)}):\n\n"
    message_text += f"⏳ Очікують: {len(tasks_by_status['pending'])}\n"
    message_text += f"🔄 В роботі: {len(tasks_by_status['in_progress'])}\n"
    message_text += f"✅ Завершені: {len(tasks_by_status['completed'])}\n\n"
    message_text += "Оберіть задачу для перегляду:"
    
    keyboard = []
    for task in tasks[:20]:
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(task['status'], '📌')
        
        desc = task['description'][:40] + '...' if len(task['description']) > 40 else task['description']
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {desc} ({task['date']})",
                callback_data=f"view_task_{task['task_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
