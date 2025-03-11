# Configuration Guide

This document provides detailed information about configuring the FTBA system.

## Overview

The FTBA system is configured using a JSON configuration file, typically located at `config/settings.json`. This file defines system-wide settings, market data sources, risk parameters, and agent-specific configuration.

## Configuration File Structure

The configuration file is structured into several main sections:

```json
{
  "system": { ... },       // System-wide settings
  "market_data": { ... },  // Market data configuration
  "risk_management": { ... }, // Risk parameters
  "agents": {              // Agent-specific configuration
    "technical_analysis": { ... },
    "fundamental_analysis": { ... },
    "risk_management": { ... },
    "strategy_optimization": { ... },
    "trade_execution": { ... }
  }
}
```

## System Configuration

The `system` section contains global settings for the entire application:

```json
"system": {
  "log_level": "INFO",          // Logging level (DEBUG, INFO, WARNING, ERROR)
  "data_directory": "./data",    // Directory for data storage
  "backup_directory": "./backups", // Directory for backups
  "max_memory_usage_mb": 1024,   // Maximum memory usage
  "message_batch_size": 10,      // Number of messages to batch
  "performance_tracking": true,  // Enable performance tracking
  "shutdown_timeout_seconds": 30 // Graceful shutdown timeout
}
```

## Market Data Configuration

The `market_data` section configures the market data sources:

```json
"market_data": {
  "provider": "deriv",           // Data provider (deriv, simulation)
  "symbols": [                   // Symbols to track
    "EUR/USD", 
    "GBP/USD", 
    "USD/JPY", 
    "USD/CHF", 
    "AUD/USD"
  ],
  "timeframes": [                // Timeframes to analyze
    "1m", "5m", "15m", "1h", "4h", "1d"
  ],
  "historical_data_days": 30,    // Days of historical data to load
  "update_interval_seconds": 1   // Real-time data update interval
}
```

## Risk Management Configuration

The `risk_management` section defines risk control parameters:

```json
"risk_management": {
  "max_account_risk_percent": 2.0,    // Maximum account risk per trade
  "max_position_size_percent": 5.0,   // Maximum position size
  "max_daily_loss_percent": 5.0,      // Daily loss limit
  "max_open_positions": 5,            // Maximum concurrent positions
  "correlation_threshold": 0.7,       // Correlation threshold for diversification
  "min_reward_risk_ratio": 1.5,       // Minimum reward-to-risk ratio
  "circuit_breaker": {                // Circuit breaker settings
    "enabled": true,
    "threshold_percent": 5.0,         // Threshold for activation
    "cooldown_minutes": 60            // Cooldown period after activation
  }
}
```

## Agent Configuration

Each agent has its own configuration section under the `agents` key:

### Technical Analysis Agent

```json
"technical_analysis": {
  "analysis_interval_seconds": 60,    // Analysis update interval
  "signal_threshold": 0.7,            // Minimum signal strength threshold
  "indicators": {                     // Indicator settings
    "moving_averages": {
      "enabled": true,
      "periods": [9, 21, 50, 200]
    },
    "rsi": {
      "enabled": true,
      "period": 14,
      "overbought": 70,
      "oversold": 30
    },
    "macd": {
      "enabled": true,
      "fast_period": 12,
      "slow_period": 26,
      "signal_period": 9
    },
    "bollinger_bands": {
      "enabled": true,
      "period": 20,
      "std_dev": 2.0
    }
  },
  "pattern_recognition": {            // Pattern recognition settings
    "enabled": true,
    "min_pattern_quality": 0.6
  }
}
```

### Fundamental Analysis Agent

```json
"fundamental_analysis": {
  "update_interval_seconds": 300,     // Update interval
  "event_sources": [                  // Event data sources
    "economic_calendar", 
    "central_bank_announcements"
  ],
  "impact_thresholds": {              // Event impact thresholds
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2
  },
  "max_event_horizon_days": 7,        // Maximum days to look ahead
  "sentiment_analysis": {             // Sentiment analysis settings
    "enabled": true,
    "min_confidence": 0.6
  }
}
```

### Risk Management Agent

```json
"risk_management": {
  "update_interval_seconds": 60,      // Update interval
  "volatility_adjustment": true,      // Adjust for volatility
  "correlation_window_days": 30,      // Correlation calculation window
  "max_correlation_allowed": 0.7,     // Maximum allowed correlation
  "drawdown_recovery": {              // Drawdown recovery settings
    "enabled": true,
    "threshold_percent": 10.0,        // Threshold for reducing risk
    "reduction_factor": 0.5           // Risk reduction factor
  },
  "stress_testing": {                 // Stress testing settings
    "enabled": true,
    "scenarios": ["volatility_spike", "trend_reversal"]
  }
}
```

### Strategy Optimization Agent

```json
"strategy_optimization": {
  "update_interval_seconds": 300,     // Update interval
  "learning_rate": 0.1,               // Learning rate for optimization
  "optimization_window_days": 30,     // Optimization window
  "min_samples_required": 20,         // Minimum samples for learning
  "learning_algorithms": [            // Learning algorithms
    "bayesian", "reinforcement"
  ],
  "performance_metrics": [            // Performance metrics to track
    "profit_factor", "sharpe_ratio", "win_rate", "drawdown"
  ],
  "regime_detection": {               // Market regime detection
    "enabled": true,
    "window_size": 100,
    "feature_set": ["volatility", "trend_strength", "momentum"]
  }
}
```

### Trade Execution Agent

```json
"trade_execution": {
  "gateway_type": "deriv",            // Gateway type (deriv, simulation)
  "use_demo_account": true,           // Use demo account
  "check_interval_seconds": 1,        // Order checking interval
  "retry_attempts": 3,                // Retry attempts on failure
  "retry_delay_seconds": 1,           // Delay between retries
  "slippage_model": "fixed",          // Slippage model
  "fixed_slippage_pips": 1.0,         // Fixed slippage amount
  "order_types": ["market", "limit"], // Supported order types
  "position_management": {            // Position management settings
    "use_trailing_stop": true,
    "trailing_stop_activation_percent": 0.5,
    "trailing_stop_distance_percent": 1.0
  },
  "trade_sizing": {                   // Trade sizing settings
    "model": "risk_based",            // Sizing model
    "fixed_size": 0.01,               // Fixed position size
    "risk_percent": 1.0,              // Risk percentage
    "atr_multiplier": 2.0             // ATR multiplier for stop loss
  }
}
```

## Configuration File Example

Below is a complete example of a configuration file:

```json
{
  "system": {
    "log_level": "INFO",
    "data_directory": "./data",
    "backup_directory": "./backups",
    "max_memory_usage_mb": 1024,
    "message_batch_size": 10,
    "performance_tracking": true,
    "shutdown_timeout_seconds": 30
  },
  "market_data": {
    "provider": "deriv",
    "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
    "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
    "historical_data_days": 30,
    "update_interval_seconds": 1
  },
  "risk_management": {
    "max_account_risk_percent": 2.0,
    "max_position_size_percent": 5.0,
    "max_daily_loss_percent": 5.0,
    "max_open_positions": 5,
    "correlation_threshold": 0.7,
    "min_reward_risk_ratio": 1.5,
    "circuit_breaker": {
      "enabled": true,
      "threshold_percent": 5.0,
      "cooldown_minutes": 60
    }
  },
  "agents": {
    "technical_analysis": {
      "analysis_interval_seconds": 60,
      "signal_threshold": 0.7,
      "indicators": {
        "moving_averages": {
          "enabled": true,
          "periods": [9, 21, 50, 200]
        },
        "rsi": {
          "enabled": true,
          "period": 14,
          "overbought": 70,
          "oversold": 30
        },
        "macd": {
          "enabled": true,
          "fast_period": 12,
          "slow_period": 26,
          "signal_period": 9
        },
        "bollinger_bands": {
          "enabled": true,
          "period": 20,
          "std_dev": 2.0
        }
      },
      "pattern_recognition": {
        "enabled": true,
        "min_pattern_quality": 0.6
      }
    },
    "fundamental_analysis": {
      "update_interval_seconds": 300,
      "event_sources": ["economic_calendar", "central_bank_announcements"],
      "impact_thresholds": {
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2
      },
      "max_event_horizon_days": 7,
      "sentiment_analysis": {
        "enabled": true,
        "min_confidence": 0.6
      }
    },
    "risk_management": {
      "update_interval_seconds": 60,
      "volatility_adjustment": true,
      "correlation_window_days": 30,
      "max_correlation_allowed": 0.7,
      "drawdown_recovery": {
        "enabled": true,
        "threshold_percent": 10.0,
        "reduction_factor": 0.5
      },
      "stress_testing": {
        "enabled": true,
        "scenarios": ["volatility_spike", "trend_reversal"]
      }
    },
    "strategy_optimization": {
      "update_interval_seconds": 300,
      "learning_rate": 0.1,
      "optimization_window_days": 30,
      "min_samples_required": 20,
      "learning_algorithms": ["bayesian", "reinforcement"],
      "performance_metrics": ["profit_factor", "sharpe_ratio", "win_rate", "drawdown"],
      "regime_detection": {
        "enabled": true,
        "window_size": 100,
        "feature_set": ["volatility", "trend_strength", "momentum"]
      }
    },
    "trade_execution": {
      "gateway_type": "deriv",
      "use_demo_account": true,
      "check_interval_seconds": 1,
      "retry_attempts": 3,
      "retry_delay_seconds": 1,
      "slippage_model": "fixed",
      "fixed_slippage_pips": 1.0,
      "order_types": ["market", "limit"],
      "position_management": {
        "use_trailing_stop": true,
        "trailing_stop_activation_percent": 0.5,
        "trailing_stop_distance_percent": 1.0
      },
      "trade_sizing": {
        "model": "risk_based",
        "fixed_size": 0.01,
        "risk_percent": 1.0,
        "atr_multiplier": 2.0
      }
    }
  }
}
```

## Environment Variables

Some configuration can be overridden using environment variables:

- `DERIV_APP_ID`: Deriv API application ID
- `DERIV_DEMO_API_TOKEN`: API token for Deriv demo account
- `DERIV_API_TOKEN`: API token for Deriv live account (caution: real money)
- `FTBA_LOG_LEVEL`: Override the logging level
- `FTBA_CONFIG_PATH`: Custom path to configuration file

## Creating a Minimal Configuration

For testing or development, a minimal configuration can be used:

```json
{
  "system": {
    "log_level": "INFO"
  },
  "market_data": {
    "provider": "simulation",
    "symbols": ["EUR/USD"]
  },
  "risk_management": {
    "max_account_risk_percent": 1.0
  },
  "agents": {
    "technical_analysis": {
      "analysis_interval_seconds": 60
    },
    "fundamental_analysis": {
      "update_interval_seconds": 300
    },
    "risk_management": {
      "update_interval_seconds": 60
    },
    "strategy_optimization": {
      "update_interval_seconds": 300
    },
    "trade_execution": {
      "gateway_type": "simulation",
      "check_interval_seconds": 1
    }
  }
}
```

## Troubleshooting

If you encounter configuration issues:

1. Validate your JSON syntax using a JSON validator
2. Check the logs for specific configuration errors
3. Ensure all required fields are present
4. Verify that file paths are correct and accessible
5. Check environment variables for any overrides