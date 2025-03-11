#!/usr/bin/env python
"""
Setup script for Deriv API integration.
This script guides you through the process of setting up and testing your Deriv API credentials.

Usage:
python scripts/setup_deriv.py
"""

import os
import sys
import configparser
import json
import asyncio
import importlib.util
from pathlib import Path

# Import Deriv API client if available
try:
    from system.deriv_api_client import DerivApiClient
    deriv_api_available = True
except ImportError:
    deriv_api_available = False

async def test_api_connection(app_id, token):
    """
    Test the connection to Deriv API with the provided credentials.
    
    Args:
        app_id: The Deriv App ID
        token: The Demo API token
        
    Returns:
        bool: True if connection was successful, False otherwise
    """
    print("\nTesting connection to Deriv API...", end="", flush=True)
    try:
        # Save original environment variables to restore later
        original_app_id = os.environ.get("DERIV_APP_ID")
        original_token = os.environ.get("DERIV_DEMO_API_TOKEN")
        
        # Temporarily set environment variables for testing
        os.environ["DERIV_APP_ID"] = app_id
        os.environ["DERIV_DEMO_API_TOKEN"] = token
        
        # Initialize API client
        api_client = DerivApiClient(app_id)
        
        # Try to connect
        connected = await api_client.connect(retry_count=1)
        if not connected:
            print("\r❌ Failed to connect to Deriv API. Please check your credentials.")
            return False
        
        # Test API authorization
        ping_successful = await api_client.ping()
        if not ping_successful:
            print("\r❌ Connection established but API authorization failed.")
            return False
        
        # Get account balance to verify token works
        balance_data = await api_client.get_account_balance()
        if not balance_data or 'error' in balance_data:
            print("\r❌ Connection established but couldn't retrieve account information.")
            return False
        
        # Test successful, show account info
        currency = balance_data.get('currency', 'USD')
        balance = balance_data.get('balance', 0.0)
        print(f"\r✅ Successfully connected to Deriv API!")
        print(f"   Account type: DEMO")
        print(f"   Balance: {balance} {currency}")
        
        # Disconnect cleanly
        await api_client.disconnect()
        
        # Restore original environment if existed
        if original_app_id:
            os.environ["DERIV_APP_ID"] = original_app_id
        else:
            os.environ.pop("DERIV_APP_ID", None)
            
        if original_token:
            os.environ["DERIV_DEMO_API_TOKEN"] = original_token
        else:
            os.environ.pop("DERIV_DEMO_API_TOKEN", None)
            
        return True
        
    except Exception as e:
        print(f"\r❌ Error testing connection: {str(e)}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    # Check for websockets package with correct version
    try:
        websockets_spec = importlib.util.find_spec("websockets")
        if websockets_spec:
            import websockets
            if websockets.__version__ != "10.3":
                missing.append("websockets==10.3 (Found version: {})".format(websockets.__version__))
        else:
            missing.append("websockets==10.3")
    except (ImportError, AttributeError):
        missing.append("websockets==10.3")
    
    # Check for python-deriv-api package
    if not deriv_api_available:
        missing.append("python-deriv-api")
    
    return missing

async def main_async():
    print("\n=== Deriv API Setup Wizard ===\n")
    print("This wizard will help you configure your Deriv API credentials for the FTBA system.")
    
    # Check dependencies first
    missing_deps = check_dependencies()
    if missing_deps:
        print("\n⚠️ Warning: Some required dependencies are missing:")
        for dep in missing_deps:
            print(f"  - {dep}")
        
        print("\nPlease install the missing dependencies with:")
        print("  pip install -r requirements.txt")
        print("  pip install git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api\n")
        
        proceed = input("Do you want to continue anyway? (y/n): ").lower().strip()
        if proceed != 'y':
            print("\nExiting setup wizard. Please install the required dependencies and try again.")
            return
    
    print("\nYou will need:")
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
        
        # Test existing connection if dependencies are available
        if not missing_deps and deriv_api_available:
            test_existing = input("\nDo you want to test these credentials? (y/n): ").lower().strip()
            if test_existing == 'y':
                connection_successful = await test_api_connection(existing_app_id, existing_token)
                if connection_successful:
                    keep_existing = input("\nCredentials are working. Keep them? (y/n): ").lower().strip()
                    if keep_existing == 'y':
                        print("\nKeeping existing credentials. Setup completed!")
                        return
                else:
                    print("\nExisting credentials failed to connect. Let's set up new ones.")
        else:
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
    
    # Test new credentials if dependencies are available
    if not missing_deps and deriv_api_available:
        connection_successful = await test_api_connection(app_id, token)
        if not connection_successful:
            retry = input("\nConnection test failed. Do you want to continue anyway? (y/n): ").lower().strip()
            if retry != 'y':
                print("\nExiting setup. Please check your credentials and try again.")
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
        
        # For Replit environment, also update the current environment
        if os.environ.get('REPL_ID'):
            print("\nDetected Replit environment. Setting environment variables for current session...")
            os.environ["DERIV_APP_ID"] = app_id
            os.environ["DERIV_DEMO_API_TOKEN"] = token
            print("Environment variables set for current session.")
            print("For permanent storage, add these to your Replit Secrets.")
    
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
    print("\nFor a more extensive test with real trading functionality:")
    print("  python main.py --tradetest")

def main():
    """Run the async main function"""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main_async())

if __name__ == "__main__":
    main()