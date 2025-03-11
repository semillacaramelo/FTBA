# Error Handling & Troubleshooting

This document describes the error handling framework in the FTBA system and provides troubleshooting guidance for common issues.

## Error Handling Framework

The FTBA system implements a comprehensive error handling framework to ensure that:

1. Errors are properly logged with detailed context
2. The system can recover gracefully from many types of failures
3. Critical errors trigger appropriate shutdown procedures
4. Users receive clear, actionable error messages

### Error Handler Classes

The main error handling is implemented in `system/error_handling.py`:

#### ErrorHandler Class

The `ErrorHandler` class provides centralized error handling services:

```python
class ErrorHandler:
    """Centralized error handling system for the application"""
    
    def __init__(self):
        self._error_callbacks = defaultdict(list)
        self._global_callbacks = []
        self._logger = logging.getLogger("error_handler")
        
    def register_callback(self, error_type: type, callback: Callable) -> None:
        """Register a callback for a specific error type"""
        
    def register_global_callback(self, callback: Callable) -> None:
        """Register a global error callback for any unhandled errors"""
        
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle an error by logging it and possibly calling registered callbacks"""
```

#### Decorators

Two decorators are provided for easy integration:

```python
@handle_exceptions
def some_function():
    # Function code that might raise exceptions
    
@handle_async_exceptions
async def some_async_function():
    # Async function code that might raise exceptions
```

### Global Exception Handling

The system also sets up global exception handlers:

```python
def handle_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    """Global unhandled exception handler for sys.excepthook"""
    
def setup_error_handling():
    """Configure global error handling for the application"""
    # Sets up sys.excepthook and asyncio exception handlers
```

## Common Error Types

The FTBA system defines several custom error types:

### API Errors

```python
class APIError(Exception):
    """Raised when an API request fails"""
    
class ResponseError(Exception):
    """Raised when an API response cannot be parsed or contains errors"""
```

### Configuration Errors

```python
class ConfigurationError(Exception):
    """Raised when there's an issue with the system configuration"""
    
class ValidationError(Exception):
    """Raised when validation fails for input data"""
```

### Connection Errors

```python
class ConnectionError(Exception):
    """Base class for connection-related errors"""
    
class ReconnectionFailedError(ConnectionError):
    """Raised when multiple reconnection attempts fail"""
```

### Agent Errors

```python
class AgentError(Exception):
    """Base class for agent-related errors"""
    
class AgentInitializationError(AgentError):
    """Raised when an agent fails to initialize"""
    
class MessageHandlingError(AgentError):
    """Raised when an agent cannot process a message"""
```

## Error Log Format

Errors are logged with detailed context to facilitate troubleshooting:

```
❌ [ERROR] Exception in module trade_execution_agent.py:
APIError: Failed to execute trade

Context:
  Operation: buy_contract
  Symbol: EUR/USD
  Direction: LONG
  Size: 0.01
  Price: 1.0865
  Attempt: 2/3

Traceback:
  File "system/agent.py", line 247, in _process_loop
    await self.process_cycle()
  File "agents/trade_execution_agent.py", line 189, in process_cycle
    result = await self._execute_trade(trade_proposal)
  File "agents/trade_execution_agent.py", line 245, in _execute_trade
    response = await self._api_client.buy_contract(proposal_id, price)
  File "system/deriv_api_client.py", line 189, in buy_contract
    return await self._execute_with_retry("buy_contract", self._api.buy, proposal_id, price)
  File "system/deriv_api_client.py", line 143, in _execute_with_retry
    raise APIError(f"Failed to {operation_name}")
```

## Troubleshooting Guide

### System Startup Issues

#### Configuration Problems

**Symptoms:**
- System exits immediately after startup
- Error logs show configuration validation errors

**Solutions:**
1. Verify your `config/settings.json` file is valid JSON
2. Check that all required fields are present
3. Ensure all field values are of the correct type
4. Compare against the example configuration in [Configuration Guide](configuration.md)

#### Agent Initialization Errors

**Symptoms:**
- System starts but one or more agents fail to initialize
- Error logs show `AgentInitializationError`

**Solutions:**
1. Check agent-specific configuration settings
2. Verify that required resources (files, directories) exist
3. Check for connection issues if the agent depends on external services

### API Connection Issues

#### Deriv API Connection Failures

**Symptoms:**
- Error logs show connection errors to Deriv API
- System retries connections but eventually fails

**Solutions:**
1. Verify your internet connection
2. Check `DERIV_APP_ID` and `DERIV_DEMO_API_TOKEN` environment variables
3. Ensure the Deriv API endpoint is correct
4. Check if the Deriv API is currently available
5. Verify your token has the correct permissions

