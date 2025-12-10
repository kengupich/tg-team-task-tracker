"""Super admin handlers for registration request management."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_pending_registration_requests,
    approve_registration_request, reject_registration_request
)

logger = logging.getLogger(__name__)

__all__ = [
    'super_view_registration_requests',
    'super_review_registration_request',
    'super_approve_registration_request_handler',
    'super_reject_registration_request_handler',
]


async def super_view_registration_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show pending registration requests."""
    query = update.callback_query
    await query.answer()
    
    requests = get_pending_registration_requests()
    
    if not requests:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")]]
        await query.edit_message_text(
            "📋 Немає нових запитів на реєстрацію.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    text = f"🔔 Запити на реєстрацію ({len(requests)}):\n\n"
    keyboard = []
    
    for req in requests:
        username_info = f"@{req['username']}" if req['username'] else "немає username"
        text += f"• {req['name']} ({username_info})\n"
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {req['name']} - ID: {req['user_id']}",
                callback_data=f"super_review_request_{req['request_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="super_manage_users")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_review_registration_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show details of a registration request with approve/reject buttons."""
    query = update.callback_query
    await query.answer()
    
    request_id = int(query.data.split("_")[-1])
    requests = get_pending_registration_requests()
    request = next((r for r in requests if r['request_id'] == request_id), None)
    
    if not request:
        await query.edit_message_text("❌ Запит не знайдено або вже оброблено.")
        return
    
    username_info = f"@{request['username']}" if request['username'] else "немає username"
    text = (
        f"📋 Запит на реєстрацію\n\n"
        f"👤 Ім'я: {request['name']}\n"
        f"🆔 Telegram ID: {request['user_id']}\n"
        f"📱 Username: {username_info}\n"
        f"📅 Дата запиту: {request['requested_at']}\n\n"
        f"Схвалити цього користувача?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Схвалити", callback_data=f"super_approve_request_{request_id}")],
        [InlineKeyboardButton("❌ Відхилити", callback_data=f"super_reject_request_{request_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="super_view_registration_requests")],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def super_approve_registration_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve a registration request."""
    from database import get_pending_registration_requests, approve_registration_request
    query = update.callback_query
    await query.answer()
    
    request_id = int(query.data.split("_")[-1])
    reviewer_id = query.from_user.id
    
    # Get request details before approval to notify user
    requests = get_pending_registration_requests()
    request = next((r for r in requests if r['request_id'] == request_id), None)
    
    if not request:
        await query.edit_message_text("❌ Запит не знайдено або вже оброблено.")
        return
    
    if approve_registration_request(request_id, reviewer_id):
        # Notify user about approval
        try:
            await context.bot.send_message(
                chat_id=request['user_id'],
                text=(
                    f"✅ Ваш запит на реєстрацію схвалено!\n\n"
                    f"Тепер ви можете користуватися ботом.\n"
                    f"Адміністратор додасть вас до відділу."
                )
            )
        except Exception as e:
            logger.error(f"Failed to notify user {request['user_id']} about approval: {e}")
        
        keyboard = [[InlineKeyboardButton("⬅️ До запитів", callback_data="super_view_registration_requests")]]
        await query.edit_message_text(
            f"✅ Запит схвалено!\n\nКористувач {request['name']} тепер зареєстрований.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text("❌ Помилка при схваленні запиту.")


async def super_reject_registration_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reject a registration request."""
    from database import get_pending_registration_requests, reject_registration_request
    query = update.callback_query
    await query.answer()
    
    request_id = int(query.data.split("_")[-1])
    reviewer_id = query.from_user.id
    
    # Get request details before rejection to notify user
    requests = get_pending_registration_requests()
    request = next((r for r in requests if r['request_id'] == request_id), None)
    
    if not request:
        await query.edit_message_text("❌ Запит не знайдено або вже оброблено.")
        return
    
    if reject_registration_request(request_id, reviewer_id):
        # Notify user about rejection
        try:
            await context.bot.send_message(
                chat_id=request['user_id'],
                text=(
                    f"❌ Ваш запит на реєстрацію відхилено.\n\n"
                    f"Будь ласка, зв'яжіться з адміністратором для з'ясування деталей."
                )
            )
        except Exception as e:
            logger.error(f"Failed to notify user {request['user_id']} about rejection: {e}")
        
        keyboard = [[InlineKeyboardButton("⬅️ До запитів", callback_data="super_view_registration_requests")]]
        await query.edit_message_text(
            f"❌ Запит відхилено.\n\nКористувач {request['name']} не буде зареєстрований.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text("❌ Помилка при відхиленні запиту.")
