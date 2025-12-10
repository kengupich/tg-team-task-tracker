"""Cancel command handler."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any conversation."""
    await update.message.reply_text("❌ Розмова скасована.")
    context.user_data.clear()
    return ConversationHandler.END
