#!/usr/bin/env python3
"""
Team Task Management Telegram Bot (v2.1 - Groups & Media Support)
Hierarchical system: Super Admin > Group Admin > users
Features: Group management, multi-assignee tasks, media attachments
"""
import os
import json
import logging
import warnings
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import config module for environment settings
from config import Config

# Suppress PTBUserWarning about per_message settings (we intentionally mix handler types)
warnings.filterwarnings("ignore", message=".*per_message.*")

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from database import (
    init_db
)

# Import utilities and handlers
from handlers.notifications import (
    send_deadline_reminder
)
from handlers.common import start, help_command, cancel, show_main_menu
from handlers.super_admin import (
    # Group management
    super_manage_groups, super_add_group, super_add_group_name_input, super_add_group_confirm,
    super_rename_group, super_rename_group_input, super_delete_group, super_delete_group_confirm,
    super_admin_select, super_admin_group_edit, super_change_admin, super_select_new_admin,
    super_back_to_group, super_edit_group_members, super_edit_member_toggle,
    super_edit_members_confirm, super_edit_members_back, super_edit_members_apply,
    super_edit_members_cancel, super_edit_members_page, super_view_group_users,
    SUPER_ADD_GROUP_NAME, SUPER_RENAME_GROUP_INPUT, WAITING_ADMIN_SELECT, SUPER_EDIT_GROUP_MEMBERS,
    # User management
    super_manage_users, super_all_employees_page, super_list_group_users, super_list_no_group_users,
    super_user_action_menu, super_user_set_name_start, super_user_set_name_input,
    super_user_edit_groups, super_user_toggle_group, super_user_groups_confirm, super_user_groups_cancel,
    super_user_ban, super_user_unban, super_user_delete, super_user_delete_confirm,
    super_add_user, super_user_select_group, super_user_id_input, super_user_name_input,
    super_confirm_user, super_cancel_user, super_my_groups,
    USER_NAME_INPUT, WAITING_GROUP_SELECT, USER_ID_INPUT, USER_CONFIRM,
    # Registration management
    super_view_registration_requests, super_review_registration_request,
    super_approve_registration_request_handler, super_reject_registration_request_handler,
)

# Import task handlers
from handlers.tasks import (
    # Filters
    view_tasks_menu, filter_tasks_created, filter_tasks_assigned,
    filter_tasks_select_group, filter_tasks_group, filter_group_all_tasks,
    filter_tasks_by_assignee, filter_tasks_all,
    filter_tasks_archived, filter_archived_created, filter_archived_assigned,
    # Creation + states
    create_task, task_title_input, task_calendar_navigation, task_date_selected,
    task_time_selected, task_time_manual_input, task_description_input,
    task_toggle_user, task_confirm_users,
    task_skip_description, task_forward_to_date, task_forward_to_time,
    task_forward_to_description, task_forward_to_users,
    task_back_to_title, task_back_to_date, task_back_to_time, task_back_to_description,
    cancel_task_creation,
    TASK_STEP_TITLE, TASK_STEP_DATE, TASK_STEP_TIME, TASK_STEP_DESCRIPTION,
    TASK_STEP_USERS,
    # Viewing
    view_task_detail, view_task_media,
    # Editing
    edit_task_handler, edit_task_field_handler, edit_title_input, edit_description_input,
    show_status_edit_menu, edit_status_select, show_media_edit_menu, edit_media_delete,
    delete_media_file, edit_media_add, handle_edit_media_file,
    show_users_edit_menu, edit_toggle_user, edit_users_done, back_to_edit_menu, cancel_task_editing, save_task_changes,
    delete_task_handler, delete_task_confirm_handler,
    change_task_status_handler, set_task_status_handler,
    EDIT_TASK_MENU, EDIT_TASK_TITLE, EDIT_TASK_DESCRIPTION, EDIT_TASK_MEDIA,
    EDIT_TASK_STATUS, EDIT_TASK_USERS,
)

# Import group_admin and worker handlers
from handlers.group_admin import admin_view_tasks, super_manage_tasks, admin_manage_users
from handlers.workers import user_my_tasks, user_stats
from handlers.registration import start_registration

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Use config for settings
TOKEN = Config.TELEGRAM_BOT_TOKEN
# Parse super admin IDs from comma-separated string
SUPER_ADMIN_IDS = [
    int(id.strip()) for id in Config.SUPER_ADMIN_ID.split(",") if id.strip()
]

