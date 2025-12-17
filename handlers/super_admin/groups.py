"""
Group management handlers for Super Admin.
Handles group creation, editing, member management, and admin assignment.
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import (
    create_group,
    get_all_groups,
    get_group,
    get_all_users,
    update_group_admin,
    get_group_users,
    add_user_to_group,
    remove_user_from_group,
    get_user_groups,
    get_user_by_id,
    update_group_name,
    delete_group,
    add_group_admin,
    reassign_user_tasks_to_group,
)

logger = logging.getLogger(__name__)

# Conversation state constants
SUPER_ADD_GROUP_NAME = 100
SUPER_RENAME_GROUP_INPUT = 101
WAITING_ADMIN_SELECT = 102
SUPER_EDIT_GROUP_MEMBERS = 103


async def super_manage_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of groups for admin management."""
    query = update.callback_query
    await query.answer()
    groups = get_all_groups()
    keyboard = []
    if not groups:
        keyboard = [
            [InlineKeyboardButton(f"🆕 Добавить отдел", callback_data="super_add_group")],
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Пока отделов нет.",reply_markup=reply_markup)
    
    else:
        for group in groups:
            # Get admin name if admin exists
            admin_name = "Не назначен"
            if group['admin_id']:
                admin = get_user_by_id(group['admin_id'])
                if admin:
                    admin_name = admin.get('name', 'Неизвестно')
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📌 {group['name']} (Администратор: {admin_name})",
                    callback_data=f"super_admin_select_{group['group_id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("📂 Добавить меня в отдел", callback_data="super_my_groups")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start_menu"), InlineKeyboardButton(f"🆕 Добавить отдел", callback_data="super_add_group")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите отдел для управления:", reply_markup=reply_markup)


async def super_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show menu for adding group."""
    query = update.callback_query
    await query.answer()
    # Ask for new group name
    await query.edit_message_text("Введите название отдела:")
    return SUPER_ADD_GROUP_NAME


async def super_add_group_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new group name from super admin and ask for confirmation."""
    group_name = update.message.text.strip()
    context.user_data["new_group_name"] = group_name

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="super_add_group_confirm")],
        [InlineKeyboardButton("⬅️ Отменить", callback_data="super_manage_groups")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Подтвердите создание отдела: {group_name}", reply_markup=reply_markup)
    # end the message-based step; the confirmation will come via callback buttons
    return ConversationHandler.END


async def super_add_group_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create the group after confirmation from the super admin."""
    query = update.callback_query
    await query.answer()
    group_name = context.user_data.get("new_group_name")
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_groups")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not group_name:
        await query.edit_message_text("❌ Название отдела не указано.", reply_markup=reply_markup)
        return

    group_id = create_group(group_name)
    if group_id:
        await query.edit_message_text(f"✅ Отдел '{group_name}' создан (ID: {group_id}).", reply_markup=reply_markup)
    else:
        await query.edit_message_text("❌ Не удалось создать отдел (возможно, дубликаты имен).", reply_markup=reply_markup)

    context.user_data.pop("new_group_name", None)


async def super_rename_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start group renaming process."""
    query = update.callback_query
    await query.answer()
    
    group_id = context.user_data.get("selected_group_id")
    
    if not group_id:
        await query.edit_message_text("❌ Ошибка: группа не выбрана.")
        return ConversationHandler.END
    
    group = get_group(group_id)
    
    if not group:
        await query.edit_message_text("❌ Ошибка: группа не найдена.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_groups")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Текущее название: {group['name']}\n\nВведите новое название отдела:", reply_markup=reply_markup
    )
    return SUPER_RENAME_GROUP_INPUT


async def super_rename_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process new group name input."""
    new_name = update.message.text.strip()
    group_id = context.user_data.get("selected_group_id")
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_admin_group_edit")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update_group_name(group_id, new_name):
        await update.message.reply_text(
            f"✅ Название отдела изменено на '{new_name}'",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось изменить название (возможно, название уже существует)",
            reply_markup=reply_markup
        )
    
    # Keep selected_group_id in context for "Back" button
    return ConversationHandler.END


async def super_delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a group after confirmation."""
    query = update.callback_query
    await query.answer()
    
    group_id = context.user_data.get("selected_group_id")
    
    if not group_id:
        await query.edit_message_text("❌ Помилка: група не вибрана.")
        return
    
    group = get_group(group_id)
    
    if not group:
        await query.edit_message_text("❌ Помилка: група не знайдена.")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="super_delete_group_confirm")],
        [InlineKeyboardButton("❌ Отменить", callback_data="super_admin_group_edit")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить отдел '{group['name']}'?\n\n"
        f"Все сотрудники будут отвязаны от этого отдела.",
        reply_markup=reply_markup
    )


async def super_delete_group_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute group deletion."""
    query = update.callback_query
    await query.answer()
    
    group_id = context.user_data.get("selected_group_id")
    group = get_group(group_id)
    group_name = group['name'] if group else "Unknown"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_groups")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if delete_group(group_id):
        await query.edit_message_text(
            f"✅ Отдел '{group_name}' успешно удален",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "❌ Не удалось удалить отдел",
            reply_markup=reply_markup
        )
    
    context.user_data.pop("selected_group_id", None)


async def super_admin_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle group selection for admin management."""
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split("_")[-1])
    context.user_data["selected_group_id"] = group_id
    
    group = get_group(group_id)
    
    if not group:
        await query.edit_message_text("❌ Помилка: група не знайдена.")
        return
    
    # Get admin name if admin exists
    admin_info = "Не призначено"
    if group.get('admin_id'):
        admin = get_user_by_id(group['admin_id'])
        if admin:
            admin_info = f"{admin.get('name', 'Невідомо')}"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать отдел", callback_data="super_admin_group_edit")],
        [InlineKeyboardButton("📋 Просмотреть сотрудников", callback_data="super_view_group_users")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_groups")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Отдел: {group['name']}\nАдминистратор: {admin_info}",
        reply_markup=reply_markup
    )


async def super_admin_group_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle group selection for admin management."""
    query = update.callback_query
    await query.answer()
    
    #group_id = int(query.data.split("_")[-1])
    group_id = context.user_data.get("selected_group_id")
    
    if not group_id:
        await query.edit_message_text("❌ Помилка: група не вибрана.")
        return
    
    group = get_group(group_id)
    
    if not group:
        await query.edit_message_text("❌ Помилка: група не знайдена.")
        return
    
    # Get admin name if admin exists
    admin_info = "Не призначено"
    if group.get('admin_id'):
        admin = get_user_by_id(group['admin_id'])
        if admin:
            admin_info = f"{admin.get('name', 'Невідомо')}"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить Администратора", callback_data="super_change_admin")],
        [InlineKeyboardButton("📝 Изменить Название", callback_data="super_rename_group")],
        [InlineKeyboardButton("🗑️ Удалить Отдел", callback_data="super_delete_group")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"super_admin_select_{group['group_id']}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Отдел: {group['name']}\nАдминистратор: {admin_info}",
        reply_markup=reply_markup
    )


async def super_change_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show list of users to select new admin."""
    query = update.callback_query
    await query.answer()
    keyboard = []
    users = get_all_users()
    if not users:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_back_to_group")])
    
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Нет доступных сотрудников.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    
    # Show all users to allow selecting any user as admin (no slicing)
    for user in users:
        # database.get_all_users() returns dicts with keys 'user_id' and 'name'
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {user.get('name') or user.get('username','unknown')}",
                callback_data=f"super_select_new_admin_{user['user_id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="super_back_to_group")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите нового администратора из списка:",
        reply_markup=reply_markup
    )
    return WAITING_ADMIN_SELECT


async def super_select_new_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process selected new admin."""
    query = update.callback_query
    await query.answer()
    
    new_admin_id = int(query.data.split("_")[-1])
    group_id = context.user_data.get("selected_group_id")
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_admin_group_edit")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Use many-to-many admin assignment to allow a user to be admin in multiple groups
    # Also set the legacy `groups.admin_id` to the selected admin so the UI
    # (which displays the primary admin) reflects the change.
    if add_group_admin(group_id, new_admin_id):
        # Promote the selected admin to primary admin for display purposes
        try:
            update_group_admin(group_id, new_admin_id)
        except Exception:
            # Non-fatal: even if updating legacy field fails, the many-to-many assignment succeeded
            logger.exception("Failed to update legacy groups.admin_id after add_group_admin")

        await query.edit_message_text(
            f"✅ Пользователя назначено администратором отдела.",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "❌ Не удалось назначить администратора.",
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END


async def super_back_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Go back to group details."""
    query = update.callback_query
    await query.answer()
    
    group_id = context.user_data.get("selected_group_id")
    
    if not group_id:
        await query.edit_message_text("❌ Помилка: група не вибрана.")
        return
    
    group = get_group(group_id)
    
    if not group:
        await query.edit_message_text("❌ Помилка: група не знайдена.")
        return
    
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать отдел", callback_data="super_admin_group_edit")],
        [InlineKeyboardButton("📋 Просмотреть сотрудников", callback_data="super_view_group_users")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_groups")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_name = "Не назначен"
    if group.get('admin_id'):
        admin = get_user_by_id(group['admin_id'])
        if admin:
            admin_name = admin.get('name', 'Неизвестно')
    
    await query.edit_message_text(
        f"Отдел: {group['name']}\nТекущий администратор: {admin_name}",
        reply_markup=reply_markup
    )


async def super_edit_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start editing membership list for the selected group."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data.get("selected_group_id")
    if not group_id:
        await query.edit_message_text("❌ Помилка: група не вибрана.")
        return ConversationHandler.END

    # Load all users and build selection map (include group_id from DB)
    all_users = get_all_users()
    # Build current membership map
    current_members = {u['user_id']: True for u in get_group_users(group_id)}

    # Save original membership for potential rollback
    context.user_data['edit_members_original'] = {u['user_id']: (u['user_id'] in current_members) for u in all_users}
    # Initialize working selection (copy of original)
    context.user_data['edit_members_selection'] = dict(context.user_data['edit_members_original'])
    # Store user list for pagination
    context.user_data['edit_members_all_users'] = all_users

    # Render first page (page 0)
    await _render_edit_members_page(query, context, group_id, page=0)
    return SUPER_EDIT_GROUP_MEMBERS


async def super_edit_member_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle membership selection for a specific user (in memory).
    Now supports adding users to multiple groups (not replacing)."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    # pattern: super_edit_member_toggle_{group_id}_{user_id}_{page}
    try:
        group_id = int(parts[-3])
        user_id = int(parts[-2])
        page = int(parts[-1])
    except Exception:
        # fallback for older pattern
        group_id = int(parts[-2])
        user_id = int(parts[-1])
        page = 0

    sel = context.user_data.get('edit_members_selection') or {}
    # Toggle (add or remove from THIS group, not affecting other groups)
    sel[user_id] = not bool(sel.get(user_id))
    context.user_data['edit_members_selection'] = sel

    # Re-render current page
    await _render_edit_members_page(query, context, group_id, page=page)
    return SUPER_EDIT_GROUP_MEMBERS


async def super_edit_members_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply membership changes to DB (with task reassignment where applicable)."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data.get('selected_group_id')
    if not group_id:
        await query.edit_message_text("❌ Помилка: група не вибрана.")
        return ConversationHandler.END

    # Instead of applying immediately, show preview of changes and ask for final Apply
    original = context.user_data.get('edit_members_original', {})
    selection = context.user_data.get('edit_members_selection', {})

    to_add = []
    to_remove = []
    for uid, new_val in selection.items():
        old_val = original.get(uid, False)
        if new_val and not old_val:
            to_add.append(uid)
        if old_val and not new_val:
            to_remove.append(uid)

    # Build preview text
    preview_lines = ["Перечень изменений перед подтверждением:\n"]
    if to_add:
        preview_lines.append("Добавить в эту группу:")
        for uid in to_add:
            u = get_user_by_id(uid)
            preview_lines.append(f"• {u['name']}")
    else:
        preview_lines.append("Добавить в эту группу: нет")

    if to_remove:
        preview_lines.append("\nУдалить из этой группы:")
        for uid in to_remove:
            u = get_user_by_id(uid)
            preview_lines.append(f"• {u['name']}")
    else:
        preview_lines.append("\nУдалить из этой группы: нет")

    keyboard = [
        [InlineKeyboardButton("✅ Применить изменения", callback_data="super_edit_members_apply")],
        [InlineKeyboardButton("⬅️ Вернуться", callback_data="super_edit_members_back")],
        [InlineKeyboardButton("❌ Отменить", callback_data="super_edit_members_cancel")],
    ]

    await query.edit_message_text("\n".join(preview_lines), reply_markup=InlineKeyboardMarkup(keyboard))
    return SUPER_EDIT_GROUP_MEMBERS


async def super_edit_members_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return from preview back to edit UI (render page 0)."""
    query = update.callback_query
    await query.answer()
    group_id = context.user_data.get('selected_group_id')
    if not group_id:
        await query.edit_message_text("❌ Помилка: група не вибрана.")
        return ConversationHandler.END
    await _render_edit_members_page(query, context, group_id, page=0)
    return SUPER_EDIT_GROUP_MEMBERS


async def super_edit_members_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply the membership changes to DB (called after preview).
    Now adds/removes users from THIS group without affecting other group memberships."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data.get('selected_group_id')
    original = context.user_data.get('edit_members_original', {})
    selection = context.user_data.get('edit_members_selection', {})

    changes = []
    for uid, new_val in selection.items():
        old_val = original.get(uid, False)
        if new_val != old_val:
            changes.append((uid, old_val, new_val))

    applied = 0
    for uid, old_val, new_val in changes:
        if new_val and not old_val:
            # Add to this group (doesn't remove from other groups)
            if add_user_to_group(uid, group_id):
                # Also reassign tasks where this user is an assignee to this group
                reassign_user_tasks_to_group(uid, group_id)
                applied += 1
        elif old_val and not new_val:
            # Remove from this group only
            if remove_user_from_group(uid, group_id):
                applied += 1

    # Clear edit context
    context.user_data.pop('edit_members_original', None)
    context.user_data.pop('edit_members_selection', None)
    context.user_data.pop('edit_members_all_users', None)

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_admin_group_edit")]]
    await query.edit_message_text(f"✅ Применено изменений: {applied}", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def super_edit_members_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel membership edits and revert in-memory changes."""
    query = update.callback_query
    await query.answer()
    # Discard selection maps
    context.user_data.pop('edit_members_original', None)
    context.user_data.pop('edit_members_selection', None)
    context.user_data.pop('edit_members_all_users', None)

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_admin_group_edit")]]
    await query.edit_message_text("❌ Изменения отменены.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def _render_edit_members_page(query, context, group_id, page=0, page_size=10):
    """Helper: render a specific page of the edit-members UI.
    Now shows all groups user belongs to (since users can be in multiple groups)."""
    # all_users is cached in context
    all_users = context.user_data.get('edit_members_all_users') or get_all_users()
    selection = context.user_data.get('edit_members_selection', {})

    total = len(all_users)
    max_page = max(0, (total - 1) // page_size)
    page = max(0, min(page, max_page))

    start = page * page_size
    end = start + page_size
    page_users = all_users[start:end]

    keyboard = []
    text_lines = [f"Редактирование списка сотрудников — страница {page+1}/{max_page+1}:\n\nВыберите сотрудников для этого отдела (сотрудник может принадлежать к нескольким отделам):"]

    for user in page_users:
        uid = user['user_id']
        # Get all groups this user belongs to
        user_groups = get_user_groups(uid)
        if user_groups:
            group_names = ', '.join([g['name'] for g in user_groups])
        else:
            group_names = 'свободный'
        checked = '☑' if selection.get(uid) else '☐'
        label = f"{checked} {user.get('name')} — {group_names}"
        # include page in callback so toggle returns to same page
        keyboard.append([InlineKeyboardButton(label, callback_data=f"super_edit_member_toggle_{group_id}_{uid}_{page}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"super_edit_members_page_{group_id}_{page-1}"))
    if page < max_page:
        nav_row.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"super_edit_members_page_{group_id}_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    # Confirm / Back / Cancel
    keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data="super_edit_members_confirm")])
    keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="super_edit_members_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("\n".join(text_lines), reply_markup=reply_markup)


async def super_edit_members_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    # pattern: super_edit_members_page_{group_id}_{page}
    try:
        group_id = int(parts[-2])
        page = int(parts[-1])
    except Exception:
        await query.edit_message_text("❌ Неправильная страница")
        return SUPER_EDIT_GROUP_MEMBERS

    await _render_edit_members_page(query, context, group_id, page=page)
    return SUPER_EDIT_GROUP_MEMBERS


async def super_view_group_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show users in selected group."""
    query = update.callback_query
    await query.answer()
    
    group_id = context.user_data.get("selected_group_id")
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
    # Add Edit list button (open checkbox editor)
    keyboard.append([InlineKeyboardButton("✏️ Редактировать список", callback_data="super_edit_group_members")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_back_to_group")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)


# Export all functions and constants
__all__ = [
    'SUPER_ADD_GROUP_NAME',
    'SUPER_RENAME_GROUP_INPUT',
    'WAITING_ADMIN_SELECT',
    'SUPER_EDIT_GROUP_MEMBERS',
    'super_manage_groups',
    'super_add_group',
    'super_add_group_name_input',
    'super_add_group_confirm',
    'super_rename_group',
    'super_rename_group_input',
    'super_delete_group',
    'super_delete_group_confirm',
    'super_admin_select',
    'super_admin_group_edit',
    'super_change_admin',
    'super_select_new_admin',
    'super_back_to_group',
    'super_edit_group_members',
    'super_edit_member_toggle',
    'super_edit_members_confirm',
    'super_edit_members_back',
    'super_edit_members_apply',
    'super_edit_members_cancel',
    '_render_edit_members_page',
    'super_edit_members_page',
    'super_view_group_users',
]
