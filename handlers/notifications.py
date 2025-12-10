"""Notification handlers for bot"""
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from datetime import datetime
from database import get_all_groups, get_group_tasks, get_task_by_id
from utils.helpers import format_task_status
import json

logger = logging.getLogger(__name__)


async def send_task_assignment_notification(
    context: ContextTypes.DEFAULT_TYPE, 
    user_id: int, 
    task_id: int, 
    task_description: str, 
    deadline: str, 
    time: str
) -> None:
    """Send notification to user about new task assignment."""
    try:
        message = (
            f"📋 Нове завдання!\n\n"
            f"Вам призначено нове завдання:\n\n"
            f"📝 {task_description}\n\n"
            f"📅 Дедлайн: {deadline} о {time}\n\n"
            f"Перегляньте деталі в меню 'Мої завдання'."
        )
        keyboard = [[InlineKeyboardButton("📋 Переглянути завдання", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to send assignment notification to user {user_id}: {e}")


async def send_status_change_notification(
    context: ContextTypes.DEFAULT_TYPE, 
    admin_id: int, 
    task_id: int, 
    task_description: str, 
    old_status: str, 
    new_status: str, 
    changed_by_name: str
) -> None:
    """Send notification to admin about task status change."""
    try:
        logger.info(f"Sending status change notification to admin {admin_id} for task {task_id}: {old_status} -> {new_status}")
        
        old_status_text = format_task_status(old_status)
        new_status_text = format_task_status(new_status)
        
        message = (
            f"🔔 Оновлення статусу завдання\n\n"
            f"📝 Завдання: {task_description[:50]}...\n\n"
            f"Статус змінено з {old_status_text} на {new_status_text}\n\n"
            f"👤 Змінив: {changed_by_name}"
        )
        keyboard = [[InlineKeyboardButton("📋 Переглянути завдання", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup)
        logger.info(f"Status change notification sent successfully to admin {admin_id}")
    except Exception as e:
        logger.error(f"Failed to send status notification to admin {admin_id}: {e}")


async def send_deadline_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check and send deadline reminders for tasks."""
    try:
        now = datetime.now()
        
        # Get all groups and their tasks
        groups = get_all_groups()
        for group in groups:
            tasks = get_group_tasks(group['group_id'])
            
            for task in tasks:
                # Skip completed or cancelled tasks
                if task['status'] in ['completed', 'cancelled']:
                    continue
                
                # Parse deadline
                try:
                    deadline_str = f"{task['date']} {task['time']}"
                    deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
                except Exception as e:
                    logger.error(f"Error parsing deadline for task {task['task_id']}: {e}")
                    continue
                
                # Check if overdue
                if deadline < now:
                    hours_overdue = (now - deadline).total_seconds() / 3600
                    
                    # Send reminder only once per day (check if hours_overdue is close to a multiple of 24)
                    if hours_overdue % 24 < 1:  # Within first hour of each day overdue
                        admin_id = task.get('created_by')
                        assigned_ids = json.loads(task.get('assigned_to_list') or '[]')
                        
                        status_text = format_task_status(task['status'])
                        
                        message = (
                            f"🚨 ПРОТЕРМІНОВАНИЙ ДЕДЛАЙН!\n\n"
                            f"📋 Завдання: {task['description'][:100]}...\n\n"
                            f"📅 Дедлайн був: {task['date']} о {task['time']}\n"
                            f"⏰ Прострочено на: {int(hours_overdue)} год.\n"
                            f"📊 Статус: {status_text}\n\n"
                            f"Завдання потребує уваги!"
                        )
                        keyboard = [[InlineKeyboardButton("📋 Переглянути завдання", callback_data=f"view_task_{task['task_id']}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Send to assigned users (виконавці)
                        for user_id in assigned_ids:
                            try:
                                await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
                            except Exception as e:
                                logger.error(f"Failed to send overdue notification to user {user_id} for task {task['task_id']}: {e}")
                        
                        # Send to admin/creator only if they are NOT in assigned list
                        if admin_id and admin_id not in assigned_ids:
                            try:
                                await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup)
                            except Exception as e:
                                logger.error(f"Failed to send overdue notification to admin {admin_id} for task {task['task_id']}: {e}")
    except Exception as e:
        logger.error(f"Error in deadline reminder job: {e}")
