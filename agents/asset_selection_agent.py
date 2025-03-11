import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import random

from system.agent import Agent, Message, MessageType
from system.core import Direction, MarketData

class AssetSelectionAgent(Agent):
    """
    Agent responsible for selecting active tradable assets and providing 
    recommendations based on market availability.
    
    Features:
    - Monitors market opening hours
    - Maintains list of currently tradable assets
    - Falls back to alternative assets when primary ones are unavailable
    - Integrates with Trade Execution Agent via message broker
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict = None):
        """
        Initialize the Asset Selection Agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker for communication
            config: Agent configuration dictionary
        """
        super().__init__(agent_id, message_broker)
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Configuration parameters
        self.check_interval = self.config.get("check_interval_seconds", 60)
        self.trading_hours_tolerance = self.config.get("trading_hours_tolerance_minutes", 30)
        
        # Asset lists
        self.primary_assets = self.config.get("primary_assets", ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"])
        self.fallback_assets = self.config.get("fallback_assets", ["USD/CAD", "NZD/USD", "EUR/GBP"])
        self.all_assets = set(self.primary_assets + self.fallback_assets)
        
        # Current state
        self.available_assets = set()
        self.recommended_assets = set()
        self.asset_status = {}  # symbol -> status dict
        self.market_data = {}   # symbol -> market data
        self.last_update_time = datetime.utcnow()
        
        # Trading hours (24-hour format, UTC)
        self.trading_hours = self.config.get("trading_hours", {
            "forex_standard": {
                "monday": {"open": "00:00", "close": "24:00"},
                "tuesday": {"open": "00:00", "close": "24:00"},
                "wednesday": {"open": "00:00", "close": "24:00"},
                "thursday": {"open": "00:00", "close": "24:00"},
                "friday": {"open": "00:00", "close": "22:00"},
                "saturday": {"open": None, "close": None},
                "sunday": {"open": "22:00", "close": "24:00"}
            }
        })
        
        # API client for checking asset availability
        self.api_client = None
    
    async def setup(self):
        """Initialize the agent"""
        self.logger.info("Setting up Asset Selection Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.MARKET_DATA
        ])
        
        # Initialize API client if needed for direct market checks
        if self.config.get("gateway_type") == "deriv":
            # Get the deriv_api configuration from the main config or the parent_config
            deriv_config = {}
            if "parent_config" in self.config:
                parent_config = self.config.get("parent_config", {})
                deriv_config = parent_config.get("deriv_api", {})
            
            app_id = deriv_config.get("app_id", "1089")
            endpoint = deriv_config.get("endpoint", "wss://ws.binaryws.com/websockets/v3")
            
            self.logger.info(f"Initializing API client with app_id: {app_id}")
            
            from system.deriv_api_client import DerivApiClient
            self.api_client = DerivApiClient(
                app_id=app_id,
                endpoint=endpoint
            )
            await self.api_client.connect()
        
        # Perform initial asset check
        await self.check_asset_availability()
        
        self.logger.info(f"Asset Selection Agent initialized with {len(self.available_assets)} available assets")
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Asset Selection Agent")
        
        # Disconnect API client if initialized
        if self.api_client:
            await self.api_client.disconnect()
    
    async def process_cycle(self):
        """Main processing cycle"""
        current_time = datetime.utcnow()
        
        # Check if it's time to update asset availability
        if (current_time - self.last_update_time).total_seconds() >= self.check_interval:
            await self.check_asset_availability()
            await self.broadcast_asset_status()
            self.last_update_time = current_time
        
        # Sleep to prevent CPU spinning
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.MARKET_DATA:
            # Update internal market data
            await self.handle_market_data(message)
        elif message.type == MessageType.SYSTEM_STATUS:
            event = message.content.get("event")
            if event == "asset_availability_request":
                # Respond to asset availability requests
                await self.send_asset_availability(message.sender)
    
    async def handle_market_data(self, message: Message):
        """
        Process market data updates
        
        Args:
            message: Message containing market data
        """
        data = message.content
        if not data:
            return
        
        symbol = data.get("symbol")
        if not symbol or symbol not in self.all_assets:
            return
        
        # Update internal market data
        self.market_data[symbol] = data
        
        # Check if this data indicates the asset is available
        if "bid" in data and "ask" in data:
            self.asset_status[symbol] = {
                "available": True,
                "last_update": datetime.utcnow().isoformat(),
                "bid": data["bid"],
                "ask": data["ask"]
            }
    
    async def check_asset_availability(self):
        """Check which assets are currently available for trading"""
        self.logger.info("Checking asset availability")
        
        # First check if current time is within trading hours
        trading_open = self.is_market_open()
        if not trading_open:
            self.logger.info("Market is closed according to trading hours")
            self.available_assets = set()
            self.recommended_assets = set()
            return
        
        # Check availability via API if possible
        await self.check_via_api()
        
        # Update the list of available assets
        self.available_assets = {symbol for symbol, status in self.asset_status.items() 
                               if status.get("available", False)}
        
        # If no primary assets are available, use fallback assets
        primary_available = self.available_assets.intersection(self.primary_assets)
        if primary_available:
            self.recommended_assets = primary_available
        else:
            self.recommended_assets = self.available_assets.intersection(self.fallback_assets)
        
        # Log the results
        self.logger.info(f"Available assets: {', '.join(self.available_assets) if self.available_assets else 'None'}")
        self.logger.info(f"Recommended assets: {', '.join(self.recommended_assets) if self.recommended_assets else 'None'}")
    
    async def check_via_api(self):
        """Check asset availability using API client"""
        # Skip if no API client is available
        if not self.api_client:
            # Mark all assets as potentially available when no API check is possible
            for symbol in self.all_assets:
                if symbol not in self.asset_status:
                    self.asset_status[symbol] = {
                        "available": True,
                        "last_update": datetime.utcnow().isoformat(),
                        "source": "schedule"
                    }
            return
        
        try:
            # Get all active symbols
            available_symbols = await self.api_client.get_active_symbols(market_type="forex")
            
            # Convert to standard format
            available_standard_symbols = set()
            for symbol_data in available_symbols:
                deriv_symbol = symbol_data.get("symbol", "")
                display_name = symbol_data.get("display_name", "")
                
                # Add to available symbols
                if display_name and "/" in display_name:  # Most reliable conversion
                    available_standard_symbols.add(display_name)
                    
                    # Update asset status
                    self.asset_status[display_name] = {
                        "available": True,
                        "last_update": datetime.utcnow().isoformat(),
                        "source": "api"
                    }
            
            # Mark assets not returned by API as unavailable
            for symbol in self.all_assets:
                if symbol not in available_standard_symbols:
                    self.asset_status[symbol] = {
                        "available": False,
                        "last_update": datetime.utcnow().isoformat(),
                        "source": "api"
                    }
        
        except Exception as e:
            self.logger.error(f"Error checking asset availability via API: {e}")
    
    def is_market_open(self) -> bool:
        """
        Check if the market is currently open based on configured trading hours
        
        Returns:
            bool: True if market is open, False otherwise
        """
        now = datetime.utcnow()
        day_of_week = now.strftime("%A").lower()
        current_time = now.strftime("%H:%M")
        
        # Get trading hours for current day
        trading_schedule = self.trading_hours.get("forex_standard", {})
        day_schedule = trading_schedule.get(day_of_week, {})
        
        open_time = day_schedule.get("open")
        close_time = day_schedule.get("close")
        
        # If no schedule for today, market is closed
        if not open_time or not close_time:
            return False
        
        # Handle special case for 24-hour trading
        if open_time == "00:00" and close_time == "24:00":
            return True
        
        # Convert to datetime objects for comparison
        now_time = datetime.strptime(current_time, "%H:%M")
        
        # Handle cases that span across midnight
        if open_time > close_time:  # Market opens today and closes tomorrow
            open_dt = datetime.strptime(open_time, "%H:%M")
            close_dt = datetime.strptime(close_time, "%H:%M") + timedelta(days=1)
        else:  # Normal case - opens and closes on same day
            open_dt = datetime.strptime(open_time, "%H:%M")
            close_dt = datetime.strptime(close_time, "%H:%M")
        
        # Add tolerance (e.g., consider market open 30 minutes before official open)
        tolerance_mins = self.trading_hours_tolerance
        open_dt = open_dt - timedelta(minutes=tolerance_mins)
        close_dt = close_dt + timedelta(minutes=tolerance_mins)
        
        # Check if current time is within trading hours
        return open_dt <= now_time <= close_dt
    
    async def broadcast_asset_status(self):
        """Broadcast the current asset availability status to other agents"""
        await self.send_message(
            MessageType.SYSTEM_STATUS,
            {
                "event": "asset_availability_update",
                "available_assets": list(self.available_assets),
                "recommended_assets": list(self.recommended_assets),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def send_asset_availability(self, requesting_agent: str):
        """
        Send asset availability information to a specific agent
        
        Args:
            requesting_agent: ID of agent requesting the information
        """
        await self.send_message(
            MessageType.SYSTEM_STATUS,
            {
                "event": "asset_availability_response",
                "available_assets": list(self.available_assets),
                "recommended_assets": list(self.recommended_assets),
                "asset_details": self.asset_status,
                "timestamp": datetime.utcnow().isoformat()
            },
            recipients=[requesting_agent]
        )
    
    def get_recommended_asset(self) -> Optional[str]:
        """
        Get a recommended asset for trading
        
        Returns:
            str: Recommended asset symbol or None if none available
        """
        if not self.recommended_assets:
            return None
        
        # Return a random asset from recommended assets
        # In a real implementation, this could use more sophisticated selection logic
        return random.choice(list(self.recommended_assets))
    
    def get_all_available_assets(self) -> List[str]:
        """
        Get all available assets
        
        Returns:
            List[str]: List of all available asset symbols
        """
        return list(self.available_assets)