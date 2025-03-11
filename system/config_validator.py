
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum
import os


class ConfigValidationLevel(Enum):
    """Configuration validation severity levels"""
    WARNING = "warning"
    ERROR = "error"


class ConfigValidationResult:
    """Result of a configuration validation"""
    
    def __init__(self):
        self.warnings = []
        self.errors = []
    
    def add_warning(self, path: str, message: str) -> None:
        """
        Add a warning message
        
        Args:
            path: Configuration path that triggered the warning
            message: Warning message
        """
        self.warnings.append({"path": path, "message": message})
    
    def add_error(self, path: str, message: str) -> None:
        """
        Add an error message
        
        Args:
            path: Configuration path that triggered the error
            message: Error message
        """
        self.errors.append({"path": path, "message": message})
    
    def is_valid(self) -> bool:
        """
        Check if the configuration is valid (no errors)
        
        Returns:
            bool: True if valid, False if there are errors
        """
        return len(self.errors) == 0
    
    def has_warnings(self) -> bool:
        """
        Check if the configuration has warnings
        
        Returns:
            bool: True if there are warnings
        """
        return len(self.warnings) > 0
    
    def get_messages(self) -> List[str]:
        """
        Get all validation messages
        
        Returns:
            List[str]: All warning and error messages
        """
        messages = []
        for warning in self.warnings:
            messages.append(f"WARNING: {warning['path']} - {warning['message']}")
        for error in self.errors:
            messages.append(f"ERROR: {error['path']} - {error['message']}")
        return messages


class ConfigValidator:
    """Configuration validator for application configuration"""
    
    def __init__(self):
        self.logger = logging.getLogger("config_validator")
        self.schema = {
            "system": {
                "log_level": {
                    "type": "str",
                    "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "default": "INFO"
                },
                "data_directory": {"type": "str", "default": "./data"},
                "backup_directory": {"type": "str", "default": "./backups"}
            },
            "market_data": {
                "provider": {
                    "type": "str", 
                    "choices": ["simulation", "deriv", "alpha_vantage", "oanda"],
                    "default": "simulation"
                },
                "symbols": {"type": "list", "default": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"]}
            },
            "risk_management": {
                "max_account_risk_percent": {"type": "float", "min": 0.1, "max": 10.0, "default": 2.0},
                "max_position_size_percent": {"type": "float", "min": 0.1, "max": 20.0, "default": 5.0},
                "max_daily_loss_percent": {"type": "float", "min": 1.0, "max": 20.0, "default": 5.0}
            },
            "deriv_api": {
                "app_id": {"type": "str", "default": "1089"},
                "endpoint": {"type": "str", "default": "wss://ws.binaryws.com/websockets/v3"},
                "account_type": {"type": "str", "choices": ["demo", "real"], "default": "demo"},
                "symbols_mapping": {"type": "dict", "default": {
                    "EUR/USD": "frxEURUSD",
                    "GBP/USD": "frxGBPUSD",
                    "USD/JPY": "frxUSDJPY",
                    "USD/CHF": "frxUSDCHF"
                }},
                "default_contract_type": {"type": "str", "default": "CALL/PUT"},
                "default_duration": {"type": "int", "min": 1, "max": 60, "default": 5},
                "default_duration_unit": {"type": "str", "choices": ["t", "s", "m", "h", "d"], "default": "m"}
            },
            "agents": {
                "technical_analysis": {
                    "analysis_interval_seconds": {"type": "int", "min": 10, "max": 3600, "default": 60},
                    "signal_threshold": {"type": "float", "min": 0.1, "max": 1.0, "default": 0.7}
                },
                "fundamental_analysis": {
                    "update_interval_seconds": {"type": "int", "min": 60, "max": 3600, "default": 300}
                },
                "risk_management": {
                    "update_interval_seconds": {"type": "int", "min": 10, "max": 600, "default": 60}
                },
                "strategy_optimization": {
                    "update_interval_seconds": {"type": "int", "min": 60, "max": 3600, "default": 300},
                    "learning_rate": {"type": "float", "min": 0.01, "max": 0.5, "default": 0.1}
                },
                "asset_selection": {
                    "check_interval_seconds": {"type": "int", "min": 10, "max": 600, "default": 60},
                    "trading_hours_tolerance_minutes": {"type": "int", "min": 0, "max": 120, "default": 30},
                    "primary_assets": {"type": "list", "default": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]},
                    "fallback_assets": {"type": "list", "default": ["USD/CAD", "NZD/USD", "EUR/GBP"]}
                },
                "trade_execution": {
                    "check_interval_seconds": {"type": "int", "min": 1, "max": 60, "default": 1},
                    "slippage_model": {"type": "str", "choices": ["fixed", "proportional"], "default": "fixed"},
                    "fixed_slippage_pips": {"type": "float", "min": 0.1, "max": 10.0, "default": 1.0},
                    "gateway_type": {"type": "str", "choices": ["simulation", "deriv", "oanda"], "default": "simulation"},
                    "use_demo_account": {"type": "bool", "default": True}
                }
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """
        Validate a configuration dictionary against the schema
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            ConfigValidationResult: Validation result with warnings and errors
        """
        result = ConfigValidationResult()
        
        # Validate against schema
        self._validate_section(config, self.schema, "", result)
        
        # Check for specific logical validations
        self._validate_specific_requirements(config, result)
        
        return result
    
    def _validate_section(self, config: Dict[str, Any], schema: Dict[str, Any], 
                        path: str, result: ConfigValidationResult) -> None:
        """
        Recursively validate a configuration section
        
        Args:
            config: Configuration section
            schema: Schema section
            path: Current path in the configuration
            result: Validation result to update
        """
        # Check for missing required sections
        for key, schema_item in schema.items():
            current_path = f"{path}.{key}" if path else key
            
            # If this is a leaf schema item with type
            if "type" in schema_item:
                if key not in config:
                    if "default" in schema_item:
                        result.add_warning(current_path, f"Missing field, will use default: {schema_item['default']}")
                    else:
                        result.add_error(current_path, "Required field is missing")
                else:
                    self._validate_value(config[key], schema_item, current_path, result)
            # Otherwise it's a nested section
            elif key not in config:
                result.add_warning(current_path, "Missing section")
            else:
                # Recursively validate nested section
                if isinstance(config[key], dict) and isinstance(schema_item, dict):
                    self._validate_section(config[key], schema_item, current_path, result)
                else:
                    result.add_error(current_path, f"Expected a configuration section, got {type(config[key]).__name__}")
        
        # Check for unknown sections
        for key in config:
            current_path = f"{path}.{key}" if path else key
            if key not in schema:
                result.add_warning(current_path, "Unknown configuration item")
    
    def _validate_value(self, value: Any, schema_item: Dict[str, Any], 
                      path: str, result: ConfigValidationResult) -> None:
        """
        Validate a single configuration value
        
        Args:
            value: Value to validate
            schema_item: Schema for this value
            path: Current path in the configuration
            result: Validation result to update
        """
        expected_type = schema_item["type"]
        
        # Type validation
        if expected_type == "str" and not isinstance(value, str):
            result.add_error(path, f"Expected string, got {type(value).__name__}")
            return
        elif expected_type == "int" and not isinstance(value, int):
            result.add_error(path, f"Expected integer, got {type(value).__name__}")
            return
        elif expected_type == "float" and not (isinstance(value, (int, float))):
            result.add_error(path, f"Expected number, got {type(value).__name__}")
            return
        elif expected_type == "bool" and not isinstance(value, bool):
            result.add_error(path, f"Expected boolean, got {type(value).__name__}")
            return
        elif expected_type == "list" and not isinstance(value, list):
            result.add_error(path, f"Expected list, got {type(value).__name__}")
            return
        elif expected_type == "dict" and not isinstance(value, dict):
            result.add_error(path, f"Expected dictionary, got {type(value).__name__}")
            return
        
        # Constraints validation
        if "min" in schema_item and value < schema_item["min"]:
            result.add_error(path, f"Value {value} is below minimum {schema_item['min']}")
        
        if "max" in schema_item and value > schema_item["max"]:
            result.add_error(path, f"Value {value} is above maximum {schema_item['max']}")
        
        if "choices" in schema_item and value not in schema_item["choices"]:
            result.add_error(path, f"Value '{value}' not in allowed choices: {', '.join(schema_item['choices'])}")
    
    def _validate_specific_requirements(self, config: Dict[str, Any], result: ConfigValidationResult) -> None:
        """
        Validate specific logical requirements that span multiple configuration items
        
        Args:
            config: Configuration dictionary
            result: Validation result to update
        """
        # Example: Check that risk_management.max_account_risk_percent is lower than max_daily_loss_percent
        if "risk_management" in config:
            rm_config = config["risk_management"]
            if "max_account_risk_percent" in rm_config and "max_daily_loss_percent" in rm_config:
                if rm_config["max_account_risk_percent"] > rm_config["max_daily_loss_percent"]:
                    result.add_warning(
                        "risk_management",
                        "max_account_risk_percent should be lower than max_daily_loss_percent"
                    )
        
        # Ensure required directories exist
        if "system" in config:
            sys_config = config["system"]
            if "data_directory" in sys_config:
                data_dir = sys_config["data_directory"]
                if not os.path.exists(data_dir):
                    result.add_warning(
                        "system.data_directory",
                        f"Directory '{data_dir}' does not exist. It will be created."
                    )
    
    def validate_config_file(self, filepath: str) -> Tuple[Optional[Dict[str, Any]], ConfigValidationResult]:
        """
        Load and validate a configuration file
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            Tuple containing:
            - Dict: The loaded configuration if successful, None if errors occurred
            - ConfigValidationResult: Validation result
        """
        result = ConfigValidationResult()
        
        try:
            with open(filepath, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error("file", f"Invalid JSON: {str(e)}")
            return None, result
        except Exception as e:
            result.add_error("file", f"Error reading file: {str(e)}")
            return None, result
        
        # Validate the loaded configuration
        validation_result = self.validate_config(config)
        
        # Combine validation results
        for warning in validation_result.warnings:
            result.add_warning(warning["path"], warning["message"])
        for error in validation_result.errors:
            result.add_error(error["path"], error["message"])
        
        if result.is_valid():
            return config, result
        else:
            return None, result
    
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values to missing configuration items
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dict: Configuration with defaults applied
        """
        result = config.copy()
        self._apply_defaults_section(result, self.schema)
        return result
    
    def _apply_defaults_section(self, config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Recursively apply defaults to a configuration section
        
        Args:
            config: Configuration section to update
            schema: Schema section
        """
        for key, schema_item in schema.items():
            # If this is a leaf schema item with type
            if "type" in schema_item:
                if key not in config and "default" in schema_item:
                    config[key] = schema_item["default"]
            # Otherwise it's a nested section
            elif key not in config:
                config[key] = {}
            
            # Recursively apply defaults to nested sections
            if key in config and isinstance(config[key], dict) and isinstance(schema_item, dict) and "type" not in schema_item:
                self._apply_defaults_section(config[key], schema_item)

def validate_configuration(config_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a configuration file and apply defaults
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Tuple containing:
        - bool: True if valid, False if there are errors
        - Dict: Validated configuration with defaults applied
    """
    logger = logging.getLogger("config_validation")
    validator = ConfigValidator()
    
    # Validate the configuration file
    config, result = validator.validate_config_file(config_path)
    
    # Log warnings and errors
    for message in result.get_messages():
        if message.startswith("WARNING"):
            logger.warning(message)
        else:
            logger.error(message)
    
    if not result.is_valid():
        logger.error("Configuration validation failed")
        return False, {}
    
    # Apply defaults
    config_with_defaults = validator.apply_defaults(config)
    
    logger.info("Configuration validation successful")
    return True, config_with_defaults
