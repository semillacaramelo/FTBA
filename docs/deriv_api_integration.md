
# Deriv API Integration

This document explains how the Deriv API is integrated into the Multi-Agent Forex Trading System.

## Overview

The [Deriv API](https://github.com/deriv-com/python-deriv-api) allows programmatic access to the Deriv trading platform, enabling automated trading of various financial instruments including forex, commodities, and synthetic indices.

Our system integrates with the Deriv API to:

1. Fetch real-time market data
2. Execute trades based on agent decisions
3. Monitor open positions
4. Process trade results

## Setup Process

To use the Deriv API integration:

1. Run the setup script:
   ```
   python scripts/setup_deriv.py
   ```

2. Follow the instructions to enter your Deriv API App ID.

3. (Optional) Test the API connection:
   ```
   python examples/deriv_api_example.py --app_id YOUR_APP_ID
   ```

4. Run the system with Deriv API integration:
   ```
   python main.py
   ```

## Configuration

The Deriv API configuration is stored in `config/settings.json` under the `deriv_api` section:

```json
"deriv_api": {
  "app_id": "YOUR_APP_ID",
  "endpoint": "wss://ws.binaryws.com/websockets/v3",
  "account_type": "demo",
  "symbols_mapping": {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "USD/CHF": "frxUSDCHF",
    "AUD/USD": "frxAUDUSD"
  },
  "default_contract_type": "CALL/PUT",
  "default_duration": 5,
  "default_duration_unit": "m"
}
```

Key configuration options:

- `app_id`: Your Deriv API application ID
- `endpoint`: Deriv WebSocket API endpoint
- `account_type`: "demo" or "live"
- `symbols_mapping`: Mapping between our symbol format and Deriv's format
- `default_contract_type`: Default contract type for trades
- `default_duration`: Default contract duration
- `default_duration_unit`: Default duration unit (m=minutes, h=hours, d=days)

## Trade Execution

The `TradeExecutionAgent` has been enhanced to support Deriv API integration:

1. When initialized with `gateway_type: "deriv"`, it connects to the Deriv API.
2. Approved trades are executed through the Deriv API.
3. A background task monitors open positions and processes completed trades.
4. Trade results are broadcast to other agents for analysis and optimization.

## Contract Types

Deriv supports various contract types:

- **CALL/PUT**: Standard high/low contracts
- **TOUCH/NO_TOUCH**: One-touch/no-touch contracts
- **ASIAN**: Asian settlement contracts
- **DIGIT**: Digit match/differ contracts
- **RESET/CALLSPREAD/PUTSPREAD**: Advanced contract types

Our implementation currently focuses on the CALL/PUT contracts, mapping:
- LONG positions to CALL contracts
- SHORT positions to PUT contracts

## Symbol Mapping

Deriv uses specific symbol codes that differ from standard forex notation:

- Standard: "EUR/USD" → Deriv: "frxEURUSD"
- Standard: "GBP/USD" → Deriv: "frxGBPUSD"

The mapping is defined in the configuration file and used by the trade execution agent.

## Error Handling

The integration includes comprehensive error handling:

1. Connection failures trigger automatic reconnection attempts
2. API errors are logged and reported to other agents
3. Invalid responses are detected and handled gracefully
4. Network timeouts have appropriate retry logic

## Limitations

Current limitations of the Deriv API integration:

1. Limited to forex pairs defined in the symbol mapping
2. Uses fixed contract durations rather than custom stop-loss/take-profit levels
3. Does not support partial position closures
4. No support for pending orders (limit/stop orders)

## Future Enhancements

Planned enhancements to the Deriv API integration:

1. Support for additional contract types
2. Dynamic contract duration based on strategy
3. Implementation of advanced position management features
4. Support for multi-account trading
5. Enhanced risk management features specific to Deriv
