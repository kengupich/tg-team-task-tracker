"""
Configuration module for the Telegram Task Management Bot.
Manages debug/production modes and application settings.
"""
import os
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Environment(Enum):
    """Application environment modes."""
    DEBUG = "debug"
    PRODUCTION = "production"


class Config:
    """Application configuration."""
    
    # Environment settings
    ENVIRONMENT = os.getenv("ENVIRONMENT", "debug").lower()
    DEBUG = ENVIRONMENT == "debug"
    PRODUCTION = ENVIRONMENT == "production"
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    SUPER_ADMIN_ID = os.getenv("SUPER_ADMIN_ID")
    
    # Database settings (PostgreSQL only)
    DATABASE_URL = os.getenv("DATABASE_URL")
    LOCAL_DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", 
                                   "postgresql://postgres:password@localhost:5432/task_management")
    
    # Bot settings
    USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    RAILWAY_URL = os.getenv("RAILWAY_URL")
    PORT = int(os.getenv("PORT", 5000))
    
    # Polling settings (for DEBUG mode)
    POLLING_TIMEOUT = 30  # seconds
    POLLING_INTERVAL = 0.5  # seconds between polling checks
    
    # Task check settings
    TASKS_CHECK_TIME = os.getenv("TASKS_CHECK_TIME", "20:00")
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Kyiv")
    
    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if PRODUCTION else "DEBUG")
    
    @classmethod
    def validate(cls):
        """Validate required configuration settings."""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is not set")
        
        if not cls.SUPER_ADMIN_ID:
            errors.append("SUPER_ADMIN_ID is not set")
        
        if cls.USE_WEBHOOK and not cls.RAILWAY_URL:
            errors.append("RAILWAY_URL is required when USE_WEBHOOK is True")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True
    
    @classmethod
    def get_info(cls):
        """Get configuration information."""
        info = {
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
            "production": cls.PRODUCTION,
            "use_webhook": cls.USE_WEBHOOK,
            "database": "PostgreSQL (Railway)" if cls.DATABASE_URL else "PostgreSQL (Local)",
            "port": cls.PORT,
            "timezone": cls.TIMEZONE,
        }
        return info


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Warning:\n{e}")
    print("\n💡 Please check your .env file or environment variables")
