# FTBA
# Multi-Agent Forex Trading System

> A collaborative artificial intelligence system for automated foreign exchange trading using specialized agents

## Overview

The Multi-Agent Forex Trading System is a sophisticated, distributed artificial intelligence platform designed for algorithmic trading in the foreign exchange market. The system employs a team of five specialized agents that communicate and collaborate to identify trading opportunities, manage risk, and execute trades.

![System Architecture](docs/images/system_architecture.png)

### Key Features

- **Distributed Intelligence**: Five specialized agents working collaboratively
- **Real-time Market Analysis**: Continuous monitoring of market conditions
- **Adaptive Strategy Optimization**: Machine learning-based strategy refinement
- **Comprehensive Risk Management**: Multi-layered approach to risk control
- **Event-driven Architecture**: Message-based communication for flexibility and scalability
- **Extendable Framework**: Easy integration of new strategies and data sources

## Specialized Agents

The system is built around five specialized agents, each with distinct responsibilities:

1. **Technical Analysis Agent**: Analyzes price charts and technical indicators to identify potential trade setups using pattern recognition and statistical analysis.

2. **Fundamental Analysis Agent**: Monitors economic news, events, and indicators to assess macro-economic impacts on currency values.

3. **Risk Management Agent**: Evaluates trade proposals against risk parameters, ensures portfolio-level risk control, and prevents excessive exposure.

4. **Strategy Optimization Agent**: Leverages machine learning to continuously refine trading strategies based on performance metrics and market conditions.

5. **Trade Execution Agent**: Manages order submission, monitors open positions, and handles trade lifecycle events.

## System Architecture

The system follows an event-driven architecture where agents communicate through a centralized message broker. This design allows for:

- Loose coupling between agents
- Asynchronous operation
- Scalable processing
- Fault tolerance
- Easy addition of new agents or capabilities

### Communication Protocol

Agents exchange standardized messages through a message broker. Each message contains:

- Message ID
- Message type (e.g., technical signal, trade proposal, risk assessment)
- Sender and recipient information
- Timestamp
- Content payload
- Correlation ID for linked messages

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- Internet connection for market data feeds
- Sufficient RAM (8GB+ recommended)

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/forex-multi-agent.git
cd forex-multi-agent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure settings
cp config/settings.example.json config/settings.json
# Edit config/settings.json with your preferred settings
```

### Configuration

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
    "provider": "simulation",
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
      "check_interval_seconds": 1,
      "slippage_model": "fixed",
      "fixed_slippage_pips": 1.0
    }
  }
}
```

## Usage

### Starting the System

```bash
# Activate the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the system
python main.py
```

### Monitoring

The system provides several monitoring interfaces:

1. **Console Output**: Real-time logging of system activities
2. **Web Dashboard** (optional): Visual representation of system status, agent activities, and trade history
3. **Log Files**: Detailed logs stored in the `logs` directory

### Stopping the System

The system can be stopped gracefully by sending a SIGINT signal (Ctrl+C) or through the administration interface.

## Directory Structure

```
forex-multi-agent/
├── agents/                  # Agent implementation modules
│   ├── technical_analysis_agent.py
│   ├── fundamental_analysis_agent.py
│   ├── risk_management_agent.py
│   ├── strategy_optimization_agent.py
│   └── trade_execution_agent.py
├── data/                    # Data storage
│   ├── market_data/         # Historical and real-time market data
│   ├── economic_calendar/   # Economic events data
│   └── performance/         # System performance metrics
├── system/                  # Core system components
│   ├── core.py             # Core data structures
│   ├── agent.py            # Base agent class and message broker
│   └── utils/              # Utility functions
├── config/                  # Configuration files
├── logs/                    # Log files
├── docs/                    # Documentation
├── tests/                   # Test suite
├── main.py                  # Main entry point
└── README.md                # This file
```

## Agent Details

### Technical Analysis Agent

The Technical Analysis Agent continuously analyzes price charts across multiple timeframes to identify trading opportunities. It utilizes various technical indicators including:

- Moving Average crossovers
- Relative Strength Index (RSI)
- Support and resistance levels
- Chart patterns
- Momentum indicators

The agent consolidates signals from different timeframes to reduce noise and increase reliability, before broadcasting significant signals to other agents.

### Fundamental Analysis Agent

The Fundamental Analysis Agent monitors economic events and news that might impact currency values:

- Central bank decisions
- Interest rate changes
- Economic indicators (GDP, inflation, employment)
- Political events
- Market sentiment analysis

This agent maintains an economic calendar to anticipate upcoming events and assesses the potential market impact of actual data releases versus expectations.

### Risk Management Agent

The Risk Management Agent serves as the system's safety mechanism by:

- Evaluating trade proposals against risk parameters
- Managing position sizing
- Enforcing stop-loss placement
- Monitoring overall portfolio risk
- Preventing excessive exposure to correlated assets
- Implementing circuit breakers in volatile conditions

Every trade proposal must be approved by this agent before execution.

### Strategy Optimization Agent

The Strategy Optimization Agent continuously improves trading strategies through:

- Performance analysis of executed trades
- Machine learning based parameter optimization
- Adaptation to changing market conditions
- A/B testing of strategy variations
- Identification of optimal market conditions for each strategy

This agent evaluates the effectiveness of different strategies across various market regimes and adjusts parameters to improve performance.

### Trade Execution Agent

The Trade Execution Agent handles the interaction with the market:

- Executes approved trades
- Manages order placement and cancellation
- Monitors open positions
- Adjusts stop-loss and take-profit levels
- Implements trailing stops
- Handles partial fills and slippage

This agent is optimized for efficient order execution while minimizing market impact and slippage.

## Communication Flow Example

A typical interaction flow:

1. **Technical Analysis Agent** detects a potential breakout pattern in EUR/USD
2. It sends a `TECHNICAL_SIGNAL` message with confidence level and direction
3. **Strategy Optimization Agent** receives this signal and correlates with fundamental data
4. If promising, it creates a `TRADE_PROPOSAL` with entry, stop-loss, and take-profit levels
5. **Risk Management Agent** evaluates the proposal against risk parameters
6. If approved, it modifies the proposal (e.g., position size) and sends back an approval
7. **Trade Execution Agent** receives the approved proposal and executes the trade
8. Execution confirmation is broadcast to all agents
9. Agents update their internal state based on the execution

## Performance Metrics

The system tracks various performance metrics:

- **Profitability**: Net profit/loss, return on investment
- **Risk Management**: Maximum drawdown, Sharpe ratio, Sortino ratio
- **Execution Quality**: Slippage, fill rate
- **Strategy Performance**: Win rate, profit factor per strategy
- **Agent Performance**: Signal accuracy, proposal quality

Performance reports are generated daily and stored in the `data/performance` directory.

## Extending the System

### Adding New Strategies

1. Define the strategy parameters in the Strategy Optimization Agent
2. Implement the strategy logic
3. Add strategy-specific signal processing in the Technical Analysis Agent
4. Register the strategy in the configuration file

### Integrating New Data Sources

1. Create a data provider class in the `system/data_providers` directory
2. Implement the required interface methods
3. Register the new data provider in the configuration
4. Update relevant agents to utilize the new data

### Creating Custom Agents

1. Create a new agent class that inherits from the base `Agent` class
2. Implement required methods (setup, cleanup, process_cycle, handle_message)
3. Register message subscriptions
4. Update the system configuration to include the new agent

## Risk Considerations

### Disclaimer

This system is a sophisticated trading tool, but it does not guarantee profits. Foreign exchange trading involves significant risk and may not be suitable for all investors. Past performance is not indicative of future results.

### System Limitations

- The system cannot predict unpredictable events (e.g., natural disasters, sudden political changes)
- Backtesting performance may differ from live trading results
- Model accuracy depends on the quality of input data
- Market conditions change over time, requiring continuous adaptation

## FAQs

### General Questions

**Q: Can the system run on a standard home computer?**  
A: Yes, the base system can run on a standard computer with 8GB+ RAM. However, for production use, a more powerful setup or cloud deployment is recommended.

**Q: How much data does the system need to start trading effectively?**  
A: The system requires at least 6 months of historical data for initial calibration, but performs better with 1+ years of data.

**Q: Is the system fully automated or does it require human oversight?**  
A: The system is designed to operate autonomously, but human oversight is recommended, especially in volatile market conditions.

### Technical Questions

**Q: How does the system handle network outages?**  
A: The system includes reconnection logic, order status verification, and position reconciliation to handle network interruptions safely.

**Q: Can I run the system with a specific broker?**  
A: Yes, by implementing a custom gateway adapter for your broker's API in the Trade Execution Agent.

**Q: How are conflicting signals between agents resolved?**  
A: The Strategy Optimization Agent weighs signals based on historical performance and current market conditions, while the Risk Management Agent has final approval authority.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This system architecture draws inspiration from multi-agent systems research
- Technical indicator implementations utilize established financial analysis methodologies
- Risk management approaches are based on professional trading practices

---

© 2025 Multi-Agent Forex Trading System
