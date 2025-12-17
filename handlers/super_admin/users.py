"""Super admin handlers for user management."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import (
    get_all_users, get_user_by_id, get_users_without_group,
    get_user_groups, get_all_groups, add_user, ban_user, unban_user, delete_user,
    add_user_to_group, remove_user_from_group, set_user_name, cancel_user_tasks, 
    get_pending_registration_requests, get_group_users, remove_user_from_all_groups,
)

logger = logging.getLogger(__name__)

# Conversation states for user management
USER_NAME_INPUT = 110
WAITING_GROUP_SELECT = 111
USER_ID_INPUT = 112
USER_CONFIRM = 113


__all__ = [
    'super_manage_users',
    '_render_all_employees_page',
    'super_all_employees_page',
    'super_list_group_users',
    'super_list_no_group_users',
    'super_user_action_menu',
    'super_user_set_name_start',
    'super_user_set_name_input',
    'super_user_edit_groups',
    '_render_user_groups_checklist',
    'super_user_toggle_group',
    'super_user_groups_confirm',
    'super_user_groups_cancel',
    'super_user_ban',
    'super_user_unban',
    'super_user_delete',
    'super_user_delete_confirm',
    'super_add_user',
    'super_user_select_group',
    'super_user_id_input',
    'super_user_name_input',
    'super_confirm_user',
    'super_cancel_user',
    'super_my_groups',
    'USER_NAME_INPUT',
    'WAITING_GROUP_SELECT',
    'USER_ID_INPUT',
    'USER_CONFIRM',
]


async def super_manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show departments (groups) with counts and users without group."""
    query = update.callback_query
    await query.answer()
    # Show paginated list of all employees (name, department or 'вільний').
    # This replaces the previous groups/counts view and provides immediate access
    # to every employee from the "Працівники" menu.
    await _render_all_employees_page(query, context, page=0)


async def _render_all_employees_page(query, context, page=0, page_size=10):
    """Render a paginated list of all employees (name, department or 'вільний')."""
    await query.answer()
    all_users = get_all_users() or []
    total = len(all_users)
    max_page = max(0, (total - 1) // page_size)
    page = max(0, min(page, max_page))

    start = page * page_size
    end = start + page_size
    page_users = all_users[start:end]

    text_lines = [f"Сотрудники ({total}) — страница {page+1}/{max_page+1}:\n"]
    keyboard = []

    for u in page_users:
        uid = u['user_id']
        name = u.get('name') or u.get('username', 'Неизвестно')
        # Get all groups this user belongs to
        user_groups = get_user_groups(uid)
        if user_groups:
            group_label = ', '.join([g['name'] for g in user_groups])
        else:
            group_label = 'свободный'
        
        # Add banned indicator
        banned_emoji = '⛔ ' if u.get('banned') else ''

        text_lines.append(f"• {banned_emoji}{name}, {group_label}")
        keyboard.append([InlineKeyboardButton(f"{banned_emoji}{name}, {group_label}", callback_data=f"super_user_{uid}")])

    # Navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"super_all_employees_page_{page-1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"super_all_employees_page_{page+1}"))
    if nav:
        keyboard.append(nav)

    # Back to main
    requests = get_pending_registration_requests()
    requests_text = f"🔔 Запросы на регистрацию ({len(requests)})"
    keyboard.append([InlineKeyboardButton(requests_text, callback_data="super_view_registration_requests")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")])

    await query.edit_message_text("\n".join(text_lines), reply_markup=InlineKeyboardMarkup(keyboard))


async def super_all_employees_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pagination callbacks for all-employees view."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    try:
        page = int(parts[-1])
    except Exception:
        await query.edit_message_text("❌ Неправильная страница")
        return

    await _render_all_employees_page(query, context, page=page)
    return


async def super_list_group_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    group_id = int(data.split("_")[-1])
    users = get_group_users(group_id)
    if not users:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text("Нет сотрудников в этом отделе.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    text = f"Сотрудники в отделе:\n\n"
    for u in users:
        keyboard.append([InlineKeyboardButton(f"{u['name']}", callback_data=f"super_user_{u['user_id']}")])
        text += f"• {u['name']}\n"

    # Add Edit list button
    keyboard.append([InlineKeyboardButton("✏️ Редактировать список", callback_data="super_edit_group_members")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_list_no_group_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    users = get_users_without_group() #get_users_without_group()
    if not users:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text("Нет работников без отдела.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    text = "Работники без отдела:\n\n"
    for u in users:
        keyboard.append([InlineKeyboardButton(f"{u['name']}", callback_data=f"super_user_{u['user_id']}")])
        text += f"• {u['name']}\n"

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_user_action_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split("_")[-1])
    user = get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("Работник не найден.")
        return

    # Get all groups this user belongs to
    user_groups = get_user_groups(user_id)
    if user_groups:
        groups_text = ', '.join([g['name'] for g in user_groups])
    else:
        groups_text = 'нет'
    
    # Check if user is banned
    is_banned = user.get('banned', 0) == 1
    ban_status = '⛔ Заблокирован' if is_banned else '✅ Активен'

    keyboard = [
        [InlineKeyboardButton("✏️ Установить имя", callback_data=f"super_user_set_name_{user_id}")],
        [InlineKeyboardButton("📂 Редактировать отделы", callback_data=f"super_user_edit_groups_{user_id}")],
    ]
    
    # Show unban or ban button based on status
    if is_banned:
        keyboard.append([InlineKeyboardButton("✅ Разблокировать", callback_data=f"super_user_unban_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("⛔ Заблокировать", callback_data=f"super_user_ban_{user_id}")])
    
    keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=f"super_user_delete_{user_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")])
    
    message_text = f"Работник: {user['name']}\nСтатус: {ban_status}\n\nОтделы: {groups_text}"
    await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_user_set_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    context.user_data['manage_user_id'] = user_id
    await query.edit_message_text("Введите новое имя для работника:")
    return USER_NAME_INPUT


async def super_user_set_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = context.user_data.get('manage_user_id')
    if not user_id:
        await update.message.reply_text("Работник не найден в контексте.")
        return ConversationHandler.END
    new_name = update.message.text.strip()
    if set_user_name(user_id, new_name):
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await update.message.reply_text("Имя обновлено.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Не удалось обновить имя.")
    context.user_data.pop('manage_user_id', None)
    return ConversationHandler.END


async def super_user_edit_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show checklist of all groups to edit user's group memberships."""
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    
    # Store user_id in context
    context.user_data['edit_user_groups_id'] = user_id
    
    # Get all groups and user's current groups
    all_groups = get_all_groups()
    user_groups = get_user_groups(user_id)
    user_group_ids = {g['group_id'] for g in user_groups}
    
    # Store original selection for rollback
    context.user_data['edit_user_groups_original'] = user_group_ids.copy()
    context.user_data['edit_user_groups_selection'] = user_group_ids.copy()
    
    # Render checklist
    await _render_user_groups_checklist(query, context, user_id, all_groups)
    return ConversationHandler.END


async def _render_user_groups_checklist(query, context, user_id, all_groups=None):
    """Render checklist of groups for a specific user."""
    if all_groups is None:
        all_groups = get_all_groups()
    
    selection = context.user_data.get('edit_user_groups_selection', set())
    user = get_user_by_id(user_id)
    user_name = user['name'] if user else 'Неизвестно'
    
    keyboard = []
    text = f"Редактирование отделов для {user_name}:\n\nВыберите отделы, к которым принадлежит этот работник:"
    
    for group in all_groups:
        gid = group['group_id']
        checked = '☑' if gid in selection else '☐'
        keyboard.append([InlineKeyboardButton(
            f"{checked} {group['name']}",
            callback_data=f"super_user_toggle_group_{user_id}_{gid}"
        )])
    
    # Confirm / Cancel buttons
    keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data=f"super_user_groups_confirm_{user_id}")])
    keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data=f"super_user_groups_cancel_{user_id}")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_user_toggle_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle a group selection for a user."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    user_id = int(parts[-2])
    group_id = int(parts[-1])
    
    selection = context.user_data.get('edit_user_groups_selection', set())
    if not isinstance(selection, set):
        selection = set(selection)
    
    # Toggle
    if group_id in selection:
        selection.remove(group_id)
    else:
        selection.add(group_id)
    
    context.user_data['edit_user_groups_selection'] = selection
    
    # Re-render
    await _render_user_groups_checklist(query, context, user_id)


async def super_user_groups_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Apply the group membership changes for a user."""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[-1])
    original = context.user_data.get('edit_user_groups_original', set())
    selection = context.user_data.get('edit_user_groups_selection', set())
    
    # Determine what to add and remove
    to_add = selection - original
    to_remove = original - selection
    
    # Apply changes
    for gid in to_add:
        add_user_to_group(user_id, gid)
    
    for gid in to_remove:
        remove_user_from_group(user_id, gid)
    
    # Clear context
    context.user_data.pop('edit_user_groups_id', None)
    context.user_data.pop('edit_user_groups_original', None)
    context.user_data.pop('edit_user_groups_selection', None)
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
    await query.edit_message_text(
        f"✅ Отделы обновлены (добавлено: {len(to_add)}, удалено: {len(to_remove)})",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def super_user_groups_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel group editing for a user."""
    query = update.callback_query
    await query.answer()
    
    # Clear context
    context.user_data.pop('edit_user_groups_id', None)
    context.user_data.pop('edit_user_groups_original', None)
    context.user_data.pop('edit_user_groups_selection', None)
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
    await query.edit_message_text("❌ Изменения отменены.", reply_markup=InlineKeyboardMarkup(keyboard))


async def super_user_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ban a user - remove from all groups and cancel their tasks."""
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    
    user = get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("Работник не найден.")
        return
    
    # Ban user
    if ban_user(user_id):
        # Remove from all groups
        remove_user_from_all_groups(user_id)
        # Cancel/update tasks
        result = cancel_user_tasks(user_id)
        
        message = f"⛔ Работник {user['name']} заблокирован.\n\n"
        message += f"Отменено задач: {result['cancelled']}\n"
        message += f"Обновлено задач: {result['updated']}"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("Не удалось заблокировать работника.")


async def super_user_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unban a user."""
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    
    user = get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("Работник не найден.")
        return
    
    if unban_user(user_id):
        message = f"✅ Работник {user['name']} разблокирован."
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("Не удалось разблокировать работника.")


async def super_user_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a user - ban them, remove from groups, and cancel tasks."""
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    
    user = get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("Работник не найден.")
        return
    
    # Show confirmation
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"super_user_delete_confirm_{user_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"super_user_{user_id}")],
    ]
    message = f"⚠️ Вы уверены, что хотите удалить работника {user['name']}?\n\nЭто заблокирует его и отменит все его задачи."
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_user_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute user deletion."""
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    
    user = get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("Работник не найден.")
        return
    
    # Cancel/update tasks first
    result = cancel_user_tasks(user_id)
    
    # Delete user (bans and removes from groups)
    if delete_user(user_id):
        message = f"🗑️ Работник {user['name']} удален.\n\n"
        message += f"Отменено задач: {result['cancelled']}\n"
        message += f"Обновлено задач: {result['updated']}"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("Не удалось удалить работника.")




async def super_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Super admin start adding user - show groups to select."""
    query = update.callback_query
    await query.answer()
    
    groups = get_all_groups()
    if not groups:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text(
            "Нет доступных отделов.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    keyboard = []
    for group in groups:
        keyboard.append([
            InlineKeyboardButton(
                f"📌 {group['name']}",
                callback_data=f"super_user_select_group_{group['group_id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите отдел для нового работника:",
        reply_markup=reply_markup
    )
    return WAITING_GROUP_SELECT


async def super_user_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Super admin selected group, now ask for user ID."""
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split("_")[-1])
    context.user_data["user_group_id"] = group_id
    
    await query.edit_message_text(
        "📝 Введите Telegram ID пользователя:"
    )
    return USER_ID_INPUT


async def super_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Super admin entered user ID, now ask for username."""
    try:
        user_id = int(update.message.text)
        context.user_data["user_id"] = user_id
        await update.message.reply_text(
            "👤 Введите имя пользователя:"
        )
        return USER_NAME_INPUT
    except ValueError:
        await update.message.reply_text(
            "⚠️ Неверный ID. Пожалуйста, введите действительный номер:"
        )
        return USER_ID_INPUT


async def super_user_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Super admin entered username, confirm."""
    context.user_data["user_name"] = update.message.text
    
    user_id = context.user_data["user_id"]
    user_name = context.user_data["user_name"]
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="super_confirm_user")],
        [InlineKeyboardButton("⬅️ Отменить", callback_data="super_cancel_user")],
    ]
    
    await update.message.reply_text(
        f"Подтвердите данные работника:\n"
        f"Имя: {user_name}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return USER_CONFIRM


async def super_confirm_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Super admin confirmed user, add to database."""
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data["user_id"]
    user_name = context.user_data["user_name"]
    group_id = context.user_data["user_group_id"]
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if add_user_to_group(user_id, user_name, group_id):
        await query.edit_message_text(
            f"✅ Работник успешно добавлен!",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "❌ Не удалось добавить работника (возможно, он уже существует).",
            reply_markup=reply_markup
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def super_cancel_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Super admin cancelled user creation."""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")]]
    await query.edit_message_text(
        "❌ Создание работника отменено.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END


async def super_my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow super admin to manage their own groups."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Get all groups and user's current groups
    all_groups = get_all_groups()
    user_groups = get_user_groups(user_id)
    user_group_ids = {g['group_id'] for g in user_groups}
    
    # Store original selection for rollback
    context.user_data['edit_user_groups_id'] = user_id
    context.user_data['edit_user_groups_original'] = user_group_ids.copy()
    context.user_data['edit_user_groups_selection'] = user_group_ids.copy()
    
    # Show checklist of groups
    keyboard = []
    text = "📂 Виберіть мої відділи:\n\nВи зможете отримувати завдання від співробітників в цих відділах:"
    
    for group in all_groups:
        gid = group['group_id']
        checked = '☑' if gid in user_group_ids else '☐'
        keyboard.append([InlineKeyboardButton(
            f"{checked} {group['name']}",
            callback_data=f"super_user_toggle_group_{user_id}_{gid}"
        )])
    
    # Confirm / Cancel buttons
    keyboard.append([InlineKeyboardButton("✅ Підтвердити", callback_data=f"super_user_groups_confirm_{user_id}")])
    keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="start_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ============================================================================

