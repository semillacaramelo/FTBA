"""
Console utilities for enhancing command-line output with colors and icons.
This module provides consistent formatting for the CLUI application.
"""
import sys
from enum import Enum
from typing import Dict, Any, Optional

# ANSI Color Codes
class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

# Unicode Icons
class Icons:
    """Unicode icons for visual representation in terminal output"""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    PENDING = "⏳"
    TRADE = "🔄"
    PROFIT = "📈"
    LOSS = "📉"
    NEUTRAL = "➖"
    LONG = "⬆️"
    SHORT = "⬇️"
    STAR = "⭐"
    CHECK = "✓"
    CROSS = "✗"
    ARROW_RIGHT = "➡️"
    CLOCK = "🕒"
    LOCK = "🔒"
    UNLOCK = "🔓"
    SIGNAL = "📶"
    MONEY = "💰"
    CHART = "📊"
    CALENDAR = "📅"
    SETTINGS = "⚙️"

class MessageType(Enum):
    """Message types for consistent formatting"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    TRADE_SUCCESS = "trade_success"
    TRADE_FAILURE = "trade_failure"
    TRADE_PENDING = "trade_pending"
    SYSTEM = "system"
    DATA = "data"
    SIGNAL = "signal"

# Format configurations for different message types
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

def supports_color() -> bool:
    """
    Check if the terminal supports color output
    
    Returns:
        bool: True if color is supported
    """
    # For simplicity and to avoid issues, always return True in our application
    # This allows color to be handled by the terminal itself
    return True

def format_message(message: str, msg_type: MessageType = MessageType.INFO, bold: bool = False,
                 additional_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Format a message with color and icon
    
    Args:
        message: The message to format
        msg_type: The type of message (from MessageType enum)
        bold: Whether to make the message bold
        additional_data: Optional additional data to include in the output
        
    Returns:
        str: Formatted message string
    """
    if not supports_color():
        # If color is not supported, just return with the icon
        format_data = MESSAGE_FORMATS.get(msg_type, {"icon": ""})
        return f"{format_data['icon']} {message}"
    
    # Get format configuration for this message type
    format_data = MESSAGE_FORMATS.get(msg_type, {"icon": "", "color": Colors.RESET})
    
    # Build the formatted message
    formatted = f"{format_data['icon']} {format_data['color']}"
    if bold:
        formatted += Colors.BOLD
    
    formatted += f"{message}{Colors.RESET}"
    
    # Add additional data if provided
    if additional_data:
        data_str = " ".join([f"{k}={v}" for k, v in additional_data.items()])
        formatted += f" {Colors.DIM}({data_str}){Colors.RESET}"
    
    return formatted

def print_message(message: str, msg_type: MessageType = MessageType.INFO, bold: bool = False,
                additional_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Print a formatted message to the console
    
    Args:
        message: The message to print
        msg_type: The type of message (from MessageType enum)
        bold: Whether to make the message bold
        additional_data: Optional additional data to include in the output
    """
    print(format_message(message, msg_type, bold, additional_data))

def print_success(message: str, **kwargs) -> None:
    """Print a success message"""
    print_message(message, MessageType.SUCCESS, **kwargs)

def print_error(message: str, **kwargs) -> None:
    """Print an error message"""
    print_message(message, MessageType.ERROR, **kwargs)

def print_warning(message: str, **kwargs) -> None:
    """Print a warning message"""
    print_message(message, MessageType.WARNING, **kwargs)

def print_info(message: str, **kwargs) -> None:
    """Print an info message"""
    print_message(message, MessageType.INFO, **kwargs)

def print_debug(message: str, **kwargs) -> None:
    """Print a debug message"""
    print_message(message, MessageType.DEBUG, **kwargs)

def print_trade_success(message: str, **kwargs) -> None:
    """Print a trade success message"""
    print_message(message, MessageType.TRADE_SUCCESS, **kwargs)

def print_trade_failure(message: str, **kwargs) -> None:
    """Print a trade failure message"""
    print_message(message, MessageType.TRADE_FAILURE, **kwargs)

def print_trade_pending(message: str, **kwargs) -> None:
    """Print a trade pending message"""
    print_message(message, MessageType.TRADE_PENDING, **kwargs)

def print_system(message: str, **kwargs) -> None:
    """Print a system message"""
    print_message(message, MessageType.SYSTEM, **kwargs)

def print_data(message: str, **kwargs) -> None:
    """Print a data message"""
    print_message(message, MessageType.DATA, **kwargs)

def print_signal(message: str, **kwargs) -> None:
    """Print a signal message"""
    print_message(message, MessageType.SIGNAL, **kwargs)

def print_separator(character: str = "-", length: int = 80) -> None:
    """Print a separator line"""
    print(character * length)

def print_header(title: str, width: int = 80) -> None:
    """Print a header with centered title"""
    print_separator("=", width)
    padding = max(0, (width - len(title) - 2) // 2)
    print(f"{' ' * padding}{Colors.BOLD}{title}{Colors.RESET}{' ' * padding}")
    print_separator("=", width)

def print_trade_direction(direction: str) -> None:
    """Print trade direction with appropriate icon and color"""
    if direction.upper() in ["LONG", "BUY", "CALL"]:
        print(f"{Icons.LONG} {Colors.GREEN}LONG{Colors.RESET}")
    elif direction.upper() in ["SHORT", "SELL", "PUT"]:
        print(f"{Icons.SHORT} {Colors.RED}SHORT{Colors.RESET}")
    else:
        print(f"{Icons.NEUTRAL} {Colors.YELLOW}NEUTRAL{Colors.RESET}")

def print_profit_loss(value: float) -> None:
    """Print profit/loss with appropriate icon and color"""
    if value > 0:
        print(f"{Icons.PROFIT} {Colors.GREEN}+{value:.2f}{Colors.RESET}")
    elif value < 0:
        print(f"{Icons.LOSS} {Colors.RED}{value:.2f}{Colors.RESET}")
    else:
        print(f"{Icons.NEUTRAL} {Colors.YELLOW}{value:.2f}{Colors.RESET}")

def progress_bar(progress: float, width: int = 40) -> str:
    """
    Generate a progress bar string
    
    Args:
        progress: Progress value between 0 and 1
        width: Width of the progress bar in characters
        
    Returns:
        str: Progress bar string representation
    """
    filled_width = int(width * progress)
    bar = "█" * filled_width + "░" * (width - filled_width)
    return f"[{bar}] {progress*100:.1f}%"

def print_progress(progress: float, message: str = "", width: int = 40) -> None:
    """
    Print a progress bar
    
    Args:
        progress: Progress value between 0 and 1
        message: Optional message to display with the progress bar
        width: Width of the progress bar in characters
    """
    bar = progress_bar(progress, width)
    if message:
        print(f"{message}: {bar}")
    else:
        print(bar)

def print_status(status: str, message: str) -> None:
    """
    Print a status message with appropriate formatting
    
    Args:
        status: Status string (e.g., "RUNNING", "COMPLETED", "FAILED")
        message: Status message
    """
    if status.upper() in ["SUCCESS", "COMPLETED", "DONE"]:
        print_success(f"[{status.upper()}] {message}")
    elif status.upper() in ["ERROR", "FAILED", "FAILURE"]:
        print_error(f"[{status.upper()}] {message}")
    elif status.upper() in ["WARNING", "CAUTION"]:
        print_warning(f"[{status.upper()}] {message}")
    elif status.upper() in ["RUNNING", "PROCESSING", "WORKING"]:
        print_trade_pending(f"[{status.upper()}] {message}")
    else:
        print_info(f"[{status.upper()}] {message}")