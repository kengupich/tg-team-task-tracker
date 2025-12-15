"""Task creation handlers - conversation flow for creating tasks."""

import logging
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import (
    get_all_groups, get_all_users, get_user_by_id, user_exists,
    add_task_media, get_users_for_task_assignment, get_admin_groups
)
from utils.permissions import is_super_admin, is_group_admin, get_user_group_id
from utils.helpers import generate_calendar, UKR_MONTHS, TIME_OPTIONS
from handlers.notifications import send_task_assignment_notification

logger = logging.getLogger(__name__)

# Conversation states  
TASK_STEP_TITLE = 0
TASK_STEP_DESCRIPTION = 1
# TASK_STEP_MEDIA = 2  # COMMENTED OUT - Media now added with description
TASK_STEP_DATE = 2  # Was 3
TASK_STEP_TIME = 3  # Was 4
TASK_STEP_USERS = 4  # Was 5


async def show_title_step(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True) -> None:
    """Display step 1: title input with navigation buttons."""
    task_data = context.user_data["task_data"]
    
    # Build keyboard with navigation
    nav_buttons = []
    
    # Show Forward button if user visited step 2
    if task_data.get("description_visited"):
        nav_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data="task_forward_to_description"))
    
    nav_buttons.append(InlineKeyboardButton("❌ Отменить", callback_data="cancel_task_creation"))
    
    keyboard = [nav_buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_title = task_data.get("title", "")
    text = f"📝 Шаг 1/5: Введите название задания:\n\n"
    if current_title:
        text += f"Текущее название: {current_title}"
    
    if is_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start task creation process - available for all registered users and super admins."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is registered or is a super admin
    if not user_exists(user_id) and not is_super_admin(user_id):
        await query.edit_message_text("⚠️ Вы не зарегистрированы в системе.")
        return ConversationHandler.END
    
    # Get user's group (if they have one)
    user_group_id = None
    if is_group_admin(user_id):
        user_group_id = get_user_group_id(user_id)
    else:
        user = get_user_by_id(user_id)
        if user and user.get('group_id'):
            user_group_id = user['group_id']
    
    context.user_data["task_data"] = {
        "admin_id": user_id,  # Creator of the task
        "group_id": user_group_id,  # Default group (can be changed)
        "media_files": [],
    }
    
    await show_title_step(update, context, is_query=True)
    return TASK_STEP_TITLE


async def show_description_step(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True) -> None:
    """Display step 2: description input with navigation buttons."""
    task_data = context.user_data["task_data"]
    task_data["description_visited"] = True
    
    # Build keyboard with navigation
    keyboard = []
    
    nav_buttons = [InlineKeyboardButton("⬅️ Назад", callback_data="task_back_to_title")]
    
    # Show Forward button if user visited step 3 (date_visited)
    if task_data.get("date_visited"):
        nav_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data="task_forward_to_date"))
    else: 
        nav_buttons.append(InlineKeyboardButton("⏭️ Пропустить", callback_data="task_skip_description"))
    
    nav_buttons.append(InlineKeyboardButton("❌ Отменить", callback_data="cancel_task_creation"))
    keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    title = task_data.get("title", "")
    text = f"✅ Название: {title}\n\n" \
           f"📝 Шаг 2/5: Введите описание задания (опционально).\n\n" \
           f"📷 Можете прикрепить фото к сообщению с описанием."
    
    if is_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def task_title_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store task name, ask for description."""
    context.user_data["task_data"]["title"] = update.message.text
    await show_description_step(update, context, is_query=False)
    return TASK_STEP_DESCRIPTION


# COMMENTED OUT - Media step removed from flow, media now added with description
# async def show_media_step(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True) -> None:
#     """Display step 3: media input with navigation buttons."""
#     task_data = context.user_data["task_data"]
#     task_data["media_visited"] = True
#     
#     # Build keyboard with navigation
#     keyboard = [[InlineKeyboardButton("📸 Добавить фото/видео", callback_data="task_add_media")]]
#     
#     nav_buttons = [InlineKeyboardButton("⬅️ Назад", callback_data="task_back_to_description")]
#     
#     # Show Forward if user visited step 4 (date_visited)
#     if task_data.get("date_visited"):
#         nav_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data="task_forward_to_date"))
#     else:
#         nav_buttons.append(InlineKeyboardButton("⏭️ Пропустить", callback_data="task_skip_media"))
#     
#     nav_buttons.append(InlineKeyboardButton("❌ Отменить", callback_data="cancel_task_creation"))
#     keyboard.append(nav_buttons)
#     
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     
#     media_count = len(task_data.get("media_files", []))
#     desc_display = task_data.get("description", "")
#     
#     if desc_display:
#         if len(desc_display) > 100:
#             status = f"✅ Описание: {desc_display[:100]}..."
#         else:
#             status = "✅ Описание сохранено"
#     else:
#         status = "⏭️ Описание пропущено"
#     
#     if media_count > 0:
#         status = f"📸 Загружено {media_count} файл(ов)"
#     
#     text = f"{status}\n\n🖼️ Шаг 3/6: Добавьте медиа (фото/видео) или пропустите:"
#     
#     if is_query:
#         await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
#     else:
#         await update.message.reply_text(text, reply_markup=reply_markup)


async def show_date_step(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True, year: int = None, month: int = None) -> None:
    """Display step 4: date selection with calendar and navigation buttons."""
    task_data = context.user_data["task_data"]
    task_data["date_visited"] = True
    
    # Use current date if not specified
    if year is None or month is None:
        now = datetime.now()
        year, month = now.year, now.month
    
    # Generate calendar
    calendar_keyboard = generate_calendar(year, month)
    
    # Add navigation buttons
    nav_buttons = [InlineKeyboardButton("⬅️ Назад", callback_data="task_back_to_description")]
    
    # Show Forward if user visited step 4 (time_visited)
    if task_data.get("time_visited"):
        nav_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data="task_forward_to_time"))
    
    nav_buttons.append(InlineKeyboardButton("❌ Отменить", callback_data="cancel_task_creation"))
    calendar_keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(calendar_keyboard)
    text = "📆 Шаг 3/5: Выберите дату дедлайна:"
    
    if is_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def show_time_step(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True) -> None:
    """Display step 5: time selection with navigation buttons."""
    task_data = context.user_data["task_data"]
    task_data["time_visited"] = True
    
    # Show time picker
    keyboard = []
    for i in range(0, len(TIME_OPTIONS), 4):
        row = []
        for time_opt in TIME_OPTIONS[i:i+4]:
            row.append(InlineKeyboardButton(time_opt, callback_data=f"time_select_{time_opt}"))
        keyboard.append(row)
    
    # Add navigation buttons
    nav_buttons = [InlineKeyboardButton("⬅️ Назад", callback_data="task_back_to_date")]
    
    # Show Forward if user visited step 5 (users_visited)
    if task_data.get("users_visited"):
        nav_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data="task_forward_to_users"))
    
    nav_buttons.append(InlineKeyboardButton("❌ Отменить", callback_data="cancel_task_creation"))
    keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get current selected date info
    selected_date = task_data.get("date", "")
    date_display = ""
    if selected_date:
        year, month, day = selected_date.split("-")
        date_display = f"📅 Выбрано: {day} {UKR_MONTHS[int(month)-1]} {year}\n\n"
    
    text = f"{date_display}🕒 Шаг 4/5: Выберите время дедлайна\n\n" \
           f"Или укажите время вручную в формате 00:00"
    
    if is_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def show_users_step(update: Update, context: ContextTypes.DEFAULT_TYPE, is_query: bool = True) -> None:
    """Display step 5: user selection with navigation buttons."""
    task_data = context.user_data["task_data"]
    task_data["users_visited"] = True
    
    # Get creator ID and determine their permissions
    creator_id = task_data.get("admin_id")
    creator_is_super = is_super_admin(creator_id)
    creator_is_admin = is_group_admin(creator_id)
    
    # Get available users based on creator's role
    if creator_is_super:
        all_users = get_all_users()
    elif creator_is_admin:
        # Admin can assign to users in their managed groups
        admin_groups = get_admin_groups(creator_id)
        admin_group_ids = [g['group_id'] for g in admin_groups]
        all_users = get_users_for_task_assignment(creator_id, False, True, admin_group_ids)
    else:
        # Regular worker: can assign to users in same groups + admins of those groups
        all_users = get_users_for_task_assignment(creator_id, False, False)
    
    if not all_users:
        text = "❌ Нет доступных сотрудников для назначения."
        if is_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    # Get currently selected users
    selected = task_data.get("assigned_users", [])
    
    keyboard = []
    
    # Display users with group name in brackets and username/ID
    for user in all_users:
        checkbox = "☑" if user['user_id'] in selected else "☐"
        
        # Format: Name [@username or ID] [Groups or -]
        username_part = f"@{user.get('username')}" if user.get('username') else f"ID:{user['user_id']}"
        
        # Show all groups or single group
        all_groups = user.get('all_groups', '')
        if all_groups:
            group_part = all_groups  # Already comma-separated
        else:
            group_part = user.get('group_name', '-')
        
        display_name = f"{checkbox} {user.get('name')} {username_part}" #[{group_part}]"
        
        keyboard.append([
            InlineKeyboardButton(
                display_name,
                callback_data=f"task_toggle_user_{user['user_id']}"
            )
        ])
    
    # Add navigation and action buttons
    nav_buttons = [
        InlineKeyboardButton("⬅️ Назад", callback_data="task_back_to_time"),
        InlineKeyboardButton("✅ Подтвердить", callback_data="task_confirm_users"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel_task_creation")
    ]
    keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show count of selected users
    selected_count = len(selected)
    message_text = f"👷 Шаг 6/6: Выберите исполнителей\n(Нажмите, чтобы переключить)\n\n✅ Выбрано: {selected_count}"
    
    try:
        if is_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
    except Exception as e:
        # If message is not modified (same content), just ignore the error
        if "Message is not modified" not in str(e):
            logger.error(f"Error updating user selection: {e}")
            raise


async def task_calendar_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle calendar navigation (prev/next month)."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("cal_prev_"):
        _, _, year, month = data.split("_")
        year, month = int(year), int(month)
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    elif data.startswith("cal_next_"):
        _, _, year, month = data.split("_")
        year, month = int(year), int(month)
        month += 1
        if month > 12:
            month = 1
            year += 1
    else:
        return TASK_STEP_DATE
    
    await show_date_step(update, context, is_query=True, year=year, month=month)
    return TASK_STEP_DATE


async def task_date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle date selection from calendar."""
    query = update.callback_query
    await query.answer()
    
    # Parse selected date
    _, _, year, month, day = query.data.split("_")
    selected_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    context.user_data["task_data"]["date"] = selected_date
    
    await show_time_step(update, context, is_query=True)
    return TASK_STEP_TIME


