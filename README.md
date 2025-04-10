# Team Task Management Telegram Bot

A Python-based Telegram bot for team task management with admin controls, worker assignment, and performance tracking.

## Features

- Admin can create tasks with details (address, date, time)
- Task broadcasting to all registered workers
- Workers can accept/decline tasks
- First worker to accept gets assigned the task
- Performance tracking system
- Admin panel with worker management and statistics
- Task listing and filtering

## Requirements

- Python 3.7+
- python-telegram-bot library
- python-dotenv
- SQLite3 (included in Python)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/team-task-bot.git
   cd team-task-bot
   ```

2. Install the required dependencies:
   ```
   pip install python-telegram-bot python-dotenv
   ```

3. Create a `.env` file based on the provided `.env.example`:
   ```
   cp .env.example .env
   ```

4. Edit the `.env` file and add your Telegram Bot Token:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ```

## Getting a Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Start a chat with BotFather and send the command `/newbot`
3. Follow the instructions to create a new bot
4. Once created, BotFather will provide you with a token
5. Copy this token to your `.env` file

## Running the Bot

Start the bot with:

