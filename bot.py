#!/usr/bin/env python3
"""
Team Task Management Telegram Bot
This bot allows admins to create tasks, workers to accept/decline them,
and tracks worker performance in a SQLite database.
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
    init_db,
    add_worker,
    remove_worker,
    get_all_workers,
    create_task,
    get_task_by_id,
    update_task_status,
    get_all_tasks,
    get_worker_stats,
    get_worker_by_id,
    worker_exists,
)
from utils import is_admin

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# States for conversation handlers
TASK_ADDRESS, TASK_DATE, TASK_TIME, TASK_DESCRIPTION = range(4)
WORKER_USERNAME = range(1)

# Initialize database
init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if is_admin(user_id, ADMIN_IDS):
        message = (
            f"👋 Welcome, Admin {user_name}!\n\n"
            "🔹 Use /create_task to add a new task\n"
            "🔹 Use /add_worker to register a new worker\n"
            "🔹 Use /remove_worker to unregister a worker\n"
            "🔹 Use /list_workers to see all registered workers\n"
            "🔹 Use /list_tasks to see all tasks\n"
            "🔹 Use /view_stats to check worker performance\n"
            "🔹 Use /help for more information"
        )
    else:
        # Add worker to database if they don't exist yet
        if not worker_exists(user_id):
            username = update.effective_user.username or user_name
            add_worker(user_id, username)
            
        message = (
            f"👋 Welcome, {user_name}!\n\n"
            "You'll receive task notifications when they're available.\n"
            "🔹 Use /accept to accept a task\n"
            "🔹 Use /decline to decline a task\n"
            "🔹 Use /my_tasks to see your assigned tasks\n"
            "🔹 Use /my_stats to see your performance\n"
            "🔹 Use /help for more information"
        )
    
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    
    if is_admin(user_id, ADMIN_IDS):
        message = (
            "📋 *Admin Commands:*\n"
            "/create_task - Create a new task\n"
            "/add_worker - Register a new worker\n"
            "/remove_worker - Unregister a worker\n"
            "/list_workers - View all registered workers\n"
            "/list_tasks - View all tasks\n"
            "/view_stats - View worker performance stats\n"
            "/help - Show this help message\n"
        )
    else:
        message = (
            "📋 *Worker Commands:*\n"
            "/accept - Accept a task (with task ID)\n"
            "/decline - Decline a task (with task ID)\n"
            "/my_tasks - View your assigned tasks\n"
            "/my_stats - View your performance stats\n"
            "/help - Show this help message\n"
        )
    
    await update.message.reply_text(message, parse_mode="Markdown")

# Admin: Create task conversation handler
async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the task creation process."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, ADMIN_IDS):
        await update.message.reply_text("⚠️ You don't have admin privileges.")
        return ConversationHandler.END
    
    await update.message.reply_text("📍 Please enter the task address:")
    return TASK_ADDRESS

async def task_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store task address and ask for date."""
    context.user_data["address"] = update.message.text
    await update.message.reply_text(
        "📆 Please enter the task date (YYYY-MM-DD):"
    )
    return TASK_DATE

async def task_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store task date and ask for time."""
    date_text = update.message.text
    
    # Validate date format
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        context.user_data["date"] = date_text
        await update.message.reply_text(
            "🕒 Please enter the task time (HH:MM):"
        )
        return TASK_TIME
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid date format. Please use YYYY-MM-DD (e.g., 2023-12-31):"
        )
        return TASK_DATE

async def task_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store task time and ask for description."""
    time_text = update.message.text
    
    # Validate time format
    try:
        datetime.strptime(time_text, "%H:%M")
        context.user_data["time"] = time_text
        await update.message.reply_text(
            "📝 Please enter the task description:"
        )
        return TASK_DESCRIPTION
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid time format. Please use HH:MM (e.g., 14:30):"
        )
        return TASK_TIME