async def task_time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time selection from button - proceed to user selection."""
    query = update.callback_query
    await query.answer()
    
    # Extract time from callback data
    _, _, time = query.data.split("_")
    context.user_data["task_data"]["time"] = time
    
    await show_users_step(update, context, is_query=True)
    return TASK_STEP_USERS


async def task_time_manual_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual time input in format HH:MM - proceed to user selection."""
    import re
    
    time_text = update.message.text.strip()
    
    # Validate time format HH:MM
    time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-4]):([0-5][0-9])$')
    match = time_pattern.match(time_text)
    
    if not match:
        await update.message.reply_text(
            "❌ Неверный формат времени. Пожалуйста, введите время в формате 00:00 (например: 14:30, 09:00)"
        )
        return TASK_STEP_TIME
    
    # Normalize time format (add leading zero if needed)
    hour, minute = match.groups()
    normalized_time = f"{int(hour):02d}:{minute}"
    
    context.user_data["task_data"]["time"] = normalized_time
    
    await show_users_step(update, context, is_query=False)
    return TASK_STEP_USERS


async def task_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store description (text or text+photo), proceed to media or date."""
    # Check if message has photo (and it's not empty)
    has_photo = update.message.photo is not None and len(update.message.photo) > 0
    
    # Get text (caption if photo, otherwise message text)
    desc_text = ""
    if has_photo:
        desc_text = update.message.caption or ""
    else:
        desc_text = update.message.text or ""
    
    # Store description
    if desc_text.strip():
        context.user_data["task_data"]["description"] = desc_text.strip()
    
    # If photo attached, save it
    if has_photo:
        file_id = update.message.photo[-1].file_id
        media_files = context.user_data["task_data"].get("media_files", [])
        media_files.append({
            "file_id": file_id,
            "file_type": "photo",
            "file_name": f"photo_1.jpg",
            "file_size": update.message.photo[-1].file_size
        })
        context.user_data["task_data"]["media_files"] = media_files
        
        await update.message.reply_text(
            f"✅ Описание и фото сохранены! Переходим к выбору даты..."
        )
    
    # Go directly to date selection
    await show_date_step(update, context, is_query=False)
    return TASK_STEP_DATE


# COMMENTED OUT - Media step removed, but functionality preserved for future use
# async def task_add_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Handle media upload."""
#     query = update.callback_query
#     await query.answer()
#     
#     context.user_data["task_data"]["waiting_for_media"] = True
#     # Don't reset media_files if they already exist (from description with photo)
#     if "media_files" not in context.user_data["task_data"]:
#         context.user_data["task_data"]["media_files"] = []
#     
#     await query.edit_message_text(
#         "📸 Отправьте фото или видео (до 20 файлов).\n\n"
#         "Когда закончите, отправьте /done_media, чтобы перейти к выбору даты."
#     )
#     return TASK_STEP_MEDIA


