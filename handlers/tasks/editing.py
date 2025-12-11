"""Task editing and status handlers."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_task_by_id, update_task_status, delete_task, get_user_by_id
from utils.permissions import can_edit_task
from handlers.notifications import send_status_change_notification

logger = logging.getLogger(__name__)

async def edit_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task editing request."""
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
        await query.answer("❌ У вас нет прав для редактирования этого задания", show_alert=True)
        return
    
    # For now, show a message that editing is not yet implemented
    keyboard = [[InlineKeyboardButton("⬅️ Назад к заданию", callback_data=f"view_task_{task_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🚧 Редактирование заданий пока что в разработке.\n\n"
        "Пока вы можете:\n"
        "• Просматривать задания\n"
        "• Добавлять новые задания\n"
        "• Удалять задания\n\n"
        "Функция редактирования будет добавлена в следующих обновлениях.",
        reply_markup=reply_markup
    )


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
        f"📝 {task['description'][:50]}...\n\n"
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
    """Show status selection menu for user."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    
    # Get current task status
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    current_status = task['status']
    
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
        f"🔄 Выберите новый статус задания:\n\n"
        f"📋 Задание #{task_id}\n"
        f"📝 {task['description'][:50]}...\n\n"
        f"Текущий статус: {current_status_text}",
        reply_markup=reply_markup
    )


async def set_task_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update task status and show confirmation."""
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
    
    old_status = task['status']
    admin_id = task.get('created_by')  # Creator of the task (постановник)
    
    logger.info(f"Task {task_id} status change: old_status={old_status}, new_status={new_status}, admin_id={admin_id}, user_id={user_id}")
    
    # Update status
    if update_task_status(task_id, new_status):
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
            task_desc = task['description'].split('\n')[0]  # Get first line
            
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
        
        confirmation_message = f"✅ Статус задания #{task_id} изменен на: {status_text}"
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