async def task_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store task description and create task in database."""
    context.user_data["description"] = update.message.text
    
    # Create task in database
    task_id = create_task(
        context.user_data["address"],
        context.user_data["date"],
        context.user_data["time"],
        context.user_data["description"]
    )
    
    # Send confirmation message to admin
    await update.message.reply_text(
        f"✅ Task created successfully!\n\n"
        f"📝 *Task ID:* {task_id}\n"
        f"📍 *Address:* {context.user_data['address']}\n"
        f"📆 *Date:* {context.user_data['date']}\n"
        f"🕒 *Time:* {context.user_data['time']}\n"
        f"📄 *Description:* {context.user_data['description']}",
        parse_mode="Markdown"
    )
    
    # Broadcast task to all workers
    workers = get_all_workers()
    task_details = (
        f"🆕 *New Task Available*\n\n"
        f"📝 *Task ID:* {task_id}\n"
        f"📍 *Address:* {context.user_data['address']}\n"
        f"📆 *Date:* {context.user_data['date']}\n"
        f"🕒 *Time:* {context.user_data['time']}\n"
        f"📄 *Description:* {context.user_data['description']}\n\n"
        f"Use /accept {task_id} to accept this task or /decline {task_id} to decline."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("Accept ✅", callback_data=f"accept_{task_id}"),
            InlineKeyboardButton("Decline ❌", callback_data=f"decline_{task_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    broadcast_count = 0
    for worker in workers:
        try:
            await context.bot.send_message(
                chat_id=worker["id"],
                text=task_details,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            broadcast_count += 1
        except Exception as e:
            logger.error(f"Failed to send task to worker {worker['id']}: {e}")
    
    await update.message.reply_text(
        f"📢 Task broadcast to {broadcast_count} workers."
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the task creation process."""
    await update.message.reply_text("❌ Task creation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# Admin: Add worker conversation handler
async def add_worker_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process to add a worker."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, ADMIN_IDS):
        await update.message.reply_text("⚠️ You don't have admin privileges.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Please enter the Telegram ID of the worker to add.\n"
        "(Note: The worker needs to start the bot first)"
    )
    return WORKER_USERNAME

async def add_worker_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process worker ID and add to database."""
    try:
        worker_id = int(update.message.text.strip())
        worker_name = f"Worker-{worker_id}"
        
        # Add worker to database
        success = add_worker(worker_id, worker_name)
        
        if success:
            await update.message.reply_text(f"✅ Worker with ID {worker_id} added successfully!")
            
            # Notify the worker
            try:
                await context.bot.send_message(
                    chat_id=worker_id,
                    text="✅ You have been added as a worker by an admin. You'll now receive task notifications."
                )
            except Exception as e:
                await update.message.reply_text(
                    f"⚠️ Worker added, but notification failed: {str(e)}\n"
                    "Make sure the worker has started a conversation with the bot."
                )
        else:
            await update.message.reply_text(f"ℹ️ Worker with ID {worker_id} already exists.")
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("⚠️ Invalid worker ID. Please enter a valid numerical Telegram ID:")
        return WORKER_USERNAME

async def cancel_add_worker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the worker addition process."""
    await update.message.reply_text("❌ Worker addition cancelled.")
    return ConversationHandler.END

# Admin: Remove worker command
async def remove_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a worker from the system."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, ADMIN_IDS):
        await update.message.reply_text("⚠️ You don't have admin privileges.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a worker ID: /remove_worker [worker_id]")
        return
    
    try:
        worker_id = int(context.args[0])
        success = remove_worker(worker_id)
        
        if success:
            await update.message.reply_text(f"✅ Worker with ID {worker_id} removed successfully!")
            
            # Notify the worker
            try:
                await context.bot.send_message(
                    chat_id=worker_id,
                    text="ℹ️ You have been removed as a worker by an admin. You'll no longer receive task notifications."
                )
            except Exception:
                pass  # Ignore if notification fails
        else:
            await update.message.reply_text(f"⚠️ Worker with ID {worker_id} not found.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid worker ID. Please provide a valid numerical ID.")

# Admin: List workers command
async def list_workers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all registered workers."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, ADMIN_IDS):
        await update.message.reply_text("⚠️ You don't have admin privileges.")
        return
    
    workers = get_all_workers()
    
    if not workers:
        await update.message.reply_text("ℹ️ No workers registered yet.")
        return
    
    workers_text = "👥 *Registered Workers:*\n\n"
    for i, worker in enumerate(workers, 1):
        workers_text += f"{i}. ID: {worker['id']} - {worker['username']}\n"
    
    await update.message.reply_text(workers_text, parse_mode="Markdown")

# Admin: List tasks command
async def list_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all tasks."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, ADMIN_IDS):
        await update.message.reply_text("⚠️ You don't have admin privileges.")
        return
    
    tasks = get_all_tasks()
    
    if not tasks:
        await update.message.reply_text("ℹ️ No tasks created yet.")
        return
    
    tasks_text = "📋 *All Tasks:*\n\n"
    for task in tasks:
        status = "✅ Assigned" if task["assigned_to"] else "⏳ Pending"
        assigned_to = f"👤 Assigned to: {task['assigned_to']}" if task["assigned_to"] else ""
        
        tasks_text += (
            f"*Task ID:* {task['id']}\n"
            f"📍 *Address:* {task['address']}\n"
            f"📆 *Date:* {task['date']}\n"
            f"🕒 *Time:* {task['time']}\n"
            f"📄 *Description:* {task['description']}\n"
            f"🔄 *Status:* {status}\n"
            f"{assigned_to}\n\n"
        )
    
    # Split message if it's too long
    if len(tasks_text) > 4000:
        task_chunks = []
        current_chunk = "📋 *All Tasks:*\n\n"
        
        for task in tasks:
            status = "✅ Assigned" if task["assigned_to"] else "⏳ Pending"
            assigned_to = f"👤 Assigned to: {task['assigned_to']}" if task["assigned_to"] else ""
            
            task_text = (
                f"*Task ID:* {task['id']}\n"
                f"📍 *Address:* {task['address']}\n"
                f"📆 *Date:* {task['date']}\n"
                f"🕒 *Time:* {task['time']}\n"
                f"📄 *Description:* {task['description']}\n"
                f"🔄 *Status:* {status}\n"
                f"{assigned_to}\n\n"
            )
            
            if len(current_chunk) + len(task_text) > 4000:
                task_chunks.append(current_chunk)
                current_chunk = "📋 *All Tasks (continued):*\n\n" + task_text
            else:
                current_chunk += task_text
        
        task_chunks.append(current_chunk)
        
        for chunk in task_chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(tasks_text, parse_mode="Markdown")

# Admin: View worker stats command
async def view_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View performance stats for all workers."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id, ADMIN_IDS):
        await update.message.reply_text("⚠️ You don't have admin privileges.")
        return
    
    workers = get_all_workers()
    
    if not workers:
        await update.message.reply_text("ℹ️ No workers registered yet.")
        return
    
    stats_text = "📊 *Worker Performance Stats:*\n\n"
    for worker in workers:
        stats = get_worker_stats(worker["id"])
        stats_text += (
            f"👤 *{worker['username']}* (ID: {worker['id']})\n"
            f"✅ Tasks accepted: {stats['accepted']}\n"
            f"❌ Tasks declined: {stats['declined']}\n"
            f"📊 Acceptance rate: {stats['acceptance_rate']}%\n\n"
        )
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# Worker: Handle task acceptance
async def accept_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle worker accepting a task."""
    user_id = update.effective_user.id
    
    # Check if command has task_id argument
    if not context.args:
        await update.message.reply_text("⚠️ Please specify a task ID: /accept [task_id]")
        return
    
    try:
        task_id = int(context.args[0])
        task = get_task_by_id(task_id)
        
        if not task:
            await update.message.reply_text(f"⚠️ Task with ID {task_id} not found.")
            return
        
        if task["assigned_to"]:
            await update.message.reply_text("⚠️ This task has already been assigned to another worker.")
            return
        
        # Update task as accepted
        worker = get_worker_by_id(user_id)
        if not worker:
            await update.message.reply_text("⚠️ You're not registered as a worker.")
            return
        
        success = update_task_status(task_id, user_id, "accepted")
        
        if success:
            # Notify the worker
            await update.message.reply_text(
                f"✅ You've successfully accepted task #{task_id}!\n\n"
                f"📍 *Address:* {task['address']}\n"
                f"📆 *Date:* {task['date']}\n"
                f"🕒 *Time:* {task['time']}\n"
                f"📄 *Description:* {task['description']}",
                parse_mode="Markdown"
            )
            
            # Notify the admin
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"✅ Task #{task_id} has been accepted by {worker['username']} (ID: {user_id})!\n\n"
                            f"📍 *Address:* {task['address']}\n"
                            f"📆 *Date:* {task['date']}\n"
                            f"🕒 *Time:* {task['time']}",
                        ),
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass  # Ignore if notification fails
            
            # Notify other workers that the task is no longer available
            workers = get_all_workers()
            for w in workers:
                if w["id"] != user_id:
                    try:
                        await context.bot.send_message(
                            chat_id=w["id"],
                            text=f"ℹ️ Task #{task_id} has been assigned to another worker."
                        )
                    except Exception:
                        pass  # Ignore if notification fails
        else:
            await update.message.reply_text("⚠️ Failed to accept the task. It may have been assigned already.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid task ID. Please provide a valid numerical ID.")

# Worker: Handle task decline
async def decline_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle worker declining a task."""
    user_id = update.effective_user.id
    
    # Check if command has task_id argument
    if not context.args:
        await update.message.reply_text("⚠️ Please specify a task ID: /decline [task_id]")
        return
    
    try:
        task_id = int(context.args[0])
        task = get_task_by_id(task_id)
        
        if not task:
            await update.message.reply_text(f"⚠️ Task with ID {task_id} not found.")
            return
        
        if task["assigned_to"]:
            await update.message.reply_text("⚠️ This task has already been assigned to another worker.")
            return
        
        # Update task as declined for this worker
        worker = get_worker_by_id(user_id)
        if not worker:
            await update.message.reply_text("⚠️ You're not registered as a worker.")
            return
        
        success = update_task_status(task_id, user_id, "declined")
        
        if success:
            await update.message.reply_text(f"✓ You've declined task #{task_id}.")
            
            # Notify the admin
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"ℹ️ Task #{task_id} has been declined by {worker['username']} (ID: {user_id})."
                    )
                except Exception:
                    pass  # Ignore if notification fails
        else:
            await update.message.reply_text("⚠️ Failed to decline the task.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid task ID. Please provide a valid numerical ID.")

