"""
Performance monitoring utilities for debugging slow requests.
Logs timing information for database and handler operations.
"""
import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def log_timing(operation_name: str):
    """
    Decorator to log execution time of async functions.
    
    Usage:
        @log_timing("super_manage_groups")
        async def super_manage_groups(update, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                
                if elapsed > 0.5:  # Log if > 500ms
                    logger.warning(f"⏱️  SLOW: {operation_name} took {elapsed:.2f}s")
                elif elapsed > 0.1:  # Debug if > 100ms
                    logger.debug(f"⏱️  {operation_name} took {elapsed:.2f}s")
                
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"❌ {operation_name} failed after {elapsed:.2f}s: {e}")
                raise
        
        return async_wrapper
    return decorator


def log_db_timing(func: Callable) -> Callable:
    """
    Decorator to log execution time of database operations.
    
    Usage:
        @log_db_timing
        def get_user_groups(user_id):
            ...
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            
            if elapsed > 0.5:  # Log if > 500ms
                logger.warning(f"🐌 SLOW DB: {func.__name__} took {elapsed:.2f}s")
            elif elapsed > 0.1:  # Debug if > 100ms
                logger.debug(f"🐌 DB: {func.__name__} took {elapsed:.3f}s")
            
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"❌ DB ERROR: {func.__name__} failed after {elapsed:.2f}s: {e}")
            raise
    
    return wrapper
