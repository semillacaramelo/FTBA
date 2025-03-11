"""
Custom logging handlers for colored console output.
This module enhances the standard Python logging with colors and icons.
"""
import logging
import sys
from typing import Dict, Any, Optional

from system.console_utils import Colors, Icons, MessageType

# Define message format dictionary for logger
MESSAGE_FORMATS = {
    MessageType.SUCCESS: {
        "icon": Icons.SUCCESS,
        "color": Colors.GREEN,
    },
    MessageType.ERROR: {
        "icon": Icons.ERROR,
        "color": Colors.RED,
    },
    MessageType.WARNING: {
        "icon": Icons.WARNING,
        "color": Colors.YELLOW,
    },
    MessageType.INFO: {
        "icon": Icons.INFO,
        "color": Colors.BLUE,
    },
    MessageType.DEBUG: {
        "icon": Icons.INFO,
        "color": Colors.DIM,
    },
    MessageType.TRADE_SUCCESS: {
        "icon": Icons.PROFIT,
        "color": Colors.BRIGHT_GREEN,
    },
    MessageType.TRADE_FAILURE: {
        "icon": Icons.LOSS,
        "color": Colors.BRIGHT_RED,
    },
    MessageType.TRADE_PENDING: {
        "icon": Icons.PENDING,
        "color": Colors.BRIGHT_YELLOW,
    },
    MessageType.SYSTEM: {
        "icon": Icons.SETTINGS,
        "color": Colors.CYAN,
    },
    MessageType.DATA: {
        "icon": Icons.CHART,
        "color": Colors.MAGENTA,
    },
    MessageType.SIGNAL: {
        "icon": Icons.SIGNAL,
        "color": Colors.BRIGHT_BLUE,
    },
}

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors and icons to log messages"""
    
    # Mapping log levels to message types and colors
    LEVEL_FORMATS = {
        logging.DEBUG: MessageType.DEBUG,
        logging.INFO: MessageType.INFO,
        logging.WARNING: MessageType.WARNING,
        logging.ERROR: MessageType.ERROR,
        logging.CRITICAL: MessageType.ERROR
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """
        Initialize the formatter
        
        Args:
            fmt: Format string
            datefmt: Date format string
        """
        super().__init__(fmt, datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with colors and icons
        
        Args:
            record: Log record to format
            
        Returns:
            str: Formatted log message
        """
        # Save the original format and message
        original_format = self._style._fmt
        original_msg = record.msg
        
        try:
            # Get the message type based on log level
            msg_type = self.LEVEL_FORMATS.get(record.levelno, MessageType.INFO)
            
            # Check for special keywords in the module name to customize the format
            if hasattr(record, 'name'):
                if 'trade_execution' in record.name:
                    if isinstance(original_msg, str) and ('Error' in original_msg or 'error' in original_msg or 'failed' in original_msg):
                        msg_type = MessageType.TRADE_FAILURE
                    elif isinstance(original_msg, str) and ('success' in original_msg or 'executed' in original_msg or 'completed' in original_msg):
                        msg_type = MessageType.TRADE_SUCCESS
                    else:
                        msg_type = MessageType.TRADE_PENDING
                elif 'technical_analysis' in record.name or 'fundamental_analysis' in record.name:
                    msg_type = MessageType.SIGNAL
                elif 'system' in record.name:
                    msg_type = MessageType.SYSTEM
                elif 'data' in record.name or 'market' in record.name:
                    msg_type = MessageType.DATA
            
            # Get message format info
            format_data = MESSAGE_FORMATS.get(msg_type, {"icon": "", "color": Colors.RESET})
            
            # Apply simple formatting directly without calling format_message
            # This avoids potential issues with the supports_color function
            if isinstance(record.msg, str):
                icon = format_data.get('icon', '')
                color = format_data.get('color', '')
                record.msg = f"{icon} {color}{record.msg}{Colors.RESET}"
            
        except Exception:
            # In case of any error, restore the original message
            record.msg = original_msg
        
        # Call the original formatter
        result = super().format(record)
        
        # Restore the original format and message
        self._style._fmt = original_format
        
        return result

class ColoredStreamHandler(logging.StreamHandler):
    """Stream handler that outputs colored logs to the console"""
    
    def __init__(self, stream=None):
        """
        Initialize the handler
        
        Args:
            stream: Output stream (defaults to sys.stderr)
        """
        super().__init__(stream)
        self.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

def setup_colored_logging(level=logging.INFO):
    """
    Set up colored logging for the application
    
    Args:
        level: Logging level to use
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our custom handler
    handler = ColoredStreamHandler()
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(level)

def get_colored_logger(name: str) -> logging.Logger:
    """
    Get a logger with colored output
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: The configured logger
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add our custom handler if not already set up at the root
    parent_has_handler = False
    if logger.parent and hasattr(logger.parent, 'handlers'):
        parent_has_handler = any(isinstance(h, ColoredStreamHandler) for h in logger.parent.handlers)
    
    if not parent_has_handler:
        handler = ColoredStreamHandler()
        logger.addHandler(handler)
    
    return logger