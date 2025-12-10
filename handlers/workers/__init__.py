"""Worker/User handlers - my tasks and statistics."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_user_by_id

# Import filter handlers to reuse for backwards compatibility  
from handlers.tasks.filters import filter_tasks_assigned

logger = logging.getLogger(__name__)


async def user_my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Redirect to filter_tasks_assigned for backward compatibility."""
    return await filter_tasks_assigned(update, context)


async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_by_id(user_id)
    
    if user:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")]]
        await query.edit_message_text(
            f"📊 Статистика:\n"
            f"Ім'я: {user['name']}\n"
            f"Статус: Активний",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start_menu")]]
        await query.edit_message_text("⚠️ Працівника не знайдено.", reply_markup=InlineKeyboardMarkup(keyboard))
