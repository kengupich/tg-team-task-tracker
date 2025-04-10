import logging
import os
from datetime import datetime
from telegram._update import Update
from telegram.ext._application import Application
from telegram.ext._commandhandler import CommandHandler
from telegram.ext._conversationhandler import ConversationHandler
from telegram.ext._contexttypes import ContextTypes
from telegram.ext._messagehandler import MessageHandler
from telegram.ext._filters_base import filters
from dotenv import load_dotenv
from database import (
    get_connection,
    init_database,
    register_worker,
    list_all_workers,
    get_worker_stats,
    create_task_record,
    list_tasks,
    get_pending_tasks,
    assign_task,
    update_task_status,
    is_worker_registered,
    is_admin,
    register_admin,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for the conversation handler
TASK_ADDRESS, TASK_DATE, TASK_TIME, TASK_DESCRIPTION = range(4)
WORKER_NAME, WORKER_PHONE = range(2)

# Dictionary to store task creation data
task_data = {}

def start_bot():
    """Initialize and start the Telegram bot."""
    # Get token from environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file")
        return

    # Initialize database
    init_database()

    # Create application
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("register_admin", register_admin_command))
    application.add_handler(CommandHandler("add_worker", add_worker_command))
    application.add_handler(CommandHandler("view_stats", view_stats_command))
    application.add_handler(CommandHandler("list_tasks", list_tasks_command))
    application.add_handler(CommandHandler("accept", accept_task_command))
    application.add_handler(CommandHandler("decline", decline_task_command))

    # Add conversation handler for task creation
    task_creation_handler = ConversationHandler(
        entry_points=[CommandHandler("create_task", create_task_command)],
        states={
            TASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_address_callback)],
            TASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_date_callback)],
            TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_time_callback)],
            TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_description_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel_task_creation)],
    )
    application.add_handler(task_creation_handler)

    # Add conversation handler for worker registration
    worker_registration_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_worker_command)],
        states={
            WORKER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, worker_name_callback)],
            WORKER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, worker_phone_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel_worker_registration)],
    )
    application.add_handler(worker_registration_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Register admin if this is the first user (only for setup purposes)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM admins")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        register_admin(user_id, username)
        await update.message.reply_text(
            f"Welcome {username}! You have been registered as the first admin.\n\n"
            "Use /help to see available commands."
        )
    else:
        if is_admin(user_id):
            await update.message.reply_text(
                f"Welcome back, Admin {username}!\n\n"
                "Use /help to see available commands."
            )
        elif is_worker_registered(user_id):
            await update.message.reply_text(
                f"Welcome back, Worker {username}!\n\n"
                "Use /help to see available commands."
            )
        else:
            await update.message.reply_text(
                f"Welcome {username}! You are not registered yet.\n\n"
                "Workers use /register to register yourself.\n"
                "Admins need to be added by an existing admin."
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        # Admin help message
        help_text = (
            "Available admin commands:\n"
            "/create_task - Create a new task for workers\n"
            "/add_worker - Register a new worker (must provide Telegram user ID)\n"
            "/view_stats - View worker performance statistics\n"
            "/list_tasks - List all tasks\n"
            "/register_admin - Register another admin\n"
            "/help - Show this help message"
        )
    elif is_worker_registered(user_id):
        # Worker help message
        help_text = (
            "Available worker commands:\n"
            "/accept - Accept a task that was sent to you\n"
            "/decline - Decline a task that was sent to you\n"
            "/help - Show this help message"
        )
    else:
        # Unregistered user help message
        help_text = (
            "Welcome to the Team Task Management Bot!\n\n"
            "Workers use /register to register yourself.\n"
            "Admins need to be added by an existing admin."
        )
    
    await update.message.reply_text(help_text)

async def register_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /register_admin command to register another admin."""
    user_id = update.effective_user.id
    
    # Check if the user is already an admin
    if not is_admin(user_id):
        await update.message.reply_text("You must be an admin to register other admins.")
        return
    
    # Check if the command has the right format
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "Please provide the Telegram user ID of the new admin.\n"
            "Usage: /register_admin <user_id>"
        )
        return
    
    try:
        new_admin_id = int(context.args[0])
        register_admin(new_admin_id, f"Admin {new_admin_id}")
        await update.message.reply_text(f"Successfully registered user {new_admin_id} as an admin.")
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a valid numeric ID.")

async def create_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the task creation conversation."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can create tasks.")
        return ConversationHandler.END
    
    # Start new task creation
    task_data[user_id] = {}
    
    await update.message.reply_text(
        "Let's create a new task. First, send me the address where the task will take place."
    )
    return TASK_ADDRESS

async def task_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the task address step."""
    user_id = update.effective_user.id
    task_data[user_id]['address'] = update.message.text
    
    await update.message.reply_text(
        "Great! Now please send me the date for this task (format: YYYY-MM-DD)."
    )
    return TASK_DATE

async def task_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the task date step."""
    user_id = update.effective_user.id
    date_text = update.message.text
    
    try:
        # Validate date format
        datetime.strptime(date_text, "%Y-%m-%d")
        task_data[user_id]['date'] = date_text
        
        await update.message.reply_text(
            "Now, please send me the time for this task (format: HH:MM)."
        )
        return TASK_TIME
    except ValueError:
        await update.message.reply_text(
            "Invalid date format. Please use YYYY-MM-DD (e.g., 2023-11-15)."
        )
        return TASK_DATE

async def task_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the task time step."""
    user_id = update.effective_user.id
    time_text = update.message.text
    
    try:
        # Validate time format
        datetime.strptime(time_text, "%H:%M")
        task_data[user_id]['time'] = time_text
        
        await update.message.reply_text(
            "Finally, please provide a brief description of the task."
        )
        return TASK_DESCRIPTION
    except ValueError:
        await update.message.reply_text(
            "Invalid time format. Please use HH:MM (e.g., 14:30)."
        )
        return TASK_TIME

async def task_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the task description step and finalize task creation."""
    user_id = update.effective_user.id
    task_data[user_id]['description'] = update.message.text
    
    # Create the task in the database
    task = task_data[user_id]
    task_id = create_task_record(
        task['address'],
        task['date'],
        task['time'],
        task['description'],
        user_id  # Admin ID
    )
    
    await update.message.reply_text(
        f"Task created successfully!\n\n"
        f"Task ID: {task_id}\n"
        f"Address: {task['address']}\n"
        f"Date: {task['date']}\n"
        f"Time: {task['time']}\n"
        f"Description: {task['description']}"
    )
    
    # Broadcast task to all workers
    await broadcast_task_to_workers(context, task_id, task)
    
    # Clean up the task_data
    del task_data[user_id]
    
    return ConversationHandler.END

async def broadcast_task_to_workers(context, task_id, task):
    """Broadcast a new task to all registered workers."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM workers")
    workers = cursor.fetchall()
    conn.close()
    
    # Generate task message
    task_message = (
        f"🔔 *NEW TASK AVAILABLE* 🔔\n\n"
        f"*Task ID:* {task_id}\n"
        f"*Address:* {task['address']}\n"
        f"*Date:* {task['date']}\n"
        f"*Time:* {task['time']}\n"
        f"*Description:* {task['description']}\n\n"
        f"Reply with /accept to take this task or /decline to pass."
    )
    
    # Send message to all workers
    sent_count = 0
    for worker in workers:
        worker_id = worker[0]
        try:
            await context.bot.send_message(
                chat_id=worker_id,
                text=task_message,
                parse_mode="Markdown"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send message to worker {worker_id}: {e}")
    
    logger.info(f"Task broadcast to {sent_count} workers")

async def cancel_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the task creation process."""
    user_id = update.effective_user.id
    
    if user_id in task_data:
        del task_data[user_id]
    
    await update.message.reply_text("Task creation canceled.")
    return ConversationHandler.END

async def add_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /add_worker command to add a new worker."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can add workers.")
        return
    
    # Check if the command has the right format
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Please provide the Telegram user ID, name, and phone (optional).\n"
            "Usage: /add_worker <user_id> <name> [phone]"
        )
        return
    
    try:
        worker_id = int(context.args[0])
        name = context.args[1]
        phone = context.args[2] if len(context.args) > 2 else None
        
        if is_worker_registered(worker_id):
            await update.message.reply_text(f"Worker with ID {worker_id} is already registered.")
            return
        
        register_worker(worker_id, name, phone)
        await update.message.reply_text(f"Successfully registered worker: {name} (ID: {worker_id})")
        
        # Inform the worker they've been added
        try:
            await context.bot.send_message(
                chat_id=worker_id,
                text=f"You have been registered as a worker by an admin. Use /help to see available commands."
            )
        except Exception as e:
            await update.message.reply_text(
                f"Worker registered, but couldn't notify them: {e}\n"
                "Make sure the worker has started a conversation with the bot."
            )
    
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a valid numeric ID.")

async def register_worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the worker self-registration conversation."""
    user_id = update.effective_user.id
    
    if is_worker_registered(user_id):
        await update.message.reply_text("You are already registered as a worker.")
        return ConversationHandler.END
    
    await update.message.reply_text("Let's register you as a worker. What is your full name?")
    return WORKER_NAME

async def worker_name_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the worker name step."""
    user_id = update.effective_user.id
    name = update.message.text
    
    # Store the name in context
    context.user_data['worker_name'] = name
    
    await update.message.reply_text("Please provide your phone number.")
    return WORKER_PHONE

async def worker_phone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the worker phone step and complete registration."""
    user_id = update.effective_user.id
    phone = update.message.text
    name = context.user_data.get('worker_name', 'Unknown')
    
    register_worker(user_id, name, phone)
    
    await update.message.reply_text(
        f"Thank you, {name}! You have been registered as a worker.\n"
        "You will receive tasks from admins. Use /help to see available commands."
    )
    
    return ConversationHandler.END

async def cancel_worker_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the worker registration process."""
    await update.message.reply_text("Worker registration canceled.")
    return ConversationHandler.END

async def view_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /view_stats command to display worker statistics."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can view worker statistics.")
        return
    
    # Get worker statistics from database
    workers_stats = get_worker_stats()
    
    if not workers_stats:
        await update.message.reply_text("No worker statistics available.")
        return
    
    # Format the statistics message
    stats_message = "*Worker Performance Statistics*\n\n"
    for worker in workers_stats:
        stats_message += (
            f"*Worker:* {worker['name']}\n"
            f"*Tasks Accepted:* {worker['tasks_accepted']}\n"
            f"*Tasks Completed:* {worker['tasks_completed']}\n"
            f"*Tasks Declined:* {worker['tasks_declined']}\n"
            f"*Completion Rate:* {worker['completion_rate']}%\n\n"
        )
    
    await update.message.reply_text(stats_message, parse_mode="Markdown")

async def list_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /list_tasks command to list all tasks."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("Only admins can list all tasks.")
        return
    
    # Determine if any filters were provided
    status_filter = None
    if context.args and len(context.args) > 0:
        status_arg = context.args[0].lower()
        if status_arg in ["pending", "assigned", "completed", "declined"]:
            status_filter = status_arg
    
    # Get tasks from database
    tasks = list_tasks(status_filter)
    
    if not tasks:
        filter_text = f" with status '{status_filter}'" if status_filter else ""
        await update.message.reply_text(f"No tasks{filter_text} found.")
        return
    
    # Format the tasks list
    filter_text = f"({status_filter.upper()})" if status_filter else ""
    message = f"*Task List {filter_text}*\n\n"
    
    for task in tasks:
        status_text = task['status'].upper()
        worker_text = f"Assigned to: {task['worker_name']}" if task['worker_name'] else "Unassigned"
        
        message += (
            f"*Task ID:* {task['id']}\n"
            f"*Date & Time:* {task['date']} at {task['time']}\n"
            f"*Address:* {task['address']}\n"
            f"*Description:* {task['description']}\n"
            f"*Status:* {status_text}\n"
            f"*{worker_text}*\n\n"
        )
    
    # If message is too long, split it into chunks (Telegram has a 4096 character limit)
    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")

async def accept_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /accept command for workers to accept tasks."""
    user_id = update.effective_user.id
    
    if not is_worker_registered(user_id):
        await update.message.reply_text("You must be a registered worker to accept tasks.")
        return
    
    # Get pending tasks
    pending_tasks = get_pending_tasks()
    
    if not pending_tasks:
        await update.message.reply_text("There are no pending tasks available.")
        return
    
    # If there's a pending task, assign it to this worker
    latest_task = pending_tasks[0]  # Get the most recent pending task
    task_id = latest_task['id']
    
    # Try to assign the task to this worker
    if assign_task(task_id, user_id):
        # Success - notify the worker
        await update.message.reply_text(
            f"✅ You have been assigned task #{task_id}!\n\n"
            f"*Address:* {latest_task['address']}\n"
            f"*Date:* {latest_task['date']}\n"
            f"*Time:* {latest_task['time']}\n"
            f"*Description:* {latest_task['description']}\n",
            parse_mode="Markdown"
        )
        
        # Notify all admins
        await notify_admins_task_assignment(context, task_id, user_id, latest_task)
        
        # Notify other workers that the task is no longer available
        await notify_other_workers_task_taken(context, task_id, user_id)
    else:
        await update.message.reply_text(
            "This task has already been assigned to another worker. "
            "You'll be notified when new tasks are available."
        )

async def notify_admins_task_assignment(context, task_id, worker_id, task):
    """Notify all admins about task assignment."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get worker name
    cursor.execute("SELECT name FROM workers WHERE user_id = ?", (worker_id,))
    worker_result = cursor.fetchone()
    worker_name = worker_result[0] if worker_result else "Unknown worker"
    
    # Get all admins
    cursor.execute("SELECT user_id FROM admins")
    admins = cursor.fetchall()
    conn.close()
    
    notification = (
        f"🔵 *TASK ASSIGNMENT NOTIFICATION* 🔵\n\n"
        f"*Task #{task_id}* has been accepted by {worker_name}\n\n"
        f"*Task Details:*\n"
        f"Address: {task['address']}\n"
        f"Date: {task['date']} at {task['time']}\n"
        f"Description: {task['description']}"
    )
    
    for admin in admins:
        admin_id = admin[0]
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

async def notify_other_workers_task_taken(context, task_id, accepted_worker_id):
    """Notify other workers that a task has been taken."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM workers WHERE user_id != ?", (accepted_worker_id,))
    workers = cursor.fetchall()
    conn.close()
    
    notification = (
        f"Task #{task_id} has been assigned to another worker. "
        f"You'll be notified when new tasks are available."
    )
    
    for worker in workers:
        worker_id = worker[0]
        try:
            await context.bot.send_message(
                chat_id=worker_id,
                text=notification
            )
        except Exception as e:
            logger.error(f"Failed to notify worker {worker_id}: {e}")

async def decline_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /decline command for workers to decline tasks."""
    user_id = update.effective_user.id
    
    if not is_worker_registered(user_id):
        await update.message.reply_text("You must be a registered worker to decline tasks.")
        return
    
    # Get pending tasks
    pending_tasks = get_pending_tasks()
    
    if not pending_tasks:
        await update.message.reply_text("There are no pending tasks to decline.")
        return
    
    # Mark the worker's response as declined for the latest task
    latest_task = pending_tasks[0]
    task_id = latest_task['id']
    
    # Update the task status for this worker
    update_task_status(task_id, user_id, "declined")
    
    await update.message.reply_text(
        f"You have declined task #{task_id}. You'll be notified of future tasks."
    )