# Worker: View assigned tasks
async def my_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View tasks assigned to the worker."""
    user_id = update.effective_user.id
    
    worker = get_worker_by_id(user_id)
    if not worker:
        await update.message.reply_text("⚠️ You're not registered as a worker.")
        return
    
    # Get all tasks assigned to this worker
    tasks = get_all_tasks()
    assigned_tasks = [task for task in tasks if task["assigned_to"] == user_id]
    
    if not assigned_tasks:
        await update.message.reply_text("ℹ️ You have no assigned tasks.")
        return
    
    tasks_text = "📋 *Your Assigned Tasks:*\n\n"
    for task in assigned_tasks:
        tasks_text += (
            f"*Task ID:* {task['id']}\n"
            f"📍 *Address:* {task['address']}\n"
            f"📆 *Date:* {task['date']}\n"
            f"🕒 *Time:* {task['time']}\n"
            f"📄 *Description:* {task['description']}\n\n"
        )
    
    await update.message.reply_text(tasks_text, parse_mode="Markdown")

# Worker: View own stats
async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View worker's own performance stats."""
    user_id = update.effective_user.id
    
    worker = get_worker_by_id(user_id)
    if not worker:
        await update.message.reply_text("⚠️ You're not registered as a worker.")
        return
    
    stats = get_worker_stats(user_id)
    
    stats_text = (
        "📊 *Your Performance Stats:*\n\n"
        f"✅ Tasks accepted: {stats['accepted']}\n"
        f"❌ Tasks declined: {stats['declined']}\n"
        f"📊 Acceptance rate: {stats['acceptance_rate']}%"
    )
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# Handle button callbacks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks for accepting/declining tasks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    action = data[0]
    task_id = int(data[1])
    
    user_id = query.from_user.id
    worker = get_worker_by_id(user_id)
    
    if not worker:
        await query.edit_message_text(
            text="⚠️ You're not registered as a worker.",
            reply_markup=None
        )
        return
    
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text(
            text=f"⚠️ Task with ID {task_id} not found.",
            reply_markup=None
        )
        return
    
    if task["assigned_to"]:
        await query.edit_message_text(
            text="⚠️ This task has already been assigned to another worker.",
            reply_markup=None
        )
        return
    
    if action == "accept":
        success = update_task_status(task_id, user_id, "accepted")
        
        if success:
            await query.edit_message_text(
                text=(
                    f"✅ You've successfully accepted task #{task_id}!\n\n"
                    f"📍 *Address:* {task['address']}\n"
                    f"📆 *Date:* {task['date']}\n"
                    f"🕒 *Time:* {task['time']}\n"
                    f"📄 *Description:* {task['description']}"
                ),
                parse_mode="Markdown",
                reply_markup=None
            )
            
            # Notify the admin
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"✅ Task #{task_id} has been accepted by {worker['username']} (ID: {user_id})!\n\n"
                            f"📍 *Address:* {task['address']}\n"
                            f"📆 *Date:* {task['date']}\n"
                            f"🕒 *Time:* {task['time']}"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass  # Ignore if notification fails
            
            # Notify other workers that the task is no longer available
            workers = get_all_workers()
            for w in workers:
                if w["id"] != user_id:
                    try:
                        await context.bot.send_message(
                            chat_id=w["id"],
                            text=f"ℹ️ Task #{task_id} has been assigned to another worker."
                        )
                    except Exception:
                        pass  # Ignore if notification fails
        else:
            await query.edit_message_text(
                text="⚠️ Failed to accept the task. It may have been assigned already.",
                reply_markup=None
            )
    
    elif action == "decline":
        success = update_task_status(task_id, user_id, "declined")
        
        if success:
            await query.edit_message_text(
                text=f"✓ You've declined task #{task_id}.",
                reply_markup=None
            )
            
            # Notify the admin
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"ℹ️ Task #{task_id} has been declined by {worker['username']} (ID: {user_id})."
                    )
                except Exception:
                    pass  # Ignore if notification fails
        else:
            await query.edit_message_text(
                text="⚠️ Failed to decline the task.",
                reply_markup=None
            )