# COMMENTED OUT - Media step removed, but functionality preserved for future use
# async def task_handle_media_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Handle incoming media files."""
#     if "task_data" not in context.user_data or not context.user_data["task_data"].get("waiting_for_media"):
#         return TASK_STEP_MEDIA
#     
#     media_files = context.user_data["task_data"].get("media_files", [])
#     
#     # Check if we've reached 20 files limit
#     if len(media_files) >= 20:
#         await update.message.reply_text("❌ Достигнут максимум 20 файлов. Отправьте /done_media, чтобы продолжить.")
#         return TASK_STEP_MEDIA
#     
#     # Handle photo
#     if update.message.photo:
#         file_id = update.message.photo[-1].file_id  # Get the largest photo
#         media_files.append({
#             "file_id": file_id,
#             "file_type": "photo",
#             "file_name": f"photo_{len(media_files)+1}.jpg",
#             "file_size": update.message.photo[-1].file_size
#         })
#         await update.message.reply_text(f"✅ Фото добавлено ({len(media_files)}/20)")
#     
#     # Handle video
#     elif update.message.video:
#         file_id = update.message.video.file_id
#         media_files.append({
#             "file_id": file_id,
#             "file_type": "video",
#             "file_name": update.message.video.file_name or f"video_{len(media_files)+1}.mp4",
#             "file_size": update.message.video.file_size
#         })
#         await update.message.reply_text(f"✅ Видео добавлено ({len(media_files)}/20)")
#     
#     # Handle document (like video)
#     elif update.message.document:
#         if update.message.document.mime_type and update.message.document.mime_type.startswith("video"):
#             file_id = update.message.document.file_id
#             media_files.append({
#                 "file_id": file_id,
#                 "file_type": "video",
#                 "file_name": update.message.document.file_name or f"video_{len(media_files)+1}.mp4",
#                 "file_size": update.message.document.file_size
#             })
#             await update.message.reply_text(f"✅ Видео добавлено ({len(media_files)}/20)")
#         else:
#             await update.message.reply_text("❌ Поддерживаются только фото и видео.")
#     
#     else:
#         await update.message.reply_text("❌ Пожалуйста, отправьте фото или видео.")
#     
#     context.user_data["task_data"]["media_files"] = media_files
#     return TASK_STEP_MEDIA


