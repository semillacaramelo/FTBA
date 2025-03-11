# Error Handling Guide

## Overview

The FTBA system includes a robust error handling mechanism to ensure the system operates reliably even when encountering issues. This document explains the error handling architecture and common error resolution strategies.

## Error Handling Architecture

The error handling system is built on several components:

1. **Central Error Handler**: The `ErrorHandler` class in `system/error_handling.py` provides centralized error management.
2. **Exception Decorators**: Functions can be decorated with `@handle_exceptions` or `@handle_async_exceptions`.
3. **Global Exception Hook**: Uncaught exceptions are captured by a global handler.
4. **Context-aware Logging**: Errors include context information for easier debugging.

## Common Error Types

### Connection Errors

When the system cannot connect to the Deriv API:

```
ERROR - ❌ Failed to connect to Deriv API: Connection refused
```

**Resolution:**
1. Check your internet connection
2. Verify the API endpoint is correct
3. Check that the Deriv API service is available

### Authentication Errors

When the system cannot authenticate with your API credentials:

```
ERROR - ❌ Authentication failed: Invalid API token
```

**Resolution:**
1. Verify your API token is valid
2. Check that your app ID is correctly registered
3. Run `python scripts/setup_deriv.py` to reconfigure your credentials

### Market Data Errors

When the system cannot retrieve market data:

```
ERROR - ❌ Failed to get market data for EUR/USD: Symbol unavailable
```

**Resolution:**
1. Verify the symbol is available for trading
2. Check if the market is currently open
3. Try with a more commonly traded symbol (e.g., EUR/USD)

### Agent Initialization Errors

When one of the trading agents fails to initialize:

```
ERROR - ❌ Failed to initialize Technical Analysis Agent: Missing configuration
```

**Resolution:**
1. Check the configuration files in the `config` directory
2. Ensure all required configuration values are present
3. Verify that dependencies for technical analysis are installed

### Trade Execution Errors

When a trade cannot be executed:

```
ERROR - ❌ Trade execution failed: Insufficient balance
```

**Resolution:**
1. Check your demo account balance
2. Verify the trade parameters are valid
3. Ensure the market is open for the selected symbol

## Dependency-related Errors

### Missing Deriv API Package

When the system cannot find the Deriv API package:

```
ERROR - ❌ ModuleNotFoundError: No module named 'deriv_api'
```

**Resolution:**
1. Run `python scripts/check_dependencies.py` to verify dependencies
2. Install the package manually:
   ```
   pip install git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api
   ```
3. Alternatively, run `pip install -e .` to install all dependencies

### API Version Incompatibility

When the installed API version is incompatible:

```
ERROR - ❌ ImportError: cannot import name 'DerivAPI' from 'deriv_api'
```

**Resolution:**
1. Reinstall the correct version:
   ```
   pip uninstall python-deriv-api -y
   pip install git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api
   ```
2. Check for API changes in the [GitHub repository](https://github.com/deriv-com/python-deriv-api)

## Logging and Debugging

The system uses a colored logging system to make error identification easier:

- ❌ RED: Errors
- ⚠️ YELLOW: Warnings
- ℹ️ BLUE: Information
- 📶 CYAN: Technical signals
- 📈 GREEN: Successful trades

All logs are stored in the `logs` directory with a timestamp. For detailed debugging:

1. Check the latest log file in `logs/`
2. Look for any error messages (marked with ❌)
3. Examine the tracebacks for the source of the error

## Advanced Troubleshooting

For more complex issues:

1. Enable debug logging:
   ```python
   # In main.py
   logging_level = logging.DEBUG
   ```

2. Run the system with the verbose flag:
   ```bash
   python main.py --verbose
   ```

3. Check specific agent logs:
   ```bash
   grep "technical_analysis" logs/latest.log
   ```

4. Test individual components:
   ```bash
   python -c "from system.deriv_api_client import DerivApiClient; import asyncio; asyncio.run(DerivApiClient('your_app_id').ping())"
   ```

## Getting Support

If you're unable to resolve an error:

1. Check the [Issues](https://github.com/your-username/forex-multi-agent/issues) page for similar problems
2. Provide the following when seeking help:
   - Complete error message and traceback
   - System version and configuration
   - Steps to reproduce the issue