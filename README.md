# FTBA - Multi-Agent Forex Trading Bot Autonomous

A sophisticated multi-agent system for automated foreign exchange trading using specialized agents and the Deriv API.

![System Architecture](docs/images/system_architecture.png)

## Overview

The FTBA (Forex Trading Bot Autonomous) is an event-driven, distributed artificial intelligence platform designed for algorithmic trading in the foreign exchange market. The system employs a team of specialized agents that communicate and collaborate to identify trading opportunities, manage risk, and execute trades.

### Key Features

- **Distributed Intelligence**: Five specialized agents working collaboratively through a central message broker
- **Real-time Market Analysis**: Continuous monitoring of market conditions with technical and fundamental analysis
- **Adaptive Strategy Optimization**: Machine learning-based strategy refinement and parameter optimization
- **Comprehensive Risk Management**: Multi-layered approach to risk control and position sizing
- **Deriv API Integration**: Real trade execution using the Deriv trading platform API
- **Enhanced Console Output**: Color-coded and icon-based logging for improved readability
- **Extensive Testing Framework**: Comprehensive test suite for all system components

## Specialized Agents

The system is built around five specialized agents, each with distinct responsibilities:

1. **Technical Analysis Agent**: Analyzes price charts and technical indicators to identify potential trade setups using pattern recognition and statistical analysis.

2. **Fundamental Analysis Agent**: Monitors economic news, events, and indicators to assess macro-economic impacts on currency values.

3. **Risk Management Agent**: Evaluates trade proposals against risk parameters, ensures portfolio-level risk control, and prevents excessive exposure.

4. **Strategy Optimization Agent**: Leverages machine learning to continuously refine trading strategies based on performance metrics and market conditions.

5. **Trade Execution Agent**: Manages order submission using the Deriv API, monitors open positions, and handles trade lifecycle events.

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- Internet connection for market data feeds and API access
- Deriv API credentials (see [Deriv API Integration](docs/deriv_api_integration.md))

### Basic Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/FTBA.git
   cd FTBA
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install in development mode:
   ```bash
   pip install -e .
   ```

3. Copy and configure settings:
   ```bash
   cp config/settings.example.json config/settings.json
   # Edit config/settings.json with your preferred settings
   ```

4. Set up Deriv API credentials (see [Deriv API Integration](docs/deriv_api_integration.md) for details):
   ```bash
   # Set environment variables for API access
   export DERIV_APP_ID=your_app_id
   export DERIV_DEMO_API_TOKEN=your_demo_token
   
   # Optional: For live trading (use with caution)
   export DERIV_API_TOKEN=your_live_token
   ```

## Usage

### Starting the System

```bash
# Start the standard application
python main.py

# Run in simulation mode (no real trades)
python main.py --simulation

# Execute test trades to verify functionality
python main.py --tradetest
```

### Command Line Arguments

- `--config CONFIG_PATH`: Use a custom configuration file
- `--simulation`: Run in simulation mode with no real trades
- `--tradetest`: Execute one CALL and one PUT test trade with the Deriv demo account

### Monitoring

The system provides several monitoring interfaces:

1. **Console Output**: Real-time color-coded logging of system activities with informative icons
2. **Log Files**: Detailed logs stored in the `logs` directory

### Stopping the System

The system can be stopped gracefully by sending a SIGINT signal (Ctrl+C).

## Configuration

The primary configuration file (`config/settings.json`) contains settings for:

- Market data sources
- Trading parameters
- Risk management thresholds
- Agent-specific parameters
- Logging configuration

Example configuration:

```json
{
  "system": {
    "log_level": "INFO",
    "data_directory": "./data",
    "backup_directory": "./backups"
  },
  "market_data": {
    "provider": "deriv",
    "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"]
  },
  "risk_management": {
    "max_account_risk_percent": 2.0,
    "max_position_size_percent": 5.0,
    "max_daily_loss_percent": 5.0
  },
  "agents": {
    "technical_analysis": {
      "analysis_interval_seconds": 60,
      "signal_threshold": 0.7
    },
    "fundamental_analysis": {
      "update_interval_seconds": 300
    },
    "risk_management": {
      "update_interval_seconds": 60
    },
    "strategy_optimization": {
      "update_interval_seconds": 300,
      "learning_rate": 0.1
    },
    "trade_execution": {
      "gateway_type": "deriv",
      "use_demo_account": true,
      "check_interval_seconds": 1
    }
  }
}
```

For detailed configuration options, see the [Configuration Guide](docs/configuration.md).

## Directory Structure

```
FTBA/
├── agents/                  # Agent implementation modules
│   ├── technical_analysis_agent.py
│   ├── fundamental_analysis_agent.py
│   ├── risk_management_agent.py
│   ├── strategy_optimization_agent.py
│   └── trade_execution_agent.py
├── config/                  # Configuration files
├── data/                    # Data storage
│   ├── market_data/         # Historical and real-time market data
│   ├── economic_calendar/   # Economic events data
│   └── performance/         # System performance metrics
├── docs/                    # Documentation
├── examples/                # Example scripts
├── logs/                    # Log files
├── python-deriv-api/        # Deriv API library
├── scripts/                 # Utility scripts
├── system/                  # Core system components
│   ├── agent.py            # Base agent class
│   ├── api_client.py       # API client base class
│   ├── console_utils.py    # Console output utilities
│   ├── core.py             # Core data structures
│   ├── deriv_api_client.py # Deriv API client
│   └── error_handling.py   # Error handling utilities
├── tests/                   # Test suite
├── .gitignore               # Git ignore file
├── main.py                  # Main entry point
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── run_tests.py             # Test runner script
├── setup.py                 # Package setup file
└── system_architecture.md   # System architecture description
```

## Testing

The system includes a comprehensive test suite that can be run using:

```bash
python run_tests.py
```

To run specific tests:

```bash
python run_tests.py --pattern "test_agent"  # Run all agent tests
```

To list available tests:

```bash
python run_tests.py --list
```

## API Integration

The system integrates with the Deriv API for trading. For details on setup and functionality, see:

- [Deriv API Integration Guide](docs/deriv_api_integration.md)
- [Dependency Management](docs/dependency_management.md)

## Recent Updates

- Successfully implemented trade test functionality with CALL/PUT orders
- Enhanced console output with color coding and icons
- Improved connection handling with the Deriv API
- Added comprehensive status monitoring for all processes
- Refined documentation and configuration files

## Disclaimer

This system is a sophisticated trading tool, but it does not guarantee profits. Foreign exchange trading involves significant risk and may not be suitable for all investors. Past performance is not indicative of future results.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
