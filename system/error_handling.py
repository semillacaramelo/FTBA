
import sys
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
import asyncio

class ErrorHandler:
    """Centralized error handling system for the application"""
    
    def __init__(self):
        self.logger = logging.getLogger("error_handler")
        self.error_counters = {}  # error_type -> count
        self.error_callbacks = {}  # error_type -> callback
        self.global_error_callback = None
    
    def register_callback(self, error_type: type, callback: Callable) -> None:
        """
        Register a callback for a specific error type
        
        Args:
            error_type: The type of error to handle
            callback: Function to call when this error occurs
        """
        self.error_callbacks[error_type] = callback
    
    def register_global_callback(self, callback: Callable) -> None:
        """
        Register a global error callback for any unhandled errors
        
        Args:
            callback: Function to call for any unhandled error
        """
        self.global_error_callback = callback
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle an error by logging it and possibly calling registered callbacks
        
        Args:
            error: The exception object
            context: Optional dictionary with context about where the error occurred
        """
        error_type = type(error)
        
        # Increment error counter
        if error_type not in self.error_counters:
            self.error_counters[error_type] = 0
        self.error_counters[error_type] += 1
        
        # Log the error
        error_message = str(error)
        self.logger.error(
            f"Error of type {error_type.__name__}: {error_message}",
            exc_info=True,
            extra={"context": context}
        )
        
        # Call specific error callback if registered
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error, context)
            except Exception as callback_error:
                self.logger.error(f"Error in error callback: {callback_error}")
        
        # Call global error callback if registered
        elif self.global_error_callback:
            try:
                self.global_error_callback(error, context)
            except Exception as callback_error:
                self.logger.error(f"Error in global error callback: {callback_error}")

# Global error handler instance
error_handler = ErrorHandler()

def handle_exceptions(func):
    """
    Decorator to handle exceptions in synchronous functions
    
    Args:
        func: The function to decorate
        
    Returns:
        Wrapped function with exception handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            error_handler.handle_error(e, context)
            raise  # Re-raise to allow higher-level handling
    return wrapper

def handle_async_exceptions(func):
    """
    Decorator to handle exceptions in asynchronous functions
    
    Args:
        func: The async function to decorate
        
    Returns:
        Wrapped async function with exception handling
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            # Don't handle cancellation, propagate it
            raise
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            error_handler.handle_error(e, context)
            raise  # Re-raise to allow higher-level handling
    return wrapper

def handle_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    """
    Global unhandled exception handler for sys.excepthook
    
    Args:
        exc_type: Exception type
        exc_value: Exception value
        exc_traceback: Exception traceback
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't override keyboard interrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    logger = logging.getLogger("uncaught_exceptions")
    logger.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    
    # Also handle using our error handler
    error_handler.handle_error(
        exc_value,
        {"traceback": "".join(traceback.format_tb(exc_traceback))}
    )

def setup_error_handling():
    """Configure global error handling for the application"""
    # Set up global exception hook
    sys.excepthook = handle_uncaught_exceptions
    
    # Set up asyncio exception handler
    loop = asyncio.get_event_loop()
    
    def handle_async_exception(loop, context):
        exception = context.get('exception')
        if exception:
            error_handler.handle_error(exception, context)
        else:
            msg = context.get('message')
            error_handler.handle_error(
                Exception(f"Async error without exception: {msg}"),
                context
            )
    
    loop.set_exception_handler(handle_async_exception)
    
    # Log that error handling is set up
    logging.getLogger("error_handling").info("Global error handling configured")
