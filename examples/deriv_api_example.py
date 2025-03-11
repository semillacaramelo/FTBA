
"""
Example script for testing the Deriv API integration.
This can be run separately to test the API before integrating with the full system.

Usage:
python examples/deriv_api_example.py --app_id YOUR_APP_ID
"""

import argparse
import asyncio
import logging
import sys
import os

# Add the parent directory to sys.path to allow imports from the system module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from system.deriv_api_client import DerivApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("deriv_example")

async def run_example(app_id):
    # Initialize the client
    client = DerivApiClient(app_id=app_id)
    
    # Connect to API
    logger.info("Connecting to Deriv API...")
    connected = await client.connect()
    
    if not connected:
        logger.error("Failed to connect to Deriv API")
        return
    
    try:
        # Ping the API
        logger.info("Pinging API...")
        ping_result = await client.ping()
        logger.info(f"Ping result: {ping_result}")
        
        # Get active symbols for forex
        logger.info("Getting forex symbols...")
        symbols = await client.get_active_symbols(market_type="forex")
        logger.info(f"Found {len(symbols)} forex symbols")
        
        # Print first few symbols
        for s in symbols[:5]:
            logger.info(f"Symbol: {s.get('symbol')}, Name: {s.get('display_name')}")
        
        # Get account balance
        logger.info("Getting account balance...")
        balance = await client.get_account_balance()
        logger.info(f"Account balance: {balance}")
        
        # Get price proposal
        if symbols:
            symbol = symbols[0]['symbol']
            logger.info(f"Getting price proposal for {symbol}...")
            proposal = await client.get_price_proposal(
                symbol=symbol,
                contract_type="CALL",
                amount=10.0,
                duration=5,
                duration_unit="m"
            )
            logger.info(f"Proposal: {proposal}")
    
    finally:
        # Disconnect from API
        logger.info("Disconnecting from Deriv API...")
        await client.disconnect()

def main():
    parser = argparse.ArgumentParser(description="Deriv API example")
    parser.add_argument("--app_id", required=True, help="Deriv App ID")
    args = parser.parse_args()
    
    asyncio.run(run_example(args.app_id))

if __name__ == "__main__":
    main()