# Conversation states (only those NOT imported from handlers)
# Note: TASK_STEP_* states are imported from handlers.tasks
# Note: SUPER_* states are imported from handlers.super_admin
(
    EDIT_TASK_SELECT, EDIT_TASK_FIELD,
    SUPER_MANAGE_USERS_STATE, SUPER_MANAGE_TASKS_STATE
) = range(4)

# Initialize database
try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    import sys
    sys.exit(1)


# ============================================================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle inline button callbacks."""
    import time
    query = update.callback_query
    data = query.data
    start_time = time.time()
    user_id = query.from_user.id
    
    # Debug log to trace callback operations (helps diagnose unresponsive buttons)
    logger.info(f"⏱️  START: Кнопка '{data}' від користувача {user_id}")

    try:
        # Registration button
        if data == "start_registration":
            return await start_registration(update, context)

        # Start menu (go back home)
        if data == "start_menu":
            user_id = query.from_user.id
            user_name = query.from_user.first_name
            await show_main_menu(user_id, user_name, update, is_callback=True)

        # Super admin handlers
        elif data == "super_add_group":
            await super_add_group(update, context)
        elif data == "super_add_group_confirm":
            await super_add_group_confirm(update, context)
        elif data == "super_manage_groups":
            await super_manage_groups(update, context)
        elif data == "super_rename_group":
            return await super_rename_group(update, context)
        elif data == "super_delete_group":
            await super_delete_group(update, context)
        elif data == "super_delete_group_confirm":
            await super_delete_group_confirm(update, context)
        elif data == "super_admin_group_edit":
            await super_admin_group_edit(update, context)
        elif data.startswith("super_admin_select_"):
            await super_admin_select(update, context)
        elif data == "super_change_admin":
            return await super_change_admin(update, context)
        elif data.startswith("super_select_new_admin_"):
            return await super_select_new_admin(update, context)
        elif data == "super_back_to_group":
            await super_back_to_group(update, context)
        elif data == "super_manage_users":
            return await super_manage_users(update, context)
        elif data == "super_my_groups":
            await super_my_groups(update, context)
        elif data.startswith("super_all_employees_page_"):
            await super_all_employees_page(update, context)
        elif data == "super_add_user":
            return await super_add_user(update, context)
        elif data.startswith("super_user_select_group_"):
            return await super_user_select_group(update, context)
        elif data == "super_confirm_user":
            return await super_confirm_user(update, context)
        elif data == "super_cancel_user":
            return await super_cancel_user(update, context)
        elif data == "super_manage_tasks":
            await super_manage_tasks(update, context)
        elif data == "super_view_group_users":
            await super_view_group_users(update, context)
        elif data.startswith("super_users_group_"):
            return await super_list_group_users(update, context)
        elif data == "super_users_no_group":
            return await super_list_no_group_users(update, context)
        elif data.startswith("super_user_") and data.count("_") == 2 and data.startswith("super_user_"):
            return await super_user_action_menu(update, context)
        elif data.startswith("super_user_set_name_"):
            return await super_user_set_name_start(update, context)
        elif data.startswith("super_user_edit_groups_"):
            return await super_user_edit_groups(update, context)
        elif data.startswith("super_user_toggle_group_"):
            return await super_user_toggle_group(update, context)
        elif data.startswith("super_user_groups_confirm_"):
            return await super_user_groups_confirm(update, context)
        elif data.startswith("super_user_groups_cancel_"):
            return await super_user_groups_cancel(update, context)
        elif data.startswith("super_user_ban_"):
            return await super_user_ban(update, context)
        elif data.startswith("super_user_unban_"):
            return await super_user_unban(update, context)
        elif data.startswith("super_user_delete_confirm_"):
            return await super_user_delete_confirm(update, context)
        elif data.startswith("super_user_delete_"):
            return await super_user_delete(update, context)
        
        # Registration request handlers
        elif data == "super_view_registration_requests":
            await super_view_registration_requests(update, context)
        elif data.startswith("super_review_request_"):
            await super_review_registration_request(update, context)
        elif data.startswith("super_approve_request_"):
            await super_approve_registration_request_handler(update, context)
        elif data.startswith("super_reject_request_"):
            await super_reject_registration_request_handler(update, context)

        # Admin handlers
        elif data == "admin_create_task" or data == "create_task":
            return await create_task(update, context)
        elif data == "admin_view_tasks":
            await admin_view_tasks(update, context)
        elif data == "admin_manage_users":
            await admin_manage_users(update, context)
        elif data == "admin_add_user":
            await query.answer()
            # TODO: Implement add user

        # Unified tasks menu with filters
        elif data == "view_tasks_menu":
            await view_tasks_menu(update, context)
        elif data == "filter_tasks_created":
            await filter_tasks_created(update, context)
        elif data == "filter_tasks_assigned":
            await filter_tasks_assigned(update, context)
        elif data == "filter_tasks_select_group":
            await filter_tasks_select_group(update, context)
        elif data.startswith("filter_tasks_group_"):
            await filter_tasks_group(update, context)
        elif data.startswith("filter_group_all_tasks_"):
            await filter_group_all_tasks(update, context)
        elif data.startswith("filter_tasks_assignee_"):
            await filter_tasks_by_assignee(update, context)
        elif data == "filter_tasks_all":
            await filter_tasks_all(update, context)
        elif data == "filter_tasks_archived":
            await filter_tasks_archived(update, context)
        elif data.startswith("filter_archived_created_"):
            await filter_archived_created(update, context)
        elif data.startswith("filter_archived_assigned_"):
            await filter_archived_assigned(update, context)

        # Note: task_add_media, task_skip_media, task_toggle_user, task_confirm_users,
        # and cancel_task_creation are handled by ConversationHandler for task creation.
        # Do not route them here to avoid conflicts with conversation state.

        # Task viewing handlers
        elif data.startswith("view_task_media_"):
            await view_task_media(update, context)
        elif data.startswith("view_task_"):
            await view_task_detail(update, context)
        
        # Task editing/deletion handlers
        # Note: edit_task_ is handled by ConversationHandler
        elif data.startswith("delete_task_confirm_"):
            await delete_task_confirm_handler(update, context)
        elif data.startswith("delete_task_"):
            await delete_task_handler(update, context)
        
        # Task status change handlers
        elif data.startswith("set_task_status_"):
            await set_task_status_handler(update, context)
        elif data.startswith("change_task_status_"):
            await change_task_status_handler(update, context)
        
        # user handlers
        elif data == "user_my_tasks":
            await user_my_tasks(update, context)
        elif data == "user_stats":
            await user_stats(update, context)

        else:
            await query.answer()
        
        # Log total time
        elapsed = time.time() - start_time
        if elapsed > 0.5:
            logger.info(f"⏱️  SLOW: Кнопка '{data}' обробилась за {elapsed:.2f}s")
        else:
            logger.debug(f"⏱️  OK: Кнопка '{data}' обробилась за {elapsed:.2f}s")

    except BadRequest as e:
        # Handle Telegram API errors (e.g., "Message is not modified")
        if "Message is not modified" in str(e):
            logger.debug(f"Message not modified for callback '{data}' - user {query.from_user.id}")
            try:
                await query.answer()
            except Exception:
                pass
        else:
            logger.error(f"BadRequest while handling callback '{data}': {e}")
            try:
                await query.answer(f"❌ Помилка Telegram API: {str(e)[:50]}")
            except Exception:
                pass
        return None
    except Exception as e:
        logger.exception("Error while handling callback '%s': %s", data, e)
        try:
            await query.answer("❌ Возникла ошибка при обработке вашего действия. Ошибка была зафиксирована.")
        except Exception:
            pass
        return None


