#!/usr/bin/env python3
"""
Configuration management module for the FTBA application.
"""

import os
import json
from typing import Dict, Any, Optional

class Config:
    """Configuration manager class"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_data = {}
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config_data = json.load(f)
        
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value
        
        Args:
            section: Configuration section name
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        if section in self.config_data and key in self.config_data[section]:
            return self.config_data[section][key]
        return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value
        
        Args:
            section: Configuration section name
            key: Configuration key
            value: Value to set
        """
        if section not in self.config_data:
            self.config_data[section] = {}
        
        self.config_data[section][key] = value
    
    def save(self, config_path: str) -> None:
        """
        Save configuration to file
        
        Args:
            config_path: Path to save configuration
        """
        with open(config_path, 'w') as f:
            json.dump(self.config_data, f, indent=4)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section
        
        Args:
            section: Configuration section name
            
        Returns:
            Dictionary with section configuration or empty dict if not found
        """
        return self.config_data.get(section, {})