# COMMENTED OUT - Media step removed, but functionality preserved for future use
# async def task_done_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Finish media upload and proceed to date selection."""
#     if "task_data" not in context.user_data:
#         await update.message.reply_text("❌ Нет активного задания.")
#         return ConversationHandler.END
#     
#     media_count = len(context.user_data["task_data"].get("media_files", []))
#     await update.message.reply_text(f"✅ Загружено {media_count} файл(ов). Переходим к выбору даты...")
#     
#     context.user_data["task_data"]["waiting_for_media"] = False
#     await show_date_step(update, context, is_query=False)
#     return TASK_STEP_DATE
# 
# 
# async def task_skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Skip media and proceed to date selection."""
#     query = update.callback_query
#     await query.answer()
#     
#     context.user_data["task_data"]["waiting_for_media"] = False
#     await show_date_step(update, context, is_query=True)
#     return TASK_STEP_DATE


async def task_toggle_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle user selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[-1])
    selected = context.user_data["task_data"].get("assigned_users", [])
    
    if user_id in selected:
        selected.remove(user_id)
    else:
        selected.append(user_id)
    
    context.user_data["task_data"]["assigned_users"] = selected
    
    await show_users_step(update, context, is_query=True)
    return TASK_STEP_USERS


async def task_confirm_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm user selection and create task."""
    query = update.callback_query
    await query.answer()
    
    task_data = context.user_data["task_data"]
    assigned_users = task_data.get("assigned_users", [])
    
    # Get title and description separately
    title = task_data.get("title", "")
    description = task_data.get("description", "")
    
    # Determine group_id for the task
    # If creator has a group, use it; otherwise use the first assigned user's group
    group_id = task_data.get("group_id")
    if not group_id and assigned_users:
        # Get group from first assigned user
        first_user = get_user_by_id(assigned_users[0])
        if first_user and first_user.get('group_id'):
            group_id = first_user['group_id']
    
    # If still no group, use first available group
    if not group_id:
        groups = get_all_groups()
        if groups:
            group_id = groups[0]['group_id']
    
    # Create task using database function (avoid name collision with bot.create_task)
    from database import create_task as db_create_task
    task_id = db_create_task(
        date=task_data["date"],
        time=task_data["time"],
        description=description or title,  # Use description, fallback to title
        group_id=group_id,
        admin_id=task_data["admin_id"],
        assigned_to_list=assigned_users,
        title=title
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if task_id:
        # Add media if any
        for media_file in task_data.get("media_files", []):
            add_task_media(
                task_id,
                media_file["file_id"],
                media_file["file_type"],
                media_file.get("file_name"),
                media_file.get("file_size")
            )
        
        # Send notifications to assigned users
        task_desc = title  # Use title for notification
        for user_id in assigned_users:
            await send_task_assignment_notification(
                context,
                user_id,
                task_id,
                task_desc,
                task_data["date"],
                task_data["time"]
            )
        
        await query.edit_message_text(
            f"✅ Задание успешно создано!\nID задания: {task_id}\n"
            f"Назначено исполнителей: {len(assigned_users)}\n\n"
            f"📧 Отправлено {len(assigned_users)} уведомлений",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "❌ Не удалось создать задание.",
            reply_markup=reply_markup
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def task_skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip description and proceed to date step."""
    query = update.callback_query
    await query.answer()
    
    context.user_data["task_data"]["description_skipped"] = True
    await show_date_step(update, context, is_query=True)
    return TASK_STEP_DATE


async def task_forward_to_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate forward to description input step."""
    query = update.callback_query
    await query.answer()
    
    await show_description_step(update, context, is_query=True)
    return TASK_STEP_DESCRIPTION


# COMMENTED OUT - Media step removed
# async def task_forward_to_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Navigate forward to media input step."""
#     query = update.callback_query
#     await query.answer()
#     
#     await show_media_step(update, context, is_query=True)
#     return TASK_STEP_MEDIA


async def task_forward_to_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate forward to date selection step."""
    query = update.callback_query
    await query.answer()
    
    await show_date_step(update, context, is_query=True)
    return TASK_STEP_DATE


async def task_forward_to_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate forward to time selection step."""
    query = update.callback_query
    await query.answer()
    
    await show_time_step(update, context, is_query=True)
    return TASK_STEP_TIME


async def task_forward_to_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate forward to user selection step."""
    query = update.callback_query
    await query.answer()
    
    await show_users_step(update, context, is_query=True)
    return TASK_STEP_USERS


async def task_back_to_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate back to title input step."""
    query = update.callback_query
    await query.answer()
    
    await show_title_step(update, context, is_query=True)
    return TASK_STEP_TITLE


async def task_back_to_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate back to description input step."""
    query = update.callback_query
    await query.answer()
    
    await show_description_step(update, context, is_query=True)
    return TASK_STEP_DESCRIPTION


# COMMENTED OUT - Media step removed
# async def task_back_to_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Navigate back to media input step."""
#     query = update.callback_query
#     await query.answer()
#     
#     await show_media_step(update, context, is_query=True)
#     return TASK_STEP_MEDIA


async def task_back_to_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate back to date selection step."""
    query = update.callback_query
    await query.answer()
    
    await show_date_step(update, context, is_query=True)
    return TASK_STEP_DATE


async def task_back_to_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate back to time selection step."""
    query = update.callback_query
    await query.answer()
    
    await show_time_step(update, context, is_query=True)
    return TASK_STEP_TIME


async def task_back_to_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navigate back to user selection step."""
    query = update.callback_query
    await query.answer()
    
    await show_users_step(update, context, is_query=True)
    return TASK_STEP_USERS


async def cancel_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel task creation and return to menu."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data.clear()
    await query.edit_message_text("❌ Создание задания отменено.", reply_markup=reply_markup)
    