#### Reconnection Issues

**Symptoms:**
- System initially connects to the API but later disconnects
- Reconnection attempts fail

**Solutions:**
1. Check for intermittent network issues
2. Verify the API session hasn't expired
3. Check for rate limiting or IP blocking by the API provider
4. Ensure the system clock is correctly synchronized

### Message Broker Issues

#### Message Delivery Failures

**Symptoms:**
- Agents don't receive expected messages
- Error logs show message queue issues

**Solutions:**
1. Check that agent subscriptions are correctly set up
2. Verify that message types match between sender and subscribers
3. Check for memory issues if message queues are growing too large

#### Message Processing Errors

**Symptoms:**
- Error logs show `MessageHandlingError`
- Agents receive messages but fail to process them

**Solutions:**
1. Check the message format is as expected
2. Verify that the agent's `handle_message` method correctly handles all message types
3. Look for missing fields or incorrect data types in messages

### Trade Execution Issues

#### Trade Proposal Rejections

**Symptoms:**
- Trade proposals are generated but rejected by the risk manager
- No trades are executed despite signals being generated

**Solutions:**
1. Check risk management settings (may be too restrictive)
2. Verify that proposals include all required fields
3. Check market conditions (volatility may trigger safety mechanisms)

#### Trade Execution Failures

**Symptoms:**
- Trade proposals are approved but fail during execution
- Error logs show API errors during buy/sell operations

**Solutions:**
1. Check account balance and trading limits
2. Verify symbol availability and market open hours
3. Check for issues with price or size (may be outside allowed ranges)
4. Ensure contract parameters are valid

### Performance Issues

#### High CPU Usage

**Symptoms:**
- System uses excessive CPU resources
- Processing cycles take longer than expected

**Solutions:**
1. Check for infinite loops or inefficient algorithms
2. Reduce the frequency of data updates or analysis
3. Optimize heavy computation in technical analysis
4. Consider enabling performance tracking for detailed metrics

#### Memory Leaks

**Symptoms:**
- System memory usage grows over time
- Performance degrades after running for extended periods

**Solutions:**
1. Check for objects not being properly released
2. Verify that large data structures are cleaned up when no longer needed
3. Check for accumulated messages in queues
4. Consider implementing periodic garbage collection

## Command Line Diagnostics

The system provides several command-line options for diagnostics:

```bash
# Run with increased logging detail
python main.py --log-level DEBUG

# Check configuration without running the system
python main.py --validate-config

# Test specific components
python main.py --test-component technical_analysis

# Run connectivity test
python main.py --connectivity-test
```

## Log Files

Important log files for troubleshooting:

- `logs/system.log`: Main system log
- `logs/errors.log`: Dedicated error log
- `logs/api_requests.log`: API request/response log
- `logs/trades.log`: Trading activity log
- `tradetest_output.log`: Output from trade tests

## Health Check Endpoints

When running in server mode, the system provides health check endpoints:

- `/health`: Basic system health
- `/health/agents`: Status of all agents
- `/health/connections`: Status of external connections
- `/health/trades`: Recent trade activity

## Reporting Issues

When reporting issues, please include:

1. Full error logs
2. System configuration (sanitized of sensitive data)
3. Steps to reproduce the issue
4. Environment details (OS, Python version, etc.)

## Common Error Codes

| Code | Description | Possible Solution |
|------|-------------|-------------------|
| E001 | Configuration error | Fix configuration file |
| E002 | API connection failure | Check network and credentials |
| E003 | Authentication error | Update API tokens |
| E004 | Message processing error | Check message format |
| E005 | Trade execution error | Verify trade parameters |
| E006 | Database error | Check database connection |
| E007 | Timeout error | Increase timeout settings |
| E008 | Resource limit reached | Reduce load or increase limits |
| E009 | Data validation error | Fix invalid data |
| E010 | System shutdown error | Check for forced termination |

## Recovery Procedures

### From Configuration Errors

1. Restore from the backup configuration
2. Fix the identified issues
3. Restart the system

### From API Connection Issues

1. Verify API credentials and network connectivity
2. Wait for services to become available if temporarily down
3. Consider using simulation mode temporarily

### From Trade Execution Failures

1. Check account status and balances
2. Verify that market conditions haven't changed dramatically
3. Consider manually closing any pending positions
4. Restart the system with modified risk parameters if needed

### From Critical System Failures

1. Stop the system completely
2. Back up all logs and data
3. Restore the last known good configuration
4. Start the system in simulation mode to verify stability
5. Switch back to live mode once stability is confirmed