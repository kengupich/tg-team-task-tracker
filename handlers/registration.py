"""User registration handler."""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import (
    create_registration_request,
    get_registration_request_by_user_id
)

logger = logging.getLogger(__name__)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start user registration process - create registration request."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    username = query.from_user.username
    
    # Check if request already exists
    existing_request = get_registration_request_by_user_id(user_id)
    if existing_request:
        if existing_request['status'] == 'pending':
            await query.edit_message_text(
                "⌛ Ваш запрос на регистрацию уже отправлен и ожидает рассмотрения администратором.\n\n"
                "Пожалуйста, дождитесь одобрения."
            )
        elif existing_request['status'] == 'rejected':
            await query.edit_message_text(
                "❌ Ваш предыдущий запрос на регистрацию был отклонен.\n\n"
                "Пожалуйста, свяжитесь с администратором для уточнения деталей."
            )
        return ConversationHandler.END
    
    # Create registration request
    if create_registration_request(user_id, user_name, username):
        await query.edit_message_text(
            f"✅ Запрос на регистрацию отправлен!\n\n"
            f"Ожидайте одобрения от администратора.\n"
            f"Вы получите уведомление, когда ваш запрос будет рассмотрен."
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при создании запроса на регистрацию.\n\n"
            "Попробуйте позже или свяжитесь с администратором."
        )
    
    return ConversationHandler.END
