"""Task viewing handlers."""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_task_by_id, get_group, get_user_by_id, get_task_media
from utils.permissions import is_super_admin, is_group_admin, can_edit_task

logger = logging.getLogger(__name__)

async def view_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed task information with media and assigned users."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    user_id = query.from_user.id
    
    # Get task details
    task = get_task_by_id(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Get group info
    group = get_group(task['group_id'])
    group_name = group['name'] if group else 'Неизвестно'
    
    # Get creator info
    creator = get_user_by_id(task.get('created_by')) if task.get('created_by') else None
    creator_name = creator['name'] if creator else 'Неизвестно'
    
    # Get assigned users
    import json
    assigned_ids = json.loads(task.get('assigned_to_list') or '[]')
    assigned_users = []
    for uid in assigned_ids:
        u = get_user_by_id(uid)
        if u:
            assigned_users.append(u['name'])
    
    # Format status
    status_text = {
        'pending': '⏳ Ожидает',
        'in_progress': '🔄 В работе',
        'completed': '✅ Завершено',
        'cancelled': '❌ Отменено'
    }.get(task['status'], task['status'])
    
    # Build task info
    task_info = (
        f"📋 ЗАДАНИЕ #{task['task_id']}\n\n"
        f"📅 Дата: {task['date']}\n"
        f"🕐 Время: {task['time']}\n"
        f"📍 Отдел: {group_name}\n"
        f"📊 Статус: {status_text}\n"
        f"👤 Постановщик: {creator_name}\n\n"
        f"📝 Описание:\n{task['description']}\n\n"
    )
    
    if assigned_users:
        task_info += f"👥 Исполнители ({len(assigned_users)}):\n"
        for name in assigned_users[:5]:  # Show first 5
            task_info += f"  • {name}\n"
        if len(assigned_users) > 5:
            task_info += f"  ... и еще {len(assigned_users) - 5}\n"
    else:
        task_info += "👥 Никто не назначен\n"
    
    # Check if task has media
    media_files = get_task_media(task_id) if task.get('has_media') else []
    if media_files:
        task_info += f"\n📎 Медиа файлов: {len(media_files)}\n"
    
    # Build keyboard based on user permissions
    keyboard = []
    
    # Show media button if media exists
    if media_files:
        keyboard.append([InlineKeyboardButton("📷 Просмотреть медиа", callback_data=f"view_task_media_{task_id}")])
    
    # Check if user can edit/delete this task
    can_edit = can_edit_task(user_id, task)
    
    # Determine if user is assigned to this task
    is_assigned = user_id in assigned_ids
    
    # Build action buttons based on permissions
    if can_edit:
        # User can edit/delete (super admin, creator, or group admin of creator)
        keyboard.append([InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_task_{task_id}")])
        keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_task_{task_id}")])
        
        # If also assigned, add status change button
        if is_assigned:
            keyboard.append([InlineKeyboardButton("🔄 Изменить статус", callback_data=f"change_task_status_{task_id}")])
    else:
        # Regular user who cannot edit
        if is_assigned:
            # Assigned executor can change status
            keyboard.append([InlineKeyboardButton("🔄 Изменить статус", callback_data=f"change_task_status_{task_id}")])
    
    # Add back button based on user role
    if is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("⬅️ К списку заданий", callback_data="super_manage_tasks")])
    elif is_group_admin(user_id):
        keyboard.append([InlineKeyboardButton("⬅️ К списку заданий", callback_data="admin_view_tasks")])
    else:
        keyboard.append([InlineKeyboardButton("⬅️ К моим заданиям", callback_data="user_my_tasks")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(task_info, reply_markup=reply_markup)


async def view_task_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send all media files for a task and duplicate message with buttons."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    
    # Get media files
    media_files = get_task_media(task_id)
    
    if not media_files:
        await query.answer("❌ Медиа файлов не найдено", show_alert=True)
        return
    
    # Store original message info
    original_message_id = query.message.message_id
    original_text = query.message.text
    original_markup = query.message.reply_markup
    
    # Send notification
    sent_count = 0
    failed_count = 0
    
    for media in media_files:
        try:
            if media['file_type'] == 'photo':
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=media['file_id'],
                    caption=f"Задание #{task_id}"
                )
                sent_count += 1
            elif media['file_type'] == 'video':
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=media['file_id'],
                    caption=f"Задание #{task_id}"
                )
                sent_count += 1
        except Exception as e:
            logger.error(f"Error sending media {media['media_id']}: {e}")
            failed_count += 1
    
    # Send duplicated message with buttons below media
    if sent_count > 0:
        summary = f"✅ Отправлено {sent_count} файл(ов)"
        if failed_count > 0:
            summary += f"\n⚠️ Не удалось отправить {failed_count} файл(ов)"
        
        # Send duplicated message with original text and buttons
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"{summary}\n\n{original_text}",
            reply_markup=original_markup
        )
        
        # Delete original message
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=original_message_id
            )
        except Exception as e:
            logger.error(f"Error deleting original message: {e}")
    elif failed_count > 0:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Не удалось отправить {failed_count} файл(ов). Возможно файлы устарели."
        )
