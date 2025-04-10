import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Database settings
DB_FILE = "task_manager.db"

# Application settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
