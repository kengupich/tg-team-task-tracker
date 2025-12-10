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
                "⏳ Ваш запит на реєстрацію вже відправлено і очікує на розгляд адміністратором.\n\n"
                "Будь ласка, зачекайте схвалення."
            )
        elif existing_request['status'] == 'rejected':
            await query.edit_message_text(
                "❌ Ваш попередній запит на реєстрацію було відхилено.\n\n"
                "Будь ласка, зв'яжіться з адміністратором для з'ясування деталей."
            )
        return ConversationHandler.END
    
    # Create registration request
    if create_registration_request(user_id, user_name, username):
        await query.edit_message_text(
            f"✅ Запит на реєстрацію відправлено!\n\n"
            f"Очікуйте схвалення від адміністратора.\n"
            f"Ви отримаєте повідомлення, коли ваш запит буде розглянуто."
        )
    else:
        await query.edit_message_text(
            "❌ Помилка при створенні запиту на реєстрацію.\n\n"
            "Спробуйте пізніше або зв'яжіться з адміністратором."
        )
    
    return ConversationHandler.END
