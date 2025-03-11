# Trade Testing Guide

## Overview

The FTBA (Forex Trading Bot Automation) system includes a trade testing feature that allows you to validate the system's ability to execute real trades on a Deriv DEMO account. This document explains how to set up and use this feature.

## Prerequisites

Before using the trade testing feature, make sure you have:

1. A Deriv account (register at [Deriv.com](https://deriv.com) if you don't have one)
2. A Deriv App ID (create one at [Deriv Developers](https://developers.deriv.com/))
3. A Demo API token (create one at [Deriv API Token Page](https://app.deriv.com/account/api-token))
4. Configured these credentials in your environment (see [Dependency Management](dependency_management.md))

## Setting Up Credentials

You have two options for setting up your Deriv API credentials:

### Option 1: Using the Setup Wizard

Run the setup wizard script:

```bash
python scripts/setup_deriv.py
```

This interactive script will guide you through the process of configuring your credentials.

### Option 2: Manual Configuration

Set the environment variables directly:

```bash
# Linux/macOS
export DERIV_APP_ID=your_app_id
export DERIV_DEMO_API_TOKEN=your_demo_token

# Windows
set DERIV_APP_ID=your_app_id
set DERIV_DEMO_API_TOKEN=your_demo_token
```

Alternatively, create a `config/deriv.ini` file:

```ini
[deriv]
app_id = your_app_id
demo_api_token = your_demo_token
use_demo = true
```

## Running the Trade Test

To execute a test trade, run:

```bash
python main.py --tradetest
```

This will:

1. Initialize the full multi-agent system
2. Connect to your Deriv DEMO account
3. Execute a test PUT (buy) and CALL (sell) trade
4. Log the results to `tradetest_output.log`

## Test Trade Parameters

The test trades use the following default parameters:

- Symbol: EUR/USD (can be configured in config/testing.yml)
- Contract Type: CALL/PUT (Rise/Fall)
- Duration: 5 minutes
- Stake Amount: 10 USD (minimum allowed by Deriv)

## Interpreting Results

After running the test, check the output log file (`tradetest_output.log`) for detailed information about the trades. Successful test trades will show:

- Contract IDs
- Entry prices
- Transaction timestamps
- Contract status updates

## Troubleshooting

If you encounter issues with trade testing:

1. **Connection Issues**: Verify your internet connection and firewall settings.
2. **Authentication Errors**: Confirm your API token is valid and has appropriate permissions.
3. **Invalid App ID**: Verify your App ID is correct and registered with Deriv.
4. **Market Closed**: Some symbols are only available during market hours. Try EUR/USD which has longer trading hours.
5. **Insufficient Funds**: Ensure your demo account has sufficient balance.

Run the check dependencies script to verify all required components are installed:

```bash
python scripts/check_dependencies.py
```

## Important Notes

- **Always use a DEMO account** for testing. Never use a real money account for automated testing.
- The default trade size is minimal (10 USD) to avoid significant virtual balance reduction.
- Test trades are executed immediately regardless of agent recommendations.
- Test trades are executed with a 5-minute duration by default.

## Next Steps

After successful trade testing, you can:

1. Adjust trading parameters in the configuration files
2. Implement your own custom strategies
3. Modify agent behaviors based on your trading preferences