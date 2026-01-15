"""Start command handler."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import user_exists, has_user_group, get_admin_groups, get_user_by_id
from utils.permissions import is_super_admin, is_group_admin


async def show_main_menu(user_id: int, user_name: str, update: Update, is_callback: bool = False) -> None:
    """
    Show role-specific main menu.

    Args:
        user_id: Telegram user ID
        user_name: User's first name
        update: Update object (can be message or callback query)
        is_callback: True if called from callback query, False if from /start command
    """
    from database import get_registration_request_by_user_id

    # Check if user is Super Admin
    if is_super_admin(user_id):
        # Super Admin Menu
        keyboard = [
            [InlineKeyboardButton(
                "📋 Задачи", callback_data="view_tasks_menu")],
            [InlineKeyboardButton(
                "👥 Отделы", callback_data="super_manage_groups")],
            [InlineKeyboardButton(
                "👤 Сотрудники", callback_data="super_manage_users")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"🔐 Приветствую, {user_name}!\n\nГлавное меню:"

        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    # Check if user is Group Admin
    elif is_group_admin(user_id):
        # Group Admin Menu
        admin_groups = get_admin_groups(user_id)
        group_names = ", ".join(
            [g['name'] for g in admin_groups]) if admin_groups else "Нет"

        keyboard = [
            [InlineKeyboardButton(
                "📋 Задачи", callback_data="view_tasks_menu")],
            [InlineKeyboardButton(
                "👥 Сотрудники", callback_data="admin_manage_users")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"👋 Приветствую, {user_name}!\nОтделы: {group_names}\n\nГлавное меню:"

        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    # Regular user/worker
    else:
        # Check registration request status
        reg_request = get_registration_request_by_user_id(user_id)

        if not reg_request:
            # No registration request at all - show registration prompt
            keyboard = [[InlineKeyboardButton(
                "Зарегистрироваться", callback_data="start_registration")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"Вы не зарегистрированы. Нажмите ниже, чтобы подать заявку на регистрацию:"

            if is_callback:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)

        elif reg_request['status'] == 'pending':
            # Pending registration request
            text = (
                f"⌛ Ваш запрос на регистрацию ожидает рассмотрения администратором.\n\n"
                f"Пожалуйста, дождитесь одобрения."
            )

            if is_callback:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)

        elif reg_request['status'] == 'rejected':
            # Rejected registration request
            text = (
                f"❌ Ваш запрос на регистрацию был отклонен.\n\n"
                f"Пожалуйста, свяжитесь с администратором для уточнения деталей."
            )

            if is_callback:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)

        elif reg_request['status'] == 'approved':
            # Approved but unassigned to group
            if not has_user_group(user_id):
                text = (
                    f"✅ Вы одобрены, но еще не назначены ни в один отдел.\n\n"
                    f"Пожалуйста, свяжитесь с администратором, чтобы вас добавили в отдел."
                )

                if is_callback:
                    await update.callback_query.edit_message_text(text)
                else:
                    await update.message.reply_text(text)
            else:
                # Approved and assigned to group - show tasks
                keyboard = [
                    [InlineKeyboardButton(
                        "📋 Задачи", callback_data="view_tasks_menu")],
                    [InlineKeyboardButton(
                        "🆕 Создать задачу", callback_data="create_task")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                text = f"Приветствую, {user_name}!\n\nГлавное меню:"

                if is_callback:
                    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(text, reply_markup=reply_markup)

        else:
            # Fallback for unknown status
            text = "Статус вашей регистрации неизвестен. Свяжитесь с администратором."

            if is_callback:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show role-specific menu or registration prompt."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "User"
    user_username = update.effective_user.username

    # Check if user has a registration request
    from database import get_registration_request_by_user_id
    reg_request = get_registration_request_by_user_id(user_id)

    # If user has a pending request, don't add them to users table yet
    # If user doesn't exist in database, show registration options
    if not user_exists(user_id):
        # Check if they have a pending registration request
        if not reg_request or reg_request['status'] != 'approved':
            # No approved registration, show registration prompt
            await show_main_menu(user_id, user_name, update, is_callback=False)
            return
        else:
            # They have an approved request, add them to users table (already done in approve_registration_request)
            pass

    # Get user's name from database (or use Telegram first name as fallback)
    user = get_user_by_id(user_id)
    user_name = user['name'] if user else user_name

    await show_main_menu(user_id, user_name, update, is_callback=False)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information."""
    user_id = update.effective_user.id

    if is_super_admin(user_id):
        help_text = (
            "🔐 *Super Admin Commands:*\n"
            "/start - Show main menu\n"
            "/help - Show this help\n\n"
            "Actions via inline buttons:\n"
            "• Manage group administrators\n"
            "• Manage all users\n"
            "• View and edit all tasks\n"
        )
    elif is_group_admin(user_id):
        help_text = (
            "👔 *Group Admin Commands:*\n"
            "/start - Show main menu\n"
            "/help - Show this help\n\n"
            "Actions via inline buttons:\n"
            "• Create tasks (with media)\n"
            "• View group tasks\n"
            "• Manage group users\n"
        )
    else:
        help_text = (
            "👷 *user Commands:*\n"
            "/start - Show main menu\n"
            "/help - Show this help\n\n"
            "Actions via inline buttons:\n"
            "• View your tasks\n"
            "• Update task status\n"
            "• View your statistics\n"
        )

    await update.message.reply_text(help_text, parse_mode="Markdown")
