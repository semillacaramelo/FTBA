
"""
Error handling utilities for the multi-agent forex trading system.
"""

import logging
import traceback
from enum import Enum
from typing import Dict, Any, Optional, Callable
from datetime import datetime

# Define error severity levels
class ErrorSeverity(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3

class ErrorHandler:
    """Centralized error handling for the system"""
    
    def __init__(self):
        self.logger = logging.getLogger("error_handler")
        self.error_callbacks = {}  # severity -> list of callback functions
        self.error_history = []    # Store recent errors
        self.max_history = 100     # Maximum number of errors to keep in history
    
    def register_callback(self, severity: ErrorSeverity, 
                          callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for a specific error severity"""
        if severity not in self.error_callbacks:
            self.error_callbacks[severity] = []
        self.error_callbacks[severity].append(callback)
    
    def handle_error(self, error: Exception, source: str, 
                     severity: ErrorSeverity = ErrorSeverity.ERROR,
                     context: Optional[Dict[str, Any]] = None) -> None:
        """Handle an error with the specified severity and context"""
        error_info = {
            "timestamp": datetime.utcnow(),
            "source": source,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "severity": severity,
            "context": context or {}
        }
        
        # Log the error
        log_method = getattr(self.logger, severity.name.lower())
        log_method(f"Error in {source}: {error} | Context: {context}")
        
        # Store in history
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Trigger callbacks
        if severity in self.error_callbacks:
            for callback in self.error_callbacks[severity]:
                try:
                    callback(error_info)
                except Exception as cb_error:
                    self.logger.error(f"Error in error callback: {cb_error}")

# Singleton instance
error_handler = ErrorHandler()

def handle_error(error: Exception, source: str, 
                severity: ErrorSeverity = ErrorSeverity.ERROR,
                context: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function to handle an error using the singleton handler"""
    error_handler.handle_error(error, source, severity, context)
