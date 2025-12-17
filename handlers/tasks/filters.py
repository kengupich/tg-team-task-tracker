"""Task filtering and viewing handlers."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_all_groups, get_group, get_group_tasks, get_user_tasks,
    get_admin_groups, get_user_by_id, get_group_users
)
from utils.permissions import is_super_admin, is_group_admin
from utils.helpers import get_status_emoji, format_task_status, format_task_button

logger = logging.getLogger(__name__)


async def view_tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show unified tasks menu with filters based on user role."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    keyboard = []
    
    # Common filters for all users
    keyboard.append([InlineKeyboardButton("📤 Поручил", callback_data="filter_tasks_created")])
    keyboard.append([InlineKeyboardButton("📥 Выполняю", callback_data="filter_tasks_assigned")])
    keyboard.append([InlineKeyboardButton("📦 Архив задач", callback_data="filter_tasks_archived")])
    
    # Admin-specific filters
    if is_group_admin(user_id):
        admin_groups = get_admin_groups(user_id)
        
        if len(admin_groups) > 1:
            # Multiple groups - show selection
            keyboard.append([InlineKeyboardButton("📂 Задачи группы", callback_data="filter_tasks_select_group")])
        elif len(admin_groups) == 1:
            # Single group - direct access
            keyboard.append([InlineKeyboardButton(
                f"📂 Задачи группы: {admin_groups[0]['name']}", 
                callback_data=f"filter_tasks_group_{admin_groups[0]['group_id']}"
            )])
    
    # Super admin filter
    if is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("🌐 Все задачи", callback_data="filter_tasks_all")])
        keyboard.append([InlineKeyboardButton("📂 Задачи по группам", callback_data="filter_tasks_select_group")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start_menu"),InlineKeyboardButton("🆕 Создать задачу", callback_data="create_task")],)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📋 Задачи\n\nВыберите фильтр:",
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
            "📤 Поручил\n\nНет задач, которые вы поручили.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [format_task_button(task, show_date=False)]
        for task in tasks[:20]
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    await query.edit_message_text(
        f"📤 Поручил ({len(tasks)}):\n\nВыберите задачу для просмотра:",
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
            "📥 Выполняю\n\nНет задач, назначенных вам.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [format_task_button(task)]
        for task in tasks[:20]
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    await query.edit_message_text(
        f"📥 Выполняю ({len(tasks)}):\n\nВыберите задачу для просмотра:",
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
            "Нет доступных групп.",
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
        "Выберите группу:",
        reply_markup=reply_markup
    )


async def filter_tasks_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show worker selection menu for a specific group."""
    query = update.callback_query
    await query.answer()
    
    # Try to get group_id from callback data, or from context if called from admin_view_tasks
    try:
        group_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        # Fallback to temp_group_id if available (called from admin_view_tasks)
        group_id = context.user_data.get('temp_group_id')
        if not group_id:
            await query.edit_message_text("❌ Помилка: група не визначена.")
            return
    
    group = get_group(group_id)
    group_name = group['name'] if group else "Неизвестно"
    
    # Get users in this group
    users = get_group_users(group_id)
    
    if not users:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="filter_tasks_select_group")]]
        await query.edit_message_text(
            f"📂 {group_name}\n\nНет сотрудников в этой группе.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Build keyboard with "All tasks" button and individual workers
    keyboard = []
    
    # Add "All tasks" button
    tasks = get_group_tasks(group_id)
    keyboard.append([InlineKeyboardButton(
        f"📋 Все задачи ({len(tasks)})",
        callback_data=f"filter_group_all_tasks_{group_id}"
    )])
    
    # Add separator
    keyboard.append([InlineKeyboardButton("👥 Фильтр по исполнителю:", callback_data="ignore")])
    
    # Add worker buttons
    for user in users:
        user_id = user['user_id']
        user_name = user.get('name') or user.get('username', 'Неизвестно')
        
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
        f"📂 {group_name}\n\nВыберите фильтр:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_group_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all tasks in a specific group."""
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split("_")[-1])
    
    tasks = get_group_tasks(group_id)
    group = get_group(group_id)
    group_name = group['name'] if group else "Неизвестно"
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")]]
        await query.edit_message_text(
            f"📂 {group_name}\n\nНет задач в этой группе.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [format_task_button(task)]
        for task in tasks[:20]
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")])
    await query.edit_message_text(
        f"📂 {group_name} - Все задачи ({len(tasks)}):\n\nВыберите задачу для просмотра:",
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
    group_name = group['name'] if group else "Неизвестно"
    
    assignee = get_user_by_id(assignee_id)
    assignee_name = assignee.get('name') or assignee.get('username', 'Неизвестно') if assignee else "Неизвестно"
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")]]
        await query.edit_message_text(
            f"📂 {group_name}\n👤 {assignee_name}\n\nНет задач для этого исполнителя.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [format_task_button(task)]
        for task in tasks[:20]
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"filter_tasks_group_{group_id}")])
    await query.edit_message_text(
        f"📂 {group_name}\n👤 {assignee_name} ({len(tasks)}):\n\nВыберите задачу для просмотра:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_tasks_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all tasks (super admin only)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Security check
    if not is_super_admin(user_id):
        await query.answer("У вас нет доступа к этой функции", show_alert=True)
        return
    
    from database import get_all_tasks
    tasks = get_all_tasks()
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")]]
        await query.edit_message_text(
            "🌐 Все задачи\n\nНет задач в системе.",
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
    
    message_text = f"🌐 Все задачи ({len(tasks)}):\n\n"
    message_text += f"⏳ Ожидают: {len(tasks_by_status['pending'])}\n"
    message_text += f"🔄 В работе: {len(tasks_by_status['in_progress'])}\n"
    message_text += f"✅ Завершены: {len(tasks_by_status['completed'])}\n\n"
    message_text += "Выберите задачу для просмотра:"
    
    keyboard = [
        [format_task_button(task)]
        for task in tasks[:20]
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")])
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_tasks_archived(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show archived (completed) tasks menu."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📤 Поручил (архив)", callback_data="filter_archived_created_0")],
        [InlineKeyboardButton("📥 Выполнял (архив)", callback_data="filter_archived_assigned_0")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="view_tasks_menu")]
    ]
    
    await query.edit_message_text(
        "📦 Архив завершенных задач\n\nВыберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_archived_created(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show archived tasks created by user with pagination."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Extract page number from callback data
    page = 0
    if "_" in query.data:
        try:
            page = int(query.data.split("_")[-1])
        except:
            page = 0
    
    from database import get_archived_tasks_created_by_user
    tasks = get_archived_tasks_created_by_user(user_id)
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="filter_tasks_archived")]]
        await query.edit_message_text(
            "📤 Поручил (архив)\n\nНет завершенных задач.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Pagination
    page_size = 10
    total_pages = (len(tasks) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_tasks = tasks[start_idx:end_idx]
    
    keyboard = [
        [format_task_button(task)]
        for task in page_tasks
    ]
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"filter_archived_created_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"filter_archived_created_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ К архиву", callback_data="filter_tasks_archived")])
    
    await query.edit_message_text(
        f"📤 Поручил (архив)\nСтраница {page + 1}/{total_pages}, всего: {len(tasks)}\n\nВыберите задачу:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def filter_archived_assigned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show archived tasks assigned to user with pagination."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Extract page number from callback data
    page = 0
    if "_" in query.data:
        try:
            page = int(query.data.split("_")[-1])
        except:
            page = 0
    
    from database import get_user_archived_tasks
    tasks = get_user_archived_tasks(user_id)
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="filter_tasks_archived")]]
        await query.edit_message_text(
            "📥 Выполнял (архив)\n\nНет завершенных задач.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Pagination
    page_size = 10
    total_pages = (len(tasks) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_tasks = tasks[start_idx:end_idx]
    
    keyboard = [
        [format_task_button(task)]
        for task in page_tasks
    ]
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"filter_archived_assigned_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"filter_archived_assigned_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ К архиву", callback_data="filter_tasks_archived")])
    
    await query.edit_message_text(
        f"📥 Выполнял (архив)\nСтраница {page + 1}/{total_pages}, всего: {len(tasks)}\n\nВыберите задачу:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

