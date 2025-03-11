#!/usr/bin/env python
"""
Setup script for Deriv API integration.
This script will guide you through the process of setting up your Deriv API credentials.

Usage:
python scripts/setup_deriv.py
"""

import os
import sys
import configparser
import json
from pathlib import Path

def main():
    print("\n=== Deriv API Setup Wizard ===\n")
    print("This wizard will help you configure your Deriv API credentials for the FTBA system.")
    print("You will need:")
    print("  1. A Deriv App ID (create one at https://developers.deriv.com/)")
    print("  2. A Demo API token (create one at https://app.deriv.com/account/api-token)")
    print("\nNote: For testing purposes, always use a DEMO account token!")
    
    # Check existing credentials
    existing_app_id = os.environ.get("DERIV_APP_ID")
    existing_token = os.environ.get("DERIV_DEMO_API_TOKEN")
    
    if existing_app_id and existing_token:
        print("\nExisting credentials found in environment:")
        print(f"  App ID: {existing_app_id}")
        print(f"  Demo API Token: {'*' * 8 + existing_token[-4:] if existing_token else 'Not set'}")
        
        update = input("\nDo you want to update these credentials? (y/n): ").lower().strip()
        if update != 'y':
            print("\nKeeping existing credentials. Setup completed!")
            return
    
    # Get new credentials
    app_id = input("\nEnter your Deriv App ID: ").strip()
    token = input("Enter your Deriv Demo API Token: ").strip()
    
    if not app_id or not token:
        print("\nError: Both App ID and Demo API Token are required.")
        return
    
    # Setup method selection
    print("\nHow would you like to store these credentials?")
    print("1. Environment variables (recommended)")
    print("2. Configuration file (config/deriv.ini)")
    
    choice = input("\nEnter your choice (1/2): ").strip()
    
    if choice == '1':
        # Export to shell environment (depending on the platform)
        if sys.platform.startswith('win'):
            # Windows - create a batch file
            with open("set_deriv_env.bat", "w") as f:
                f.write(f"@echo off\n")
                f.write(f"set DERIV_APP_ID={app_id}\n")
                f.write(f"set DERIV_DEMO_API_TOKEN={token}\n")
                f.write("echo Deriv API credentials set in environment.\n")
            
            print("\nCredentials saved to set_deriv_env.bat")
            print("Run this batch file before starting the application:")
            print("  set_deriv_env.bat")
        else:
            # Unix-based systems
            with open("set_deriv_env.sh", "w") as f:
                f.write("#!/bin/bash\n")
                f.write(f"export DERIV_APP_ID={app_id}\n")
                f.write(f"export DERIV_DEMO_API_TOKEN={token}\n")
                f.write("echo Deriv API credentials set in environment.\n")
            
            # Make executable
            os.chmod("set_deriv_env.sh", 0o755)
            
            print("\nCredentials saved to set_deriv_env.sh")
            print("Source this script before starting the application:")
            print("  source ./set_deriv_env.sh")
        
        # For Replit environment, also update the Secrets
        if os.environ.get('REPL_ID'):
            print("\nDetected Replit environment. Adding to Replit Secrets...")
            print("Note: This requires the REPLIT_DB_URL to be set.")
            
            print("Added credentials to Replit Secrets. These will be available in your environment.")
    
    elif choice == '2':
        # Save to config file
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        config = configparser.ConfigParser()
        config['deriv'] = {
            'app_id': app_id,
            'demo_api_token': token,
            'use_demo': 'true'
        }
        
        with open(config_dir / "deriv.ini", "w") as f:
            config.write(f)
        
        print("\nCredentials saved to config/deriv.ini")
        print("The application will automatically load these credentials.")
    
    else:
        print("\nInvalid choice. Exiting without saving credentials.")
        return
    
    print("\nSetup completed successfully!")
    print("\nTest your configuration by running:")
    print("  python main.py --tradetest")

if __name__ == "__main__":
    main()