# ============================================================================
def start_bot():
    """Start the bot."""
    # Enable concurrent updates for faster webhook processing
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Task creation conversation
    task_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_task, pattern="^(create_task|admin_create_task)$")],
        per_message=False,
        states={
            TASK_STEP_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_title_input),
                CallbackQueryHandler(task_forward_to_description, pattern="^task_forward_to_description$"),
                CallbackQueryHandler(cancel_task_creation, pattern="^cancel_task_creation$"),
            ],
            TASK_STEP_DATE: [
                CallbackQueryHandler(task_calendar_navigation, pattern="^cal_(prev|next)_.*"),
                CallbackQueryHandler(task_date_selected, pattern="^cal_select_.*"),
                CallbackQueryHandler(task_back_to_description, pattern="^task_back_to_description$"),
                CallbackQueryHandler(task_forward_to_time, pattern="^task_forward_to_time$"),
                CallbackQueryHandler(cancel_task_creation, pattern="^cancel_task_creation$"),
                CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^cal_ignore$"),
            ],
            TASK_STEP_TIME: [
                CallbackQueryHandler(task_time_selected, pattern="^time_select_.*$"),
                CallbackQueryHandler(task_back_to_date, pattern="^task_back_to_date$"),
                CallbackQueryHandler(task_forward_to_users, pattern="^task_forward_to_users$"),
                CallbackQueryHandler(cancel_task_creation, pattern="^cancel_task_creation$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_time_manual_input),
            ],
            TASK_STEP_DESCRIPTION: [
                MessageHandler(filters.PHOTO, task_description_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_description_input),
                CallbackQueryHandler(task_skip_description, pattern="^task_skip_description$"),
                CallbackQueryHandler(task_back_to_title, pattern="^task_back_to_title$"),
                CallbackQueryHandler(task_forward_to_date, pattern="^task_forward_to_date$"),
                CallbackQueryHandler(cancel_task_creation, pattern="^cancel_task_creation$"),
            ],
            TASK_STEP_USERS: [
                CallbackQueryHandler(task_toggle_user, pattern="^task_toggle_user_.*"),
                CallbackQueryHandler(task_confirm_users, pattern="^task_confirm_users$"),
                CallbackQueryHandler(task_back_to_time, pattern="^task_back_to_time$"),
                CallbackQueryHandler(cancel_task_creation, pattern="^cancel_task_creation$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(task_conv_handler)
    
    # Super admin change admin conversation
    change_admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(super_change_admin, pattern="^super_change_admin$")],
        per_message=False,
        states={
            WAITING_ADMIN_SELECT: [
                CallbackQueryHandler(super_select_new_admin, pattern="^super_select_new_admin_.*"),
                CallbackQueryHandler(super_back_to_group, pattern="^super_back_to_group$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(change_admin_conv)

    # Super admin edit group members conversation
    edit_members_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(super_edit_group_members, pattern="^super_edit_group_members$")],
        per_message=False,
        states={
            SUPER_EDIT_GROUP_MEMBERS: [
                CallbackQueryHandler(super_edit_member_toggle, pattern="^super_edit_member_toggle_.*"),
                CallbackQueryHandler(super_edit_members_confirm, pattern="^super_edit_members_confirm$"),
                CallbackQueryHandler(super_edit_members_cancel, pattern="^super_edit_members_cancel$"),
                CallbackQueryHandler(super_edit_members_back, pattern="^super_edit_members_back$"),
                CallbackQueryHandler(super_edit_members_apply, pattern="^super_edit_members_apply$"),
                CallbackQueryHandler(super_edit_members_page, pattern="^super_edit_members_page_.*$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(edit_members_conv)
    
    # Super admin add user conversation
    super_add_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(super_add_user, pattern="^super_add_user$")],
        per_message=False,
        states={
            WAITING_GROUP_SELECT: [
                CallbackQueryHandler(super_user_select_group, pattern="^super_user_select_group_.*"),
                CallbackQueryHandler(lambda u, c: None, pattern="^super_manage_users$"),
            ],
            USER_ID_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, super_user_id_input)],
            USER_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, super_user_name_input)],
            USER_CONFIRM: [
                CallbackQueryHandler(super_confirm_user, pattern="^super_confirm_user$"),
                CallbackQueryHandler(super_cancel_user, pattern="^super_cancel_user$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(super_add_user_conv)

    # Super admin add group conversation
    super_add_group_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(super_add_group, pattern="^super_add_group$")],
        per_message=False,
        states={
            SUPER_ADD_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, super_add_group_name_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(super_add_group_conv)

    # Super admin rename group conversation
    super_rename_group_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(super_rename_group, pattern="^super_rename_group$")],
        per_message=False,
        states={
            SUPER_RENAME_GROUP_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, super_rename_group_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(super_rename_group_conv)

    # Super admin change user name conversation
    super_user_set_name_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(super_user_set_name_start, pattern="^super_user_set_name_.*")],
        per_message=False,
        states={
            USER_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, super_user_set_name_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(super_user_set_name_conv)

    # Task editing conversation
    edit_task_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_task_handler, pattern="^edit_task_.*")],
        per_message=False,
        states={
            EDIT_TASK_MENU: [
                CallbackQueryHandler(edit_task_field_handler, pattern="^edit_task_field_.*"),
                CallbackQueryHandler(save_task_changes, pattern="^save_task_changes_.*"),
                CallbackQueryHandler(cancel_task_editing, pattern="^cancel_edit_.*"),
                CallbackQueryHandler(back_to_edit_menu, pattern="^back_to_edit_menu_.*"),
            ],
            EDIT_TASK_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title_input),
                CallbackQueryHandler(cancel_task_editing, pattern="^cancel_edit_.*"),
                CallbackQueryHandler(back_to_edit_menu, pattern="^back_to_edit_menu_.*"),
            ],
            EDIT_TASK_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description_input),
                CallbackQueryHandler(cancel_task_editing, pattern="^cancel_edit_.*"),
                CallbackQueryHandler(back_to_edit_menu, pattern="^back_to_edit_menu_.*"),
            ],
            EDIT_TASK_STATUS: [
                CallbackQueryHandler(edit_status_select, pattern="^edit_status_select_.*"),
                CallbackQueryHandler(cancel_task_editing, pattern="^cancel_edit_.*"),
                CallbackQueryHandler(back_to_edit_menu, pattern="^back_to_edit_menu_.*"),
            ],
            EDIT_TASK_MEDIA: [
                CallbackQueryHandler(edit_media_delete, pattern="^edit_media_delete_.*"),
                CallbackQueryHandler(delete_media_file, pattern="^delete_media_file_.*"),
                CallbackQueryHandler(edit_media_add, pattern="^edit_media_add_.*"),
                MessageHandler(filters.PHOTO | filters.VIDEO, handle_edit_media_file),
                CallbackQueryHandler(cancel_task_editing, pattern="^cancel_edit_.*"),
                CallbackQueryHandler(back_to_edit_menu, pattern="^back_to_edit_menu_.*"),
            ],
            EDIT_TASK_USERS: [
                CallbackQueryHandler(edit_toggle_user, pattern="^edit_toggle_user_.*"),
                CallbackQueryHandler(edit_users_done, pattern="^edit_users_done_.*"),
                CallbackQueryHandler(cancel_task_editing, pattern="^cancel_edit_.*"),
                CallbackQueryHandler(back_to_edit_menu, pattern="^back_to_edit_menu_.*"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(edit_task_conv_handler)
    
    # Callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Schedule deadline reminders (check every 30 minutes)
    job_queue = application.job_queue
    job_queue.run_repeating(send_deadline_reminder, interval=1800, first=10)  # 1800 seconds = 30 minutes
    
    # Start in debug or production mode
    config_info = Config.get_info()
    logger.info(f"Bot configuration: {config_info}")
    
    if Config.DEBUG:
        # Debug mode: use polling for local development
        logger.info("[BOT] Running in DEBUG mode (polling)")
        print("[BOT] Bot started in DEBUG mode. Press Ctrl+C to stop.")
        print("[BOT] Deadline reminder job scheduled (checks every 30 minutes)")
        application.run_polling(allowed_updates=Update.ALL_TYPES, timeout=Config.POLLING_TIMEOUT)
    else:
        # Production mode: use webhook for Railway
        logger.info(f"[BOT] Running in PRODUCTION mode (webhook)")
        # Use python-telegram-bot's built-in webhook support
        webhook_url = f"{Config.RAILWAY_URL}/webhook"
        
        print(f"[BOT] Bot started in PRODUCTION mode")
        print(f"[BOT] Webhook URL: {webhook_url}")
        print(f"[BOT] Listening on 0.0.0.0:{Config.PORT}")
        
        logger.info(f"Setting webhook URL: {webhook_url}")
        
        # Start the application with webhook
        return application.run_webhook(
            listen="0.0.0.0",
            port=Config.PORT,
            url_path="/webhook",
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES
        )
    
    return application



def main():
    """Main entry point."""
    try:
        start_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
