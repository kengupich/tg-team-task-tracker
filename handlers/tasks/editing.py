"""Task editing and status handlers."""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import (
    get_task_by_id, update_task_status, delete_task, get_user_by_id,
    get_task_media, remove_task_media, add_task_media, get_all_users,
    get_users_for_task_assignment, get_admin_groups, update_task_field,
    update_assignee_status, get_assignee_status, calculate_task_status
)
from utils.permissions import can_edit_task, is_super_admin, is_group_admin
from handlers.notifications import send_status_change_notification

logger = logging.getLogger(__name__)

# Conversation states for task editing
EDIT_TASK_MENU = 0
EDIT_TASK_TITLE = 1
EDIT_TASK_DESCRIPTION = 2
EDIT_TASK_MEDIA = 3
EDIT_TASK_STATUS = 4
EDIT_TASK_USERS = 5


async def show_edit_task_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True) -> None:
    """Display task editing menu with all editable fields."""
    if not hasattr(context, 'user_data') or 'editing_task_id' not in context.user_data:
        return
    
    task_id = context.user_data['editing_task_id']
    task = get_task_by_id(task_id)
    
    if not task:
        text = "❌ Задание не найдено."
        if is_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    # Get changes that were made
    changes = context.user_data.get('task_changes', {})
    
    # Get title and description from task (with changes if applicable)
    title = changes.get('title', task.get('title', ''))
    description = changes.get('description', task.get('description', ''))
    
    status = changes.get('status', task['status'])
    assigned_users = changes.get('assigned_users', json.loads(task.get('assigned_to_list', '[]')))
    
    from utils.helpers import get_status_emoji, format_task_status
    status_emoji = get_status_emoji(status)
    status_text = format_task_status(status)
    
    message_text = f"✏️ Редактирование задания #{task_id}\n\n"
    message_text += f"📝 Название: {title}\n"
    if description:
        message_text += f"📋 Описание: {description[:50]}{'...' if len(description) > 50 else ''}\n"
    message_text += f"{status_emoji} Статус: {status_text}\n"
    message_text += f"👥 Исполнителей: {len(assigned_users)}\n\n"
    
    if changes:
        message_text += "📝 Внесены изменения:\n"
        for key in changes:
            message_text += f"  • {key}\n"
        message_text += "\n"
    
    message_text += "Выберите поле для редактирования:"
    
    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data=f"edit_task_field_title_{task_id}")],
        [InlineKeyboardButton("📋 Описание", callback_data=f"edit_task_field_description_{task_id}")],
        [InlineKeyboardButton("🖼️ Медиа", callback_data=f"edit_task_field_media_{task_id}")],
        [InlineKeyboardButton(f"{status_emoji} Статус", callback_data=f"edit_task_field_status_{task_id}")],
        [InlineKeyboardButton("👥 Исполнители", callback_data=f"edit_task_field_users_{task_id}")],
        [
            InlineKeyboardButton("💾 Сохранить", callback_data=f"save_task_changes_{task_id}"),
            InlineKeyboardButton("⬅️ Назад", callback_data=f"cancel_edit_{task_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_query:
        try:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        except:
            await update.callback_query.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)


async def edit_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle task editing request - open edit menu."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    user_id = query.from_user.id
    
    # Get task info to check permissions
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return ConversationHandler.END
    
    # Check permissions
    if not can_edit_task(user_id, task):
        await query.answer("❌ У вас нет прав для редактирования этого задания", show_alert=True)
        return ConversationHandler.END
    
    # Initialize editing session
    context.user_data['editing_task_id'] = task_id
    context.user_data['task_changes'] = {}
    
    await show_edit_task_menu(update, context, is_query=True)
    return EDIT_TASK_MENU


async def delete_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task deletion request with confirmation."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    user_id = query.from_user.id
    
    # Get task info to check permissions
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Check permissions
    if not can_edit_task(user_id, task):
        await query.answer("❌ У вас нет прав для удаления этого задания", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_task_confirm_{task_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"view_task_{task_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить задание?\n\n"
        f"📋 Задание #{task_id}\n"
        f"📝 {task.get('title') or task['description'][:50]}...\n\n"
        f"Это приведет к удалению задания и всех его медиа файлов.",
        reply_markup=reply_markup
    )


async def delete_task_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute task deletion."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    user_id = query.from_user.id
    
    # Get task info to check permissions again (security check)
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Check permissions
    if not can_edit_task(user_id, task):
        await query.answer("❌ У вас нет прав для удаления этого задания", show_alert=True)
        return
    
    # Delete task from database (includes media deletion)
    keyboard = [[InlineKeyboardButton("⬅️ К списку заданий", callback_data="super_manage_tasks")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if delete_task(task_id):
        await query.edit_message_text(
            f"✅ Задание #{task_id} успешно удалено.",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            f"❌ Не удалось удалить задание #{task_id}.",
            reply_markup=reply_markup
        )


async def change_task_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show status selection menu for user (shows their individual status)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    task_id = int(query.data.split("_")[-1])
    
    # Get current task
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Get user's individual status
    current_status = get_assignee_status(task_id, user_id)
    if current_status is None:
        # User is not an assignee, check if admin
        if user_id == task.get('created_by') or is_super_admin(user_id):
            current_status = task['status']
        else:
            await query.edit_message_text("❌ Вы не назначены на это задание.")
            return
    
    # Status options for user - only show statuses different from current
    status_options = [
        ('pending', '⏳ Ожидает'),
        ('in_progress', '🔄 В работе'),
        ('completed', '✅ Завершено')
    ]
    
    keyboard = []
    for status_value, status_label in status_options:
        if status_value != current_status:
            keyboard.append([InlineKeyboardButton(
                status_label,
                callback_data=f"set_task_status_{task_id}_{status_value}"
            )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"view_task_{task_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get current status text for display
    current_status_text = {
        'pending': '⏳ Ожидает',
        'in_progress': '🔄 В работе',
        'completed': '✅ Завершено',
        'cancelled': '❌ Отменено'
    }.get(current_status, current_status)
    
    await query.edit_message_text(
        f"🔄 Выберите новый статус:\n\n"
        f"📋 Задание #{task_id}\n"
        f"📝 {task.get('title') or task['description'][:50]}...\n\n"
        f"Ваш текущий статус: {current_status_text}",
        reply_markup=reply_markup
    )



async def set_task_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update task status for the current user (assignee-specific)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Parse callback data: set_task_status_{task_id}_{new_status}
    # Split only on first 3 underscores to handle status names with underscores (like in_progress)
    parts = query.data.split("_", 3)
    task_id = int(parts[3].split("_")[0])
    new_status = "_".join(parts[3].split("_")[1:])
    
    # Get task info before update for notification
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Get user's current status
    old_status = get_assignee_status(task_id, user_id)
    if old_status is None:
        # User is not an assignee, fall back to checking if they're admin
        admin_id = task.get('created_by')
        if user_id == admin_id or is_super_admin(user_id):
            # Admin changing overall task status
            old_status = task['status']
            if update_task_status(task_id, new_status):
                status_text = {
                    'pending': '⏳ Ожидает',
                    'in_progress': '🔄 В работе',
                    'completed': '✅ Завершено'
                }.get(new_status, new_status)
                
                keyboard = [[InlineKeyboardButton("⬅️ К заданию", callback_data=f"view_task_{task_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ Статус задания #{task_id} изменен на: {status_text}",
                    reply_markup=reply_markup
                )
        else:
            await query.edit_message_text("❌ Вы не назначены на это задание.")
        return
    
    admin_id = task.get('created_by')  # Creator of the task (постановник)
    
    logger.info(f"Task {task_id} user {user_id} status change: old_status={old_status}, new_status={new_status}")
    
    # Update assignee's individual status
    if update_assignee_status(task_id, user_id, new_status):
        # Get the new aggregate task status after update
        aggregate_status = calculate_task_status(task_id)
        
        status_text = {
            'pending': '⏳ Ожидает',
            'in_progress': '🔄 В работе',
            'completed': '✅ Завершено'
        }.get(new_status, new_status)
        
        # Send notification to admin if status changed
        notification_sent = False
        if old_status != new_status and admin_id and admin_id != user_id:
            logger.info(f"Preparing to send notification: old_status={old_status} != new_status={new_status}, admin_id={admin_id} != user_id={user_id}")
            user = get_user_by_id(user_id)
            user_name = user['name'] if user else 'Неизвестный сотрудник'
            task_desc = task.get('title') or task['description'].split('\n')[0]  # Use title or first line of description
            
            await send_status_change_notification(
                context,
                admin_id,
                task_id,
                task_desc,
                old_status,
                new_status,
                user_name
            )
            notification_sent = True
        else:
            logger.info(f"Notification skipped: old_status={old_status}, new_status={new_status}, admin_id={admin_id}, user_id={user_id}")
        
        keyboard = [[InlineKeyboardButton("⬅️ К заданию", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        confirmation_message = f"✅ Ваш статус изменен на: {status_text}"
        if old_status != aggregate_status:
            aggregate_text = {
                'pending': '⏳ Ожидает',
                'in_progress': '🔄 В работе',
                'completed': '✅ Завершено'
            }.get(aggregate_status, aggregate_status)
            confirmation_message += f"\n📊 Общий статус задания: {aggregate_text}"
        if notification_sent:
            confirmation_message += "\n\n📧 Постановщик уведомлен"
        
        await query.edit_message_text(
            confirmation_message,
            reply_markup=reply_markup
        )
    else:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ Не удалось изменить статус.",
            reply_markup=reply_markup
        )


# Field-specific edit handlers
async def edit_task_field_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route to specific field editor based on callback data."""
    query = update.callback_query
    await query.answer()
    
    # Parse: edit_task_field_{field_name}_{task_id}
    parts = query.data.split("_")
    field_name = parts[3]
    task_id = int(parts[4])
    
    context.user_data['editing_task_id'] = task_id
    
    if field_name == "title":
        await query.edit_message_text(
            "📝 Введите новое название задания:"
        )
        return EDIT_TASK_TITLE
    elif field_name == "description":
        await query.edit_message_text(
            "📋 Введите новое описание задания:"
        )
        return EDIT_TASK_DESCRIPTION
    elif field_name == "status":
        return await show_status_edit_menu(update, context)
    elif field_name == "media":
        return await show_media_edit_menu(update, context)
    elif field_name == "users":
        return await show_users_edit_menu(update, context)
    
    return EDIT_TASK_MENU


async def edit_title_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle title input during editing."""
    task_id = context.user_data.get('editing_task_id')
    new_title = update.message.text.strip()
    
    if len(new_title) > 200:
        await update.message.reply_text("❌ Название слишком длинное (максимум 200 символов)")
        return EDIT_TASK_TITLE
    
    if not new_title:
        await update.message.reply_text("❌ Название не может быть пустым")
        return EDIT_TASK_TITLE
    
    context.user_data['task_changes']['title'] = new_title
    
    await show_edit_task_menu(update, context, is_query=False)
    return EDIT_TASK_MENU


async def edit_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle description input during editing."""
    task_id = context.user_data.get('editing_task_id')
    new_description = update.message.text.strip()
    
    if len(new_description) > 2000:
        await update.message.reply_text("❌ Описание слишком длинное (максимум 2000 символов)")
        return EDIT_TASK_DESCRIPTION
    
    context.user_data['task_changes']['description'] = new_description
    
    await show_edit_task_menu(update, context, is_query=False)
    return EDIT_TASK_MENU


async def show_status_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show status selection menu for editing."""
    query = update.callback_query
    
    task_id = context.user_data.get('editing_task_id')
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return EDIT_TASK_MENU
    
    current_status = context.user_data.get('task_changes', {}).get('status', task['status'])
    
    status_options = [
        ('pending', '⏳ Ожидает'),
        ('in_progress', '🔄 В работе'),
        ('completed', '✅ Завершено')
    ]
    
    keyboard = []
    for status_value, status_label in status_options:
        if status_value != current_status:
            keyboard.append([InlineKeyboardButton(
                status_label,
                callback_data=f"edit_status_select_{task_id}_{status_value}"
            )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_edit_menu_{task_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 Выберите новый статус:",
        reply_markup=reply_markup
    )
    
    return EDIT_TASK_STATUS


async def edit_status_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle status selection during editing."""
    query = update.callback_query
    await query.answer()
    
    # Parse: edit_status_select_{task_id}_{status}
    # Split only first 3 underscores to handle status names with underscores (like in_progress)
    parts = query.data.split("_", 4)
    task_id = int(parts[3])
    new_status = parts[4]  # This now contains 'in_progress' correctly
    
    context.user_data['task_changes']['status'] = new_status
    
    await show_edit_task_menu(update, context, is_query=True)
    return EDIT_TASK_MENU


async def show_media_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show media editing menu."""
    query = update.callback_query
    
    task_id = context.user_data.get('editing_task_id')
    media_files = get_task_media(task_id)
    
    keyboard = []
    
    if media_files:
        keyboard.append([InlineKeyboardButton("🗑️ Удалить медиа", callback_data=f"edit_media_delete_{task_id}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить медиа", callback_data=f"edit_media_add_{task_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_edit_menu_{task_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"🖼️ Редактирование медиа\n\n"
    message_text += f"Файлов в задании: {len(media_files)}\n\n"
    message_text += "Выберите действие:"
    
    await query.edit_message_text(message_text, reply_markup=reply_markup)
    
    return EDIT_TASK_MEDIA


async def edit_media_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show list of media files to delete."""
    query = update.callback_query
    await query.answer()
    
    task_id = context.user_data.get('editing_task_id')
    media_files = get_task_media(task_id)
    
    if not media_files:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_edit_menu_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ Нет медиа файлов для удаления.",
            reply_markup=reply_markup
        )
        return EDIT_TASK_MEDIA
    
    keyboard = []
    for i, media in enumerate(media_files, 1):
        file_type_emoji = "📹" if media['file_type'] == 'video' else "🖼️"
        keyboard.append([InlineKeyboardButton(
            f"{file_type_emoji} Файл {i}: {media.get('file_name', 'Unknown')}",
            callback_data=f"delete_media_file_{task_id}_{media['media_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_edit_menu_{task_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите файл для удаления:",
        reply_markup=reply_markup
    )
    
    return EDIT_TASK_MEDIA


async def delete_media_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Delete selected media file."""
    query = update.callback_query
    await query.answer()
    
    # Parse: delete_media_file_{task_id}_{media_id}
    parts = query.data.split("_")
    task_id = int(parts[3])
    media_id = int(parts[4])
    
    if remove_task_media(media_id):
        await query.answer("✅ Файл удален", show_alert=True)
    else:
        await query.answer("❌ Ошибка при удалении", show_alert=True)
    
    return await show_media_edit_menu(update, context)


async def edit_media_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prepare to add media files."""
    query = update.callback_query
    await query.answer()
    
    task_id = context.user_data.get('editing_task_id')
    context.user_data['adding_media_to_task'] = task_id
    
    await query.edit_message_text(
        "📸 Отправьте фото или видео для добавления к заданию:"
    )
    
    return EDIT_TASK_MEDIA


async def handle_edit_media_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming media file for editing."""
    task_id = context.user_data.get('adding_media_to_task')
    
    if not task_id:
        return EDIT_TASK_MEDIA
    
    # Handle photo
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        add_task_media(task_id, file_id, 'photo', f"photo_{task_id}.jpg", update.message.photo[-1].file_size)
        await update.message.reply_text("✅ Фото добавлено")
    
    # Handle video
    elif update.message.video:
        file_id = update.message.video.file_id
        add_task_media(task_id, file_id, 'video', update.message.video.file_name or f"video_{task_id}.mp4", update.message.video.file_size)
        await update.message.reply_text("✅ Видео добавлено")
    
    else:
        await update.message.reply_text("❌ Поддерживаются только фото и видео")
        return EDIT_TASK_MEDIA
    
    # Ask if they want to add more
    keyboard = [
        [InlineKeyboardButton("➕ Добавить еще", callback_data=f"edit_media_add_{task_id}")],
        [InlineKeyboardButton("✅ Готово", callback_data=f"back_to_edit_menu_{task_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Добавить еще?",
        reply_markup=reply_markup
    )
    
    return EDIT_TASK_MEDIA


async def show_users_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user selection menu for editing."""
    query = update.callback_query
    
    task_id = context.user_data.get('editing_task_id')
    user_id = query.from_user.id
    task = get_task_by_id(task_id)
    
    # Get available users based on creator's role
    if is_super_admin(user_id):
        all_users = get_all_users()
    elif is_group_admin(user_id):
        admin_groups = get_admin_groups(user_id)
        admin_group_ids = [g['group_id'] for g in admin_groups]
        all_users = get_users_for_task_assignment(user_id, False, True, admin_group_ids)
    else:
        all_users = get_users_for_task_assignment(user_id, False, False)
    
    if not all_users:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_edit_menu_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ Нет доступных сотрудников.",
            reply_markup=reply_markup
        )
        return EDIT_TASK_USERS
    
    # Get currently selected users - use task_selected_users if it exists (during selection)
    # otherwise get from task_changes or original task
    if 'task_selected_users' in context.user_data:
        selected = context.user_data['task_selected_users']
    else:
        selected = context.user_data.get('task_changes', {}).get('assigned_users', json.loads(task.get('assigned_to_list', '[]')))
        context.user_data['task_selected_users'] = selected.copy()
    
    keyboard = []
    
    for user in all_users:
        checkbox = "☑" if user['user_id'] in selected else "☐"
        username_part = f"@{user.get('username')}" if user.get('username') else ""
        all_groups = user.get('all_groups', '')
        group_part = all_groups if all_groups else user.get('group_name', '-')
        
        display_name = f"{checkbox} {user.get('name')} {username_part} [{group_part}]"
        
        keyboard.append([
            InlineKeyboardButton(
                display_name,
                callback_data=f"edit_toggle_user_{task_id}_{user['user_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Готово", callback_data=f"edit_users_done_{task_id}"),
        InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_edit_menu_{task_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            f"👥 Выберите исполнителей (выбрано: {len(selected)}):",
            reply_markup=reply_markup
        )
    except Exception as e:
        # If message is not modified (same content), just ignore the error
        logger.debug(f"Message not modified in show_users_edit_menu: {e}")
    
    return EDIT_TASK_USERS


async def edit_toggle_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle user selection during editing."""
    query = update.callback_query
    await query.answer()
    
    # Parse: edit_toggle_user_{task_id}_{user_id}
    parts = query.data.split("_")
    task_id = int(parts[3])
    user_id = int(parts[4])
    
    selected = context.user_data.get('task_selected_users', [])
    
    if user_id in selected:
        selected.remove(user_id)
    else:
        selected.append(user_id)
    
    context.user_data['task_selected_users'] = selected
    
    return await show_users_edit_menu(update, context)


async def edit_users_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm user selection."""
    query = update.callback_query
    await query.answer()
    
    task_id = context.user_data.get('editing_task_id')
    selected = context.user_data.get('task_selected_users', [])
    
    context.user_data['task_changes']['assigned_users'] = selected
    
    await show_edit_task_menu(update, context, is_query=True)
    return EDIT_TASK_MENU


async def back_to_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back to edit menu."""
    query = update.callback_query
    await query.answer()
    
    await show_edit_task_menu(update, context, is_query=True)
    return EDIT_TASK_MENU


async def cancel_task_editing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel editing and clean up session state."""
    query = update.callback_query
    await query.answer()
    
    task_id = context.user_data.get('editing_task_id')
    
    # Clear editing session completely
    context.user_data.pop('editing_task_id', None)
    context.user_data.pop('task_changes', None)
    context.user_data.pop('task_selected_users', None)
    context.user_data.pop('adding_media_to_task', None)
    
    if task_id:
        # Return to task view
        from handlers.tasks.viewing import view_task_detail
        # Create a mock callback query with proper data
        query.data = f"view_task_{task_id}"
        await view_task_detail(update, context)
    
    return ConversationHandler.END


async def save_task_changes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save all changes and apply them to task."""
    query = update.callback_query
    await query.answer()
    
    task_id = context.user_data.get('editing_task_id')
    changes = context.user_data.get('task_changes', {})
    
    if not changes:
        await query.answer("ℹ️ Нет изменений для сохранения", show_alert=True)
        return EDIT_TASK_MENU
    
    task = get_task_by_id(task_id)
    
    try:
        # Update title
        if 'title' in changes:
            update_task_field(task_id, 'title', changes['title'])
        
        # Update description
        if 'description' in changes:
            update_task_field(task_id, 'description', changes['description'])
        
        # Update status
        if 'status' in changes:
            update_task_status(task_id, changes['status'])
        
        # Update assigned users
        if 'assigned_users' in changes:
            update_task_field(task_id, 'assigned_to_list', json.dumps(changes['assigned_users']))
        
        # Clear editing session
        context.user_data.pop('editing_task_id', None)
        context.user_data.pop('task_changes', None)
        
        keyboard = [[InlineKeyboardButton("⬅️ К заданию", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Задание #{task_id} успешно обновлено!",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error saving task changes: {e}")
        await query.answer("❌ Ошибка при сохранении", show_alert=True)
        return EDIT_TASK_MENU
