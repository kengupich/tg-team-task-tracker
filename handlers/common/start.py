"""Start command handler."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import user_exists, has_user_group, get_admin_groups
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
    # Check if user is Super Admin
    if is_super_admin(user_id):
        # Super Admin Menu
        keyboard = [
            [InlineKeyboardButton("📋 Задачі", callback_data="view_tasks_menu")],
            [InlineKeyboardButton("👥 Відділи", callback_data="super_manage_groups")],
            [InlineKeyboardButton("👤 Працівники", callback_data="super_manage_users")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"🔐 Вітаю, {user_name}!\n\nГоловне меню:"
        
        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    # Check if user is Group Admin
    elif is_group_admin(user_id):
        # Group Admin Menu
        admin_groups = get_admin_groups(user_id)
        group_names = ", ".join([g['name'] for g in admin_groups]) if admin_groups else "Немає"
        
        keyboard = [
            [InlineKeyboardButton("📋 Задачі", callback_data="view_tasks_menu")],
            [InlineKeyboardButton("👥 Працівники", callback_data="admin_manage_users")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"👋 Вітаю, {user_name}!\nВідділи: {group_names}\n\nГоловне меню:"
        
        if is_callback:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    # Regular user/worker
    else:
        # Check if user is registered
        if not user_exists(user_id):
            # Not registered yet - show registration prompt
            keyboard = [[InlineKeyboardButton("Зареєструватися як користувач", callback_data="start_registration")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"Ви не зареєстровані. Натисніть нижче, щоб зареєструватися:"
            
            if is_callback:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
        
        elif not has_user_group(user_id):
            # Registered but unassigned: do not show navigation that leads to user menu
            text = (
                f"Ви зареєстровані, але ще не призначені до жодного відділу.\n\n"
                f"Будь ласка, зверніться до свого адміністратора, щоб додати вас до відділу."
            )
            
            if is_callback:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
        
        else:
            # Worker with group - show tasks
            keyboard = [
                [InlineKeyboardButton("📋 Задачі", callback_data="view_tasks_menu")],
                [InlineKeyboardButton("🆕 Створити задачу", callback_data="create_task")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"Панель завдань:"
            
            if is_callback:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show role-specific menu or registration prompt."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
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
