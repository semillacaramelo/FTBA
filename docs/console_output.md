# Console Output System

This document describes the enhanced console output system used in the FTBA application.

## Overview

The FTBA system features a rich console output system that uses colors and icons to make monitoring the application easier and more intuitive. This system helps quickly identify different types of messages and their importance.

## Features

- **Color Coding**: Different message types are displayed in distinct colors
- **Informative Icons**: Each message type has a relevant icon for visual identification
- **Structured Formatting**: Consistent layout makes information easy to scan
- **Status Indicators**: Special indicators for important status updates
- **Progress Visualization**: Progress bars for long-running operations

## Message Types

The system supports the following message types:

| Type | Icon | Color | Description |
|------|------|-------|-------------|
| Success | ✅ | Green | Successful operations |
| Error | ❌ | Red | Errors and failures |
| Warning | ⚠️ | Yellow | Warnings and cautions |
| Info | ℹ️ | Blue | General information |
| Debug | 🔍 | Gray | Detailed debug information |
| Trade Success | 📈 | Bright Green | Successful trades |
| Trade Failure | 📉 | Bright Red | Failed trades |
| Trade Pending | ⏳ | Bright Yellow | Pending trade operations |
| System | ⚙️ | Magenta | System operations |
| Data | 📊 | Cyan | Data updates and analysis |
| Signal | 📶 | Bright Blue | Trading signals generated |

## Example Output

Below is an example of how different message types appear in the console:

```
ℹ️ [INFO] System starting up...
📊 [DATA] Loading market data for EUR/USD, GBP/USD, USD/JPY
⚙️ [SYSTEM] Initializing agents: technical_analysis, fundamental_analysis, risk_management, strategy_optimization, trade_execution
✅ [SUCCESS] All agents initialized successfully
📶 [SIGNAL] Technical signal generated: EUR/USD, LONG, confidence=0.82
📶 [SIGNAL] Technical signal generated: GBP/USD, SHORT, confidence=0.67
⏳ [TRADE PENDING] Processing trade proposal for EUR/USD
✅ [TRADE SUCCESS] Executed EUR/USD LONG @ 1.0865, size=0.01
⚠️ [WARNING] Market volatility increased above threshold (25%)
❌ [ERROR] Failed to connect to price feed: Connection timeout
```

## Implementation Details

The console output system is implemented in the following files:

- `system/console_utils.py`: Core formatting functions and constants
- `system/colored_logger.py`: Integration with Python's logging system

### Colors Class

The `Colors` class in `console_utils.py` defines ANSI color codes:

```python
class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Additional colors and background colors...
```

### Icons Class

The `Icons` class defines Unicode icons for each message type:

```python
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
    # Additional icons...
```

### MessageType Enum

The `MessageType` enum defines standardized message types:

```python
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
```

### Formatting Functions

Several formatting functions apply the appropriate colors and icons:

```python
def format_message(message: str, msg_type: MessageType = MessageType.INFO, bold: bool = False,
                 additional_data: Optional[Dict[str, Any]] = None) -> str:
    """Format a message with color and icon"""
    # Implementation...

def print_message(message: str, msg_type: MessageType = MessageType.INFO, bold: bool = False,
                additional_data: Optional[Dict[str, Any]] = None) -> None:
    """Print a formatted message to the console"""
    # Implementation...
```

### Convenience Functions

For common message types, convenience functions are provided:

```python
def print_success(message: str, **kwargs) -> None:
    """Print a success message"""
    print_message(message, MessageType.SUCCESS, **kwargs)

def print_error(message: str, **kwargs) -> None:
    """Print an error message"""
    print_message(message, MessageType.ERROR, **kwargs)

def print_trade_success(message: str, **kwargs) -> None:
    """Print a trade success message"""
    print_message(message, MessageType.TRADE_SUCCESS, **kwargs)
```

### Progress and Status Visualization

Special formatting for progress bars and status updates:

```python
def progress_bar(progress: float, width: int = 40) -> str:
    """Generate a progress bar string"""
    # Implementation...

def print_status(status: str, message: str) -> None:
    """Print a status message with appropriate formatting"""
    # Implementation...
```

## Integration with Logging

The colored output is integrated with Python's logging system via `ColoredFormatter`:

```python
class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors and icons to log messages"""
    # Implementation...
```

This allows all log messages to be properly formatted with colors and icons.

## Usage in Code

To use the colored console output in your code:

```python
from system.console_utils import print_info, print_success, print_error, print_trade_success

# General information
print_info("Loading market data...")

# Success message
print_success("Market data loaded successfully")

# Error message
print_error("Failed to connect to API")

# Trade-specific messages
print_trade_success("EUR/USD LONG executed @ 1.0865")
```

## Terminal Compatibility

The colored output works in most modern terminals, including:

- Linux terminals (GNOME Terminal, Konsole, etc.)
- macOS Terminal and iTerm2
- Windows Terminal and PowerShell
- VSCode integrated terminal
- Various cloud-based terminal interfaces

In terminals that don't support ANSI colors, the system automatically falls back to plain text output without colors but keeps the informative icons.

## Color Scheme Design Principles

The color scheme follows these design principles:

1. **Semantic Consistency**: Colors consistently represent the same severity level (red = error, yellow = warning, etc.)
2. **Contrast**: Text maintains good contrast with background for readability
3. **Differentiation**: Each message type is visually distinct from others
4. **Restraint**: Colors are used purposefully, not excessively, to avoid visual fatigue

## Status Monitoring Integration

The console output system integrates with the status monitoring system to provide real-time updates on system processes:

```python
# Status monitoring integration
status_monitor.register_item("trade_execution", "Trade Execution Agent")
status_monitor.start_item("trade_execution")
print_info("Trade execution agent started")

# Later in the code
status_monitor.update_progress("trade_execution", 0.5, "Processing trade")
print_trade_pending("Processing trade for EUR/USD")

# On completion
status_monitor.complete_item("trade_execution", "Trade executed successfully")
print_trade_success("EUR/USD LONG executed @ 1.0865")
```