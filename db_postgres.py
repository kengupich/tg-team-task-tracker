"""
PostgreSQL database connection handler with connection pooling.
Uses connection pool to reuse connections instead of creating new ones for every query.
"""
import os
import logging
from typing import Optional
from psycopg2 import connect, extensions
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class PostgreSQLConnection:
    """PostgreSQL database connection handler with connection pooling."""
    
    def __init__(self):
        self.connection_string = self._get_connection_string()
        self._validated = False
        self.pool = None  # Connection pool will be created on first use
        logger.info("PostgreSQL connection handler initialized with pooling (lazy validation)")
    
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
    
    def _init_pool(self):
        """Initialize connection pool on first use."""
        if self.pool is None:
            try:
                # Create pool with 5-20 connections
                # minconn=5: keep 5 connections always open
                # maxconn=20: allow up to 20 concurrent connections
                self.pool = SimpleConnectionPool(5, 20, self.connection_string)
                logger.info("✅ PostgreSQL connection pool initialized (5-20 connections)")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise
    
    def get_connection(self):
        """Get database connection from pool (or create new if needed)."""
        import time
        try:
            # Validate connection on first use
            if not self._validated:
                self._validate_connection()
                self._validated = True
            
            # Initialize pool on first use
            if self.pool is None:
                self._init_pool()
            
            start = time.time()
            # Get connection from pool (reuses existing connections)
            conn = self.pool.getconn()
            elapsed = time.time() - start
            
            if elapsed > 0.5:
                logger.warning(f"🐌 DB POOL GET slow: {elapsed:.3f}s")
            elif elapsed > 0.1:
                logger.debug(f"🐌 DB POOL GET: {elapsed:.3f}s (reusing connection)")
            
            # Use AUTOCOMMIT mode for auto-commit
            conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn):
        """Return connection back to pool for reuse."""
        try:
            if self.pool and conn:
                self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
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
