"""Task viewing handlers."""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_task_by_id, get_group, get_user_by_id, get_task_media, get_task_assignee_statuses
from utils.permissions import is_super_admin, is_group_admin, can_edit_task

logger = logging.getLogger(__name__)

async def view_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed task information with media and assigned users."""
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[-1])
    user_id = query.from_user.id
    
    # Clear any editing state when viewing a task (cleanup from previous edits)
    context.user_data.pop('editing_task_id', None)
    context.user_data.pop('task_changes', None)
    context.user_data.pop('task_selected_users', None)
    context.user_data.pop('adding_media_to_task', None)
    
    # Track where user came from if not already set (for back navigation)
    if 'task_view_source' not in context.user_data:
        # Try to determine source based on callback history or default to 'user_my_tasks'
        context.user_data['task_view_source'] = 'user_my_tasks'
    
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
    
    # Get assignee statuses
    assignee_statuses = get_task_assignee_statuses(task_id)
    
    assigned_users = []
    for uid in assigned_ids:
        u = get_user_by_id(uid)
        if u:
            # Get status emoji for this assignee
            user_status = assignee_statuses.get(uid, 'pending')
            status_emoji = {
                'pending': '⏳',
                'in_progress': '🔄',
                'completed': '✅',
                'cancelled': '❌'
            }.get(user_status, '❓')
            assigned_users.append(f"{status_emoji} {u['name']}")
    
    # Format status
    from utils.helpers import format_task_status
    status_text = format_task_status(task['status'])
    
    # Build task info
    task_info = f"📋 ЗАДАНИЕ #{task['task_id']}\n\n"
    
    # Add title if it exists and is different from description
    title = task.get('title', '').strip()
    if title:
        task_info += f"📝 Название:\n{title}\n\n"
    
    # Add metadata
    task_info += (
        f"📅 Дата: {task['date']}\n"
        f"🕐 Дедлайн: {task['time']}\n"
        f"📍 Отдел: {group_name}\n"
        f"📊 Общий статус: {status_text}\n"
        f"👤 Постановщик: {creator_name}\n\n"
    )
    
    # Add description if it exists
    description = task.get('description', '').strip()
    if description:
        task_info += f"📋 Описание:\n{description}\n\n"
    
    if assigned_users:
        task_info += f"👥 Исполнители ({len(assigned_users)}):\n"
        for name_with_status in assigned_users[:5]:  # Show first 5
            task_info += f"  {name_with_status}\n"
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
    
    # Add back button based on where user came from (if they're assigned to this task, prioritize user_my_tasks)
    back_callback = context.user_data.get('task_view_source', 'user_my_tasks')
    
    if is_assigned and back_callback == 'admin_view_tasks':
        # If assigned to task and came from admin view, prioritize going back to user's tasks
        back_callback = 'user_my_tasks'
        back_text = "⬅️ К моим заданиям"
    elif is_assigned:
        back_callback = 'user_my_tasks'
        back_text = "⬅️ К моим заданиям"
    elif is_super_admin(user_id):
        back_callback = 'super_manage_tasks'
        back_text = "⬅️ К списку заданий"
    elif is_group_admin(user_id):
        back_callback = 'admin_view_tasks'
        back_text = "⬅️ К списку заданий"
    else:
        back_callback = 'user_my_tasks'
        back_text = "⬅️ К моим заданиям"
    
    keyboard.append([InlineKeyboardButton(back_text, callback_data=back_callback)])
    
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
