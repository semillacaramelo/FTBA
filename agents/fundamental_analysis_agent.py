
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, Confidence, 
    FundamentalUpdate
)

class FundamentalAnalysisAgent(Agent):
    """
    Agent responsible for analyzing economic news, events, and indicators
    to assess macro-economic impacts on currency values.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict = None):
        """
        Initialize the Fundamental Analysis Agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker for communication
            config: Agent configuration dictionary
        """
        super().__init__(agent_id, message_broker)
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.update_interval = self.config.get("update_interval_seconds", 300)
        self.economic_calendar = []
        self.last_processed_time = datetime.utcnow()
    
    async def setup(self):
        """Initialize the agent"""
        self.logger.info("Setting up Fundamental Analysis Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.TRADE_RESULT  # To learn from past trades
        ])
        
        # Initial loading of economic calendar
        await self.load_economic_calendar()
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Fundamental Analysis Agent")
    
    async def process_cycle(self):
        """Main processing cycle"""
        # Check if it's time to update
        current_time = datetime.utcnow()
        if (current_time - self.last_processed_time).total_seconds() >= self.update_interval:
            self.logger.debug("Running fundamental analysis cycle")
            
            # Process economic news and events
            await self.process_economic_events()
            
            # Process news impact
            await self.process_news_impact()
            
            # Update the last processed time
            self.last_processed_time = current_time
        
        # Sleep to prevent CPU spinning
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.SYSTEM_STATUS:
            # Handle system status messages (e.g., initialization, shutdown)
            pass
        elif message.type == MessageType.TRADE_RESULT:
            # Learn from trade results to improve future analyses
            pass
    
    async def load_economic_calendar(self):
        """Load upcoming economic events from data source"""
        # In a real implementation, this would load data from an API or database
        # For this example, we'll create some sample data
        self.logger.info("Loading economic calendar")
        
        # Sample economic events for the next week
        self.economic_calendar = [
            {
                "event": "US Non-Farm Payrolls",
                "datetime": datetime.utcnow() + timedelta(days=1),
                "currency": "USD",
                "impact": "HIGH",
                "forecast": 200000,
                "previous": 180000
            },
            {
                "event": "ECB Interest Rate Decision",
                "datetime": datetime.utcnow() + timedelta(days=2),
                "currency": "EUR",
                "impact": "HIGH",
                "forecast": 0.0,
                "previous": 0.0
            },
            {
                "event": "UK GDP",
                "datetime": datetime.utcnow() + timedelta(days=3),
                "currency": "GBP",
                "impact": "MEDIUM",
                "forecast": 0.3,
                "previous": 0.2
            }
        ]
    
    async def process_economic_events(self):
        """Process upcoming and recent economic events"""
        self.logger.info("Processing economic events")
        current_time = datetime.utcnow()
        
        # Find events that are coming up or recently occurred
        upcoming_events = []
        for event in self.economic_calendar:
            event_time = event["datetime"]
            time_diff = (event_time - current_time).total_seconds()
            
            # If event is in the next 4 hours or occurred in the last hour
            if -3600 <= time_diff <= 14400:
                upcoming_events.append(event)
        
        # Process each relevant event
        updates_to_send = []
        for event in upcoming_events:
            # For upcoming events, assess potential impact
            if event["datetime"] > current_time:
                impact_assessment = Direction.NEUTRAL
                confidence = Confidence.MEDIUM
                
                # Higher impact events get higher confidence
                if event["impact"] == "HIGH":
                    confidence = Confidence.HIGH
                
                update = FundamentalUpdate(
                    event=event["event"],
                    impact_currency=[event["currency"]],
                    impact_assessment=impact_assessment,
                    confidence=confidence,
                    forecast=event.get("forecast"),
                    previous=event.get("previous"),
                    source="Economic Calendar"
                )
                updates_to_send.append(update)
            
            # For past events, assess actual impact (in a real system, we'd have actual values)
            else:
                # Simulate actual values for demonstration
                actual_value = event.get("forecast", 0) * (1 + (0.1 * (2 * (0.5 - 0.5))))
                
                # Determine impact
                impact_assessment, confidence = self.determine_event_impact(event, actual_value)
                
                update = FundamentalUpdate(
                    event=event["event"],
                    impact_currency=[event["currency"]],
                    impact_assessment=impact_assessment,
                    confidence=confidence,
                    forecast=event.get("forecast"),
                    previous=event.get("previous"),
                    actual=actual_value,
                    source="Economic Calendar"
                )
                updates_to_send.append(update)
        
        # Send updates to other agents
        for update in updates_to_send:
            await self.send_message(
                MessageType.FUNDAMENTAL_UPDATE,
                {
                    "update": update.__dict__,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            self.logger.info(f"Sent fundamental update for {update.event}")
    
    async def process_news_impact(self):
        """Process recent news and assess impact on currencies"""
        # In a real implementation, this would process news from various sources
        # For this example, we'll skip implementation details
        pass
    
    def determine_event_impact(self, event: Dict, actual_value: float):
        """Determine the impact of an economic event based on actual vs expected values"""
        # Implementation would assess the significance of deviation from forecast
        # and determine both impact direction and confidence level
        
        # For demonstration purposes:
        forecast = event.get("forecast", 0)
        if forecast == 0:
            return Direction.NEUTRAL, Confidence.LOW
        
        deviation = (actual_value - forecast) / forecast if forecast != 0 else 0
        
        # Determine direction
        if abs(deviation) < 0.01:
            direction = Direction.NEUTRAL
        elif deviation > 0:
            direction = Direction.LONG if event["currency"] == "USD" else Direction.SHORT
        else:
            direction = Direction.SHORT if event["currency"] == "USD" else Direction.LONG
        
        # Determine confidence
        if abs(deviation) < 0.01:
            confidence = Confidence.LOW
        elif abs(deviation) < 0.05:
            confidence = Confidence.MEDIUM
        else:
            confidence = Confidence.HIGH
        
        return direction, confidence
