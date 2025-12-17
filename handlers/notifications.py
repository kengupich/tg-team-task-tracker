"""Notification handlers for bot"""
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from datetime import datetime
from database import (
    get_all_groups, get_group_tasks, get_task_by_id, 
    get_notification_recipients, get_user_by_id
)
from utils.helpers import format_task_status
import json

logger = logging.getLogger(__name__)


async def send_task_assignment_notification(
    context: ContextTypes.DEFAULT_TYPE, 
    user_id: int, 
    task_id: int, 
    task_description: str, 
    deadline: str, 
    time: str,
    role: str = "assignee"
) -> None:
    """
    Send notification to user about new task assignment.
    
    Args:
        context: Bot context
        user_id: ID of recipient
        task_id: ID of task
        task_description: Task title/description
        deadline: Date string
        time: Time string
        role: "assignee" for regular assignees, "admin" for admins receiving as creators
    """
    try:
        if role == "assignee":
            message = (
                f"📋 Новое задание!\n\n"
                f"Вам назначено новое задание:\n\n"
                f"📝 {task_description}\n\n"
                f"📅 Дедлайн: {deadline} в {time}\n\n"
                f"Просмотрите детали в меню 'Мои задания'."
            )
        elif role == "admin":
            message = (
                f"📋 Новое задание в вашем отделе!\n\n"
                f"В отделе создано новое задание:\n\n"
                f"📝 {task_description}\n\n"
                f"📅 Дедлайн: {deadline} в {time}\n\n"
                f"Просмотрите детали в меню 'Мои задания'."
            )
        else:  # "super_admin"
            message = (
                f"📋 Новое задание в системе!\n\n"
                f"Создано новое задание:\n\n"
                f"📝 {task_description}\n\n"
                f"📅 Дедлайн: {deadline} в {time}\n\n"
                f"Просмотрите детали в меню 'Мои задания'."
            )
        
        keyboard = [[InlineKeyboardButton("📋 Просмотреть задание", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to send assignment notification to user {user_id}: {e}")


async def send_task_notification_to_admins(
    context: ContextTypes.DEFAULT_TYPE,
    task_id: int,
    task_description: str,
    deadline: str,
    time: str
) -> None:
    """
    Send notification about new task to super admin and group admins.
    
    Args:
        context: Bot context
        task_id: ID of created task
        task_description: Task title/description
        deadline: Date string
        time: Time string
    """
    try:
        recipients = get_notification_recipients(task_id, include_assignees=False)
        
        seen_admins = set()
        
        # Send to super admins
        for super_admin_id in recipients['super_admin_ids']:
            if super_admin_id not in seen_admins:
                await send_task_assignment_notification(
                    context,
                    super_admin_id,
                    task_id,
                    task_description,
                    deadline,
                    time,
                    role="super_admin"
                )
                seen_admins.add(super_admin_id)
        
        # Send to group admins (avoid duplicates)
        for admin_id in recipients['admins']:
            if admin_id not in seen_admins:
                await send_task_assignment_notification(
                    context,
                    admin_id,
                    task_id,
                    task_description,
                    deadline,
                    time,
                    role="admin"
                )
                seen_admins.add(admin_id)
    except Exception as e:
        logger.error(f"Error sending admin notifications for task {task_id}: {e}")


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
            f"🔔 Обновление статуса задания\n\n"
            f"📝 Задание: {task_description[:50]}...\n\n"
            f"Статус изменен с {old_status_text} на {new_status_text}\n\n"
            f"👤 Изменил: {changed_by_name}"
        )
        keyboard = [[InlineKeyboardButton("📋 Просмотреть задание", callback_data=f"view_task_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup)
        logger.info(f"Status change notification sent successfully to admin {admin_id}")
    except Exception as e:
        logger.error(f"Failed to send status notification to admin {admin_id}: {e}")


async def send_status_change_notification_to_all_admins(
    context: ContextTypes.DEFAULT_TYPE,
    task_id: int,
    task_description: str,
    old_status: str,
    new_status: str,
    changed_by_name: str,
    task_creator_id: int = None
) -> None:
    """
    Send status change notification to task creator and all admins.
    
    Args:
        context: Bot context
        task_id: ID of task
        task_description: Task description
        old_status: Previous status
        new_status: New status
        changed_by_name: Name of user who changed status
        task_creator_id: ID of task creator (task.created_by)
    """
    try:
        recipients = get_notification_recipients(task_id, include_assignees=False)
        
        seen_admins = set()
        
        # Send to task creator first (if not already notified as admin)
        if task_creator_id and task_creator_id not in recipients['super_admin_ids'] and task_creator_id not in recipients['admins']:
            await send_status_change_notification(
                context, task_creator_id, task_id, task_description,
                old_status, new_status, changed_by_name
            )
            seen_admins.add(task_creator_id)
        
        # Send to super admins
        for super_admin_id in recipients['super_admin_ids']:
            if super_admin_id not in seen_admins:
                await send_status_change_notification(
                    context, super_admin_id, task_id, task_description,
                    old_status, new_status, changed_by_name
                )
                seen_admins.add(super_admin_id)
        
        # Send to group admins (avoid duplicates)
        for admin_id in recipients['admins']:
            if admin_id not in seen_admins:
                await send_status_change_notification(
                    context, admin_id, task_id, task_description,
                    old_status, new_status, changed_by_name
                )
                seen_admins.add(admin_id)
    except Exception as e:
        logger.error(f"Error sending status notifications for task {task_id}: {e}")


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
                            f"🚨 ПРОСРОЧЕННЫЙ ДЕДЛАЙН!\n\n"
                            f"📋 Задание: {task['description'][:100]}...\n\n"
                            f"📅 Дедлайн был: {task['date']} в {task['time']}\n"
                            f"⏰ Просрочено на: {int(hours_overdue)} час.\n"
                            f"📊 Статус: {status_text}\n\n"
                            f"Задание требует внимания!"
                        )
                        keyboard = [[InlineKeyboardButton("📋 Просмотреть задание", callback_data=f"view_task_{task['task_id']}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Get all notification recipients (creator, assigned, super admin, group admins)
                        recipients = get_notification_recipients(task['task_id'], include_assignees=True)
                        
                        seen_ids = set()
                        
                        # Send to assigned users (виконавці)
                        for user_id in recipients['assignees']:
                            try:
                                await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
                                seen_ids.add(user_id)
                            except Exception as e:
                                logger.error(f"Failed to send overdue notification to user {user_id} for task {task['task_id']}: {e}")
                        
                        # Send to task creator if not in assigned list
                        if admin_id and admin_id not in seen_ids:
                            try:
                                await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup)
                                seen_ids.add(admin_id)
                            except Exception as e:
                                logger.error(f"Failed to send overdue notification to creator {admin_id} for task {task['task_id']}: {e}")
                        
                        # Send to super admins if not already sent
                        for super_admin_id in recipients['super_admin_ids']:
                            if super_admin_id not in seen_ids:
                                try:
                                    await context.bot.send_message(chat_id=super_admin_id, text=message, reply_markup=reply_markup)
                                    seen_ids.add(super_admin_id)
                                except Exception as e:
                                    logger.error(f"Failed to send overdue notification to super admin {super_admin_id} for task {task['task_id']}: {e}")
                        
                        # Send to group admins if not already sent
                        for admin_id in recipients['admins']:
                            if admin_id not in seen_ids:
                                try:
                                    await context.bot.send_message(chat_id=admin_id, text=message, reply_markup=reply_markup)
                                    seen_ids.add(admin_id)
                                except Exception as e:
                                    logger.error(f"Failed to send overdue notification to group admin {admin_id} for task {task['task_id']}: {e}")
    except Exception as e:
        logger.error(f"Error in deadline reminder job: {e}")