def start_bot():
    """Function to start the bot - can be imported and used by other modules."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Worker command handlers
    application.add_handler(CommandHandler("accept", accept_task))
    application.add_handler(CommandHandler("decline", decline_task))
    application.add_handler(CommandHandler("my_tasks", my_tasks_command))
    application.add_handler(CommandHandler("my_stats", my_stats_command))
    
    # Admin command handlers
    application.add_handler(CommandHandler("list_workers", list_workers_command))
    application.add_handler(CommandHandler("list_tasks", list_tasks_command))
    application.add_handler(CommandHandler("view_stats", view_stats_command))
    application.add_handler(CommandHandler("remove_worker", remove_worker_command))
    
    # Conversation handlers
    # Create task conversation
    create_task_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("create_task", create_task_start)],
        states={
            TASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_address)],
            TASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_date)],
            TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_time)],
            TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_description)],
        },
        fallbacks=[CommandHandler("cancel", cancel_task_creation)],
    )
    application.add_handler(create_task_conv_handler)
    
    # Add worker conversation
    add_worker_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_worker", add_worker_start)],
        states={
            WORKER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_worker_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_worker)],
    )
    application.add_handler(add_worker_conv_handler)
    
    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the Bot
    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    return application

def main():
    """Start the bot (for direct script execution)."""
    start_bot()

if __name__ == "__main__":
    main()
