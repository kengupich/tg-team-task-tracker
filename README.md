# Team Task Management Telegram Bot

A Telegram bot for team task management with admin controls, worker assignment, and performance tracking. The system includes a web dashboard for monitoring tasks and worker performance.

## Features

- **Admin Controls**:
  - Create tasks with detailed information (address, date, time, description)
  - View all registered workers
  - Add or remove workers
  - View worker performance statistics

- **Worker Features**:
  - Receive notifications about new tasks
  - Accept or decline tasks (using inline buttons or commands)
  - View assigned tasks
  - View personal performance stats

- **Task Management**:
  - First worker to accept a task gets assigned
  - Tasks are stored in a SQLite database
  - Worker performance tracking
  - Web dashboard to visualize tasks and statistics

## Setup Instructions

### Prerequisites

- Python 3.6+
- pip (Python package manager)

### Installation

1. Clone this repository or download the files

2. Install required dependencies:
   ```
   pip install python-telegram-bot python-dotenv flask gunicorn
   ```

3. Configure your environment:
   - Create a `.env` file in the project root (use `.env.example` as a template)
   - Add your Telegram Bot Token (get from @BotFather on Telegram)
   - Add your Telegram user ID to the ADMIN_IDS list to gain admin privileges

4. Run the bot:
   ```
   python bot.py
   ```

5. Run the web dashboard (optional):
   ```
   python main.py
   ```

## Bot Commands

### Admin Commands
- `/start` - Get started with the bot
- `/help` - Show available commands
- `/create_task` - Create a new task
- `/add_worker` - Register a new worker
- `/remove_worker` - Unregister a worker
- `/list_workers` - View all registered workers
- `/list_tasks` - View all tasks
- `/view_stats` - View worker performance stats

### Worker Commands
- `/start` - Get started with the bot
- `/help` - Show available commands
- `/accept` - Accept a task (followed by task ID)
- `/decline` - Decline a task (followed by task ID)
- `/my_tasks` - View your assigned tasks
- `/my_stats` - View your performance stats

## Project Structure

- `bot.py` - Main Telegram bot implementation
- `database.py` - Database operations and task management
- `utils.py` - Helper functions
- `main.py` - Web dashboard for the bot
- `templates/` - HTML templates for the web dashboard
- `.env.example` - Template for the environment variables
- `task_management.db` - SQLite database (created automatically)

## Customization

You can customize the bot by modifying the following:
1. Edit `database.py` to change the database structure or add more fields
2. Modify `templates/index.html` to enhance the web dashboard
3. Add additional commands in `bot.py`
   