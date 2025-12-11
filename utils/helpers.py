"""Helper utilities for bot operations"""
import re
import calendar
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Ukrainian month names
UKR_MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

# Ukrainian day names (short)
UKR_DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Time options for selection (01:00 to 24:00)
TIME_OPTIONS = [
    "01:00", "02:00", "03:00", "04:00", "05:00", "06:00",
    "07:00", "08:00", "09:00", "10:00", "11:00", "12:00",
    "13:00", "14:00", "15:00", "16:00", "17:00", "18:00",
    "19:00", "20:00", "21:00", "22:00", "23:00", "24:00"
]


def format_task_status(status: str) -> str:
    """Format task status with emoji."""
    status_map = {
        'pending': '⏳ Ожидает',
        'in_progress': '🔄 В работе',
        'completed': '✅ Завершено',
        'cancelled': '❌ Отменено'
    }
    return status_map.get(status, status)


def get_status_emoji(status: str) -> str:
    """Get emoji for task status."""
    emoji_map = {
        'pending': '⏳',
        'in_progress': '🔄',
        'completed': '✅',
        'cancelled': '❌'
    }
    return emoji_map.get(status, '📌')


def format_task_button(task: dict) -> InlineKeyboardButton:
    """Create a standardized task button."""
    status_emoji = get_status_emoji(task['status'])
    desc = task['description'][:40] + '...' if len(task['description']) > 40 else task['description']
    
    return InlineKeyboardButton(
        f"{status_emoji} {desc} ({task['date']})",
        callback_data=f"view_task_{task['task_id']}"
    )


def generate_calendar(year, month):
    """Generate calendar keyboard for given year and month."""
    keyboard = []
    
    # Header with month/year and navigation
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(f"{UKR_MONTHS[month-1]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("▶️", callback_data=f"cal_next_{year}_{month}")
    ])
    
    # Days of week header
    keyboard.append([InlineKeyboardButton(day, callback_data="cal_ignore") for day in UKR_DAYS_SHORT])
    
    # Calendar days
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"cal_select_{year}_{month}_{day}"))
        keyboard.append(row)
    
    return keyboard


def validate_time_format(time_text: str) -> tuple[bool, str]:
    """
    Validate and normalize time format HH:MM.
    Returns (is_valid, normalized_time)
    """
    time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-4]):([0-5][0-9])$')
    match = time_pattern.match(time_text.strip())
    
    if not match:
        return False, ""
    
    # Normalize time format (add leading zero if needed)
    hour, minute = match.groups()
    normalized_time = f"{int(hour):02d}:{minute}"
    
    return True, normalized_time


def create_back_button(callback_data: str = "start_menu", text: str = "⬅️ Назад") -> InlineKeyboardMarkup:
    """Create a standard back button keyboard."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback_data)]])


def build_user_selection_keyboard(all_users: list, groups: list, selected: list) -> list:
    """Build keyboard for user selection with grouped display."""
    keyboard = []
    grouped_users = {}
    users_without_group = []
    
    # Group users by their group
    for user in all_users:
        group_id = user.get('group_id')
        if group_id:
            if group_id not in grouped_users:
                grouped_users[group_id] = []
            grouped_users[group_id].append(user)
        else:
            users_without_group.append(user)
    
    # Add users grouped by department
    for group in groups:
        if group['group_id'] in grouped_users:
            # Add group header
            keyboard.append([InlineKeyboardButton(f"📌 {group['name']}", callback_data="ignore")])
            
            # Add users from this group
            for user in grouped_users[group['group_id']]:
                checkbox = "☑" if user['user_id'] in selected else "☐"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{checkbox} {user.get('name')}",
                        callback_data=f"task_toggle_user_{user['user_id']}"
                    )
                ])
    
    # Add users without group
    if users_without_group:
        for user in users_without_group:
            checkbox = "☑" if user['user_id'] in selected else "☐"
            keyboard.append([
                InlineKeyboardButton(
                    f"{checkbox} {user.get('name')}",
                    callback_data=f"task_toggle_user_{user['user_id']}"
                )
            ])
    
    return keyboard
