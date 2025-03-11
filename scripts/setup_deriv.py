
"""
Setup script for Deriv API integration.
This script will guide you through the process of setting up your Deriv API credentials.

Usage:
python scripts/setup_deriv.py
"""

import os
import json
import sys

def main():
    print("\n=== Deriv API Setup ===\n")
    print("This script will help you set up your Deriv API configuration.")
    print("You will need a Deriv API App ID to proceed.\n")
    
    # Check if settings file exists
    settings_path = "config/settings.json"
    if not os.path.exists("config"):
        os.makedirs("config")
    
    if not os.path.exists(settings_path):
        # If example file exists, copy it
        example_path = "config/settings.example.json"
        if os.path.exists(example_path):
            with open(example_path, 'r') as f_in:
                with open(settings_path, 'w') as f_out:
                    f_out.write(f_in.read())
            print(f"Created settings file from example.")
        else:
            # Create new minimal settings file
            with open(settings_path, 'w') as f:
                json.dump({
                    "system": {
                        "log_level": "INFO"
                    },
                    "agents": {}
                }, f, indent=2)
            print(f"Created new settings file.")
    
    # Load current settings
    with open(settings_path, 'r') as f:
        try:
            settings = json.load(f)
        except json.JSONDecodeError:
            print("Error: Settings file is not valid JSON. Please fix it manually.")
            return
    
    # Get Deriv API App ID
    print("\nTo get your Deriv API App ID, follow these steps:")
    print("1. Go to https://developers.deriv.com/ and create an account or log in")
    print("2. Create a new API token under 'Applications'")
    print("3. Copy the App ID provided by Deriv\n")
    
    app_id = input("Enter your Deriv API App ID: ").strip()
    
    if not app_id:
        print("Error: App ID cannot be empty.")
        return
    
    # Configure symbols mapping
    print("\nConfiguring forex symbol mappings...")
    standard_mapping = {
        "EUR/USD": "frxEURUSD",
        "GBP/USD": "frxGBPUSD",
        "USD/JPY": "frxUSDJPY",
        "USD/CHF": "frxUSDCHF",
        "AUD/USD": "frxAUDUSD"
    }
    
    # Update settings
    if "deriv_api" not in settings:
        settings["deriv_api"] = {}
    
    settings["deriv_api"]["app_id"] = app_id
    settings["deriv_api"]["endpoint"] = "wss://ws.binaryws.com/websockets/v3"
    settings["deriv_api"]["account_type"] = "demo"
    settings["deriv_api"]["symbols_mapping"] = standard_mapping
    settings["deriv_api"]["default_contract_type"] = "CALL/PUT"
    settings["deriv_api"]["default_duration"] = 5
    settings["deriv_api"]["default_duration_unit"] = "m"
    
    # Configure trade execution agent if needed
    if "agents" not in settings:
        settings["agents"] = {}
    
    if "trade_execution" not in settings["agents"]:
        settings["agents"]["trade_execution"] = {}
    
    # Ask user if they want to use the Deriv API for trade execution
    use_deriv = input("\nUse Deriv API for trade execution? (y/n): ").strip().lower()
    
    if use_deriv == 'y':
        settings["agents"]["trade_execution"]["gateway_type"] = "deriv"
        settings["agents"]["trade_execution"]["use_demo_account"] = True
        print("Configured trade execution agent to use Deriv API.")
    
    # Save updated settings
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print("\nDeriv API configuration saved successfully!")
    print(f"Settings file updated: {settings_path}")
    print("\nTo test your Deriv API integration, run:")
    print(f"  python examples/deriv_api_example.py --app_id {app_id}")
    print("\nTo run the full system with Deriv API:")
    print("  python main.py")

if __name__ == "__main__":
    main()
