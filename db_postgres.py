"""
PostgreSQL database connection handler.
All database operations use PostgreSQL exclusively.
"""
import os
import logging
from typing import Optional
from psycopg2 import connect, extensions
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class PostgreSQLConnection:
    """PostgreSQL database connection handler."""
    
    def __init__(self):
        self.connection_string = self._get_connection_string()
        self._validated = False
        logger.info("PostgreSQL connection handler initialized (lazy validation)")
    
    def _get_connection_string(self) -> str:
        """Get PostgreSQL connection string from environment."""
        database_url = os.getenv("DATABASE_URL", "").strip()
        
        # Detect if running on Railway/production
        is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("PORT") is not None
        is_production = os.getenv("ENVIRONMENT", "debug").lower() == "production"
        
        if not database_url:
            if is_railway or is_production:
                # On Railway/production, DATABASE_URL is required
                error_msg = (
                    "DATABASE_URL environment variable is not set. "
                    "On Railway, ensure PostgreSQL service is connected and "
                    "DATABASE_URL is available in Variables."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                # Use local PostgreSQL if DATABASE_URL not set (local development)
                database_url = os.getenv(
                    "LOCAL_DATABASE_URL",
                    "postgresql://postgres:password@localhost:5432/task_management"
                )
                logger.warning(f"DATABASE_URL not set, using LOCAL_DATABASE_URL: {database_url[:50]}...")
        else:
            logger.info(f"Using DATABASE_URL from environment (production: {is_production})")
        
        # Convert postgres:// to postgresql:// if needed (Railway compatibility)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        return database_url
    
    def _validate_connection(self):
        """Validate that we can connect to PostgreSQL."""
        try:
            conn = connect(self.connection_string)
            conn.close()
            logger.info("PostgreSQL connection validated")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def get_connection(self):
        """Get new database connection."""
        try:
            # Validate connection on first use
            if not self._validated:
                self._validate_connection()
                self._validated = True
            
            conn = connect(self.connection_string)
            # Use AUTOCOMMIT mode for auto-commit
            conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection: {e}")
            raise
    
    def get_connection_with_dict_cursor(self):
        """Get connection with dictionary cursor (returns rows as dicts)."""
        try:
            conn = connect(self.connection_string)
            conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return conn, RealDictCursor
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection: {e}")
            raise


# Global connection instance
_db_connection: Optional[PostgreSQLConnection] = None


def get_db_connection() -> PostgreSQLConnection:
    """Get or create database connection handler."""
    global _db_connection
    if _db_connection is None:
        _db_connection = PostgreSQLConnection()
    return _db_connection


def init_connection():
    """Initialize database connection on startup."""
    conn = get_db_connection()
    logger.info("PostgreSQL database connection ready")
    return conn
