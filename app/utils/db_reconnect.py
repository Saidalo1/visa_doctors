import logging
import time
import asyncio
import functools
from django.db import connections
from django.db.utils import OperationalError, InterfaceError

logger = logging.getLogger(__name__)


def with_db_reconnect(max_attempts=3, backoff_time=0.5):
    """
    Decorator to handle database connection issues by attempting to reconnect.
    
    Args:
        max_attempts: Maximum number of reconnection attempts
        backoff_time: Initial backoff time (will increase exponentially)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Проверка на наличие активной транзакции
            from django.db import transaction
            if not transaction.get_autocommit():
                logger.warning(f"Function {func.__name__} called inside transaction, skipping reconnect logic")
                return func(*args, **kwargs)
                
            attempt = 0
            current_backoff = backoff_time
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, InterfaceError) as e:
                    # Фильтруем по типичным ошибкам соединения
                    error_msg = str(e).lower()
                    conn_errors = [
                        'connection already closed', 'could not connect to server',
                        'connection refused', 'connection timed out', 'terminating connection',
                        'SSL connection has been closed unexpectedly'
                    ]
                    
                    if not any(err in error_msg for err in conn_errors):
                        logger.error(f"[{func.__name__}] Database error not related to connection, not retrying: {error_msg}")
                        raise
                        
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"[{func.__name__}] All {max_attempts} database reconnection attempts failed: {error_msg}")
                        raise
                    
                    # Close all database connections to force Django to reconnect
                    logger.warning(f"[{func.__name__}] Database connection error: {error_msg}. Reconnecting (attempt {attempt}/{max_attempts})")
                    for conn in connections.all():
                        try:
                            conn.close()
                            logger.debug(f"Closed connection: {conn.alias}")
                        except Exception as close_ex:
                            logger.warning(f"Error closing connection {conn.alias}: {str(close_ex)}")
                    
                    # Wait with exponential backoff
                    time.sleep(current_backoff)
                    current_backoff *= 2  # Exponential backoff
        
        return wrapper
    return decorator


def with_db_reconnect_async(max_attempts=3, backoff_time=0.5):
    """
    Decorator to handle database connection issues for async functions.
    
    Args:
        max_attempts: Maximum number of reconnection attempts
        backoff_time: Initial backoff time (will increase exponentially)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Проверка на наличие активной транзакции
            from django.db import transaction
            if not transaction.get_autocommit():
                logger.warning(f"Function {func.__name__} called inside transaction, skipping reconnect logic")
                return await func(*args, **kwargs)
                
            attempt = 0
            current_backoff = backoff_time
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, InterfaceError) as e:
                    # Фильтруем по типичным ошибкам соединения
                    error_msg = str(e).lower()
                    conn_errors = [
                        'connection already closed', 'could not connect to server',
                        'connection refused', 'connection timed out', 'terminating connection',
                        'SSL connection has been closed unexpectedly'
                    ]
                    
                    if not any(err in error_msg for err in conn_errors):
                        logger.error(f"[{func.__name__}] Database error not related to connection, not retrying: {error_msg}")
                        raise
                        
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"[{func.__name__}] All {max_attempts} database reconnection attempts failed: {error_msg}")
                        raise
                    
                    # Close all database connections to force Django to reconnect
                    logger.warning(f"[{func.__name__}] Database connection error: {error_msg}. Reconnecting (attempt {attempt}/{max_attempts})")
                    for conn in connections.all():
                        try:
                            conn.close()
                            logger.debug(f"Closed connection: {conn.alias}")
                        except Exception as close_ex:
                            logger.warning(f"Error closing connection {conn.alias}: {str(close_ex)}")
                    
                    # Wait with exponential backoff
                    await asyncio.sleep(current_backoff)
                    current_backoff *= 2  # Exponential backoff
        
        return wrapper
    return decorator
