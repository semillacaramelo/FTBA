# Trade Testing Guide

This document explains how to use the trade testing functionality in the FTBA system to verify that the Deriv API integration is working correctly.

## Overview

The trade testing feature (`--tradetest` option) executes one CALL (buy) and one PUT (sell) contract on EUR/USD using the Deriv demo account. This allows you to verify that:

1. The connection to the Deriv API is working
2. Your API tokens are valid
3. Trades can be executed successfully
4. The response handling is functioning properly

## Prerequisites

Before using the trade testing functionality, ensure you have:

1. A Deriv demo account
2. A Deriv API token with trading permissions for the demo account
3. The Deriv API App ID
4. Both values set as environment variables:
   ```
   DERIV_APP_ID=your_app_id
   DERIV_DEMO_API_TOKEN=your_demo_token
   ```

## Running a Trade Test

To execute the test trades, run:

```bash
python main.py --tradetest
```

This will:

1. Initialize the system with minimal components
2. Connect to the Deriv API using your credentials
3. Execute a CALL trade on EUR/USD
4. Execute a PUT trade on EUR/USD
5. Display detailed status updates in the console
6. Write the trade results to `tradetest_output.log`

## Expected Output

A successful test will produce console output similar to:

```
ℹ️ [INFO] Starting trade test mode
⚙️ [SYSTEM] Initializing Deriv API client
✅ [SUCCESS] Connected to Deriv API
📊 [DATA] Current EUR/USD price: 1.0865/1.0867
⏳ [TRADE PENDING] Executing CALL trade for EUR/USD
📈 [TRADE SUCCESS] CALL contract executed
   Contract ID: 275102430888
   Buy price: 10.00 USD
   Symbol: frxEURUSD
   Duration: 1 day
⏳ [TRADE PENDING] Executing PUT trade for EUR/USD
📈 [TRADE SUCCESS] PUT contract executed
   Contract ID: 275102432788
   Buy price: 10.00 USD
   Symbol: frxEURUSD
   Duration: 1 day
✅ [SUCCESS] Trade test completed successfully
ℹ️ [INFO] Trade details saved to tradetest_output.log
```

## Trade Parameters

The test trades use the following parameters:

- **Symbol**: EUR/USD (frxEURUSD in Deriv format)
- **Trade size**: 10.00 USD
- **Duration**: 1 day
- **Contract types**: CALL and PUT (binary options)

These parameters are hardcoded for the test and don't reflect the actual trading parameters that would be used in production.

## Verifying Results

After running a trade test, you can:

1. Check the console output for success messages
2. Review the `tradetest_output.log` file for detailed trade information
3. Log in to your Deriv demo account to view the executed trades

## Troubleshooting

### Connection Issues

If you see an error like:

```
❌ [ERROR] Failed to connect to Deriv API: Connection timed out
```

Check:
- Your internet connection
- Firewall settings that might block WebSocket connections
- The Deriv API endpoint status (see https://api.deriv.com/status)

### Authentication Errors

If you see an error like:

```
❌ [ERROR] Authorization failed: Invalid token
```

Check:
- Your `DERIV_DEMO_API_TOKEN` environment variable is set correctly
- The token has permissions for the demo account
- The token hasn't expired (regenerate a new one if needed)

### App ID Errors

If you see an error like:

```
❌ [ERROR] Invalid App ID
```

Check:
- Your `DERIV_APP_ID` environment variable is set correctly
- Your App ID is registered and active on Deriv

## Example Log File

The `tradetest_output.log` file contains detailed information about the executed trades:

```
[2025-03-11 12:34:56] Trade Test Started
[2025-03-11 12:34:57] Connected to Deriv API with App ID: 1234
[2025-03-11 12:34:58] Current market price for EUR/USD: 1.0865/1.0867
[2025-03-11 12:34:59] Executing CALL contract on frxEURUSD:
  - Amount: 10.00 USD
  - Duration: 1 day
  - Direction: CALL
[2025-03-11 12:35:00] CALL contract executed successfully:
  - Contract ID: 275102430888
  - Buy price: 10.00 USD
  - Payout: 18.20 USD
  - Start: 2025-03-11 12:35:00
  - End: 2025-03-12 12:35:00
[2025-03-11 12:35:01] Executing PUT contract on frxEURUSD:
  - Amount: 10.00 USD
  - Duration: 1 day
  - Direction: PUT
[2025-03-11 12:35:02] PUT contract executed successfully:
  - Contract ID: 275102432788
  - Buy price: 10.00 USD
  - Payout: 18.20 USD
  - Start: 2025-03-11 12:35:02
  - End: 2025-03-12 12:35:02
[2025-03-11 12:35:03] Trade Test Completed
```

## Using Trade Tests in Development

The trade test functionality is useful during development for:

1. **Initial Setup Verification**: Confirm that your development environment can connect to the Deriv API
2. **CI/CD Pipeline Testing**: Verify API integration in automated builds (using secure environment variables)
3. **API Changes Monitoring**: Detect changes in the Deriv API that might affect your implementation
4. **Demo Account Verification**: Ensure your demo account is active and configured correctly

## Security Considerations

Remember:

1. **Never commit API tokens to source control**
2. Use environment variables or secure credential storage
3. Only use demo accounts for testing
4. Monitor your demo account for any unexpected activity

## Next Steps After Testing

After successfully running trade tests:

1. Review the code in `main.py` and `system/deriv_api_client.py` to understand the implementation
2. Check how trades are executed in `--tradetest` mode
3. Compare with the full system's trade execution flow in production mode
4. Consider adding more comprehensive tests for different market conditions and contract types