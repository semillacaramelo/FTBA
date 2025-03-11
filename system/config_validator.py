
"""
Configuration validation utilities for the multi-agent forex trading system.
"""

import json
import jsonschema
from typing import Dict, Any, List, Optional

# Schema for validating the system configuration
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "system": {
            "type": "object",
            "properties": {
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "data_directory": {"type": "string"},
                "backup_directory": {"type": "string"}
            },
            "required": ["log_level"]
        },
        "market_data": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "symbols": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["provider", "symbols"]
        },
        "risk_management": {
            "type": "object",
            "properties": {
                "max_account_risk_percent": {"type": "number", "minimum": 0, "maximum": 100},
                "max_position_size_percent": {"type": "number", "minimum": 0, "maximum": 100},
                "max_daily_loss_percent": {"type": "number", "minimum": 0, "maximum": 100}
            },
            "required": ["max_account_risk_percent", "max_position_size_percent", "max_daily_loss_percent"]
        },
        "agents": {
            "type": "object",
            "properties": {
                "technical_analysis": {"type": "object"},
                "fundamental_analysis": {"type": "object"},
                "risk_management": {"type": "object"},
                "strategy_optimization": {"type": "object"},
                "trade_execution": {"type": "object"}
            },
            "required": []
        }
    },
    "required": ["system", "market_data", "risk_management", "agents"]
}

def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate the configuration against the schema
    
    Args:
        config: The configuration dictionary to validate
        
    Returns:
        A list of validation errors, empty if the configuration is valid
    """
    validator = jsonschema.Draft7Validator(CONFIG_SCHEMA)
    errors = list(validator.iter_errors(config))
    return [f"{error.path}: {error.message}" for error in errors]

def validate_config_file(file_path: str) -> Dict[str, Any]:
    """
    Load and validate a configuration file
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        The validated configuration dictionary
        
    Raises:
        ValueError: If the configuration is invalid
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    with open(file_path, "r") as f:
        config = json.load(f)
    
    errors = validate_config(config)
    if errors:
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    return config
