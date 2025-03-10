import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import re

from system.agent import Agent
from system.core import (
    Message, MessageType, Direction, Confidence, 
    FundamentalUpdate
)

class FundamentalAnalysisAgent(Agent):
    def __init__(self, agent_id: str, message_broker, config):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.economic_calendar = pd.DataFrame()  # Economic events
        self.news_sentiment = {}  # Currency -> sentiment score
        self.central_bank_rates = {}  # Currency -> interest rate
        self.inflation_data = {}  # Currency -> inflation rate
        self.update_interval = config.get("update_interval_seconds", 300)  # 5 minutes
        self.last_update_time = datetime.min
        self.currencies_to_monitor = config.get("currencies", ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"])
        self.sentiment_threshold = config.get("sentiment_threshold", 0.3)
    
    async def setup(self):
        """Set up the agent when starting"""
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.TRADE_RESULT
        ])
        await self.load_economic_calendar()
        await self.initialize_market_data()
        self.logger.info(f"Fundamental Analysis Agent setup complete. Monitoring {len(self.currencies_to_monitor)} currencies")
    
    async def cleanup(self):
        """Clean up when agent is stopping"""
        self.economic_calendar = pd.DataFrame()
        self.news_sentiment = {}
        self.logger.info("Fundamental Analysis Agent cleaned up")
    
    async def process_cycle(self):
        """Process a single cycle of the agent's main loop"""
        now = datetime.utcnow()
        
        # Check if it's time to update data
        time_since_last = (now - self.last_update_time).total_seconds()
        if time_since_last >= self.update_interval:
            await self.update_economic_data()
            await self.update_news_sentiment()
            await self.analyze_and_broadcast()
            self.last_update_time = now
        
        # Check for upcoming high-impact events
        await self.check_upcoming_events()
        
        # Wait to maintain the desired update frequency
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.SYSTEM_STATUS:
            # Handle system status updates
            pass
        elif message.type == MessageType.TRADE_RESULT:
            # Learn from trade results to improve analysis
            if message.content.get("successful"):
                await self.evaluate_forecast_accuracy(message.content)
    
    async def load_economic_calendar(self):
        """Load the economic calendar from data provider"""
        # In a real implementation, this would fetch from an API
        # Simulating with a basic structure
        self.economic_calendar = pd.DataFrame({
            'datetime': pd.date_range(start=datetime.utcnow(), periods=20, freq='H'),
            'currency': ['USD', 'EUR', 'JPY', 'GBP', 'USD', 'EUR', 'USD', 'CAD', 'AUD', 'USD',
                         'USD', 'EUR', 'JPY', 'GBP', 'USD', 'EUR', 'USD', 'CAD', 'AUD', 'USD'],
            'event': ['Non-Farm Payrolls', 'CPI', 'Interest Rate', 'GDP', 'Retail Sales', 
                      'Unemployment Rate', 'ISM Manufacturing', 'GDP', 'CPI', 'FOMC Meeting',
                      'Core PCE', 'ECB Speech', 'BOJ Meeting', 'BOE Rate', 'Durable Goods', 
                      'German IFO', 'ISM Services', 'Employment', 'RBA Rate', 'Trade Balance'],
            'importance': ['high', 'high', 'high', 'medium', 'medium', 
                          'high', 'medium', 'high', 'medium', 'high',
                          'high', 'medium', 'high', 'high', 'medium', 
                          'medium', 'medium', 'high', 'high', 'low'],
            'forecast': [200, 2.3, 0.5, 3.2, 0.4, 
                         7.2, 52.1, 2.8, 3.5, None,
                         0.3, None, -0.1, 0.25, 0.5, 
                         95.2, 54.5, 35000, 4.35, -2.5],
            'previous': [175, 2.2, 0.5, 3.0, 0.3, 
                         7.4, 51.8, 2.5, 3.6, None,
                         0.2, None, -0.1, 0.25, 0.2, 
                         94.8, 53.2, 32000, 4.35, -3.1]
        })
        
        # Make datetimes more realistic and within the next week
        start = datetime.utcnow()
        self.economic_calendar['datetime'] = [
            start + timedelta(hours=i*12) for i in range(len(self.economic_calendar))
        ]
        
        self.logger.info(f"Loaded economic calendar with {len(self.economic_calendar)} events")
    
    async def initialize_market_data(self):
        """Initialize market data structures"""
        for currency in self.currencies_to_monitor:
            # Initial sentiment is neutral
            self.news_sentiment[currency] = 0.0
            
            # Sample interest rates
            self.central_bank_rates[currency] = {
                'USD': 5.25, 'EUR': 4.0, 'GBP': 5.25, 'JPY': -0.1,
                'CHF': 1.75, 'CAD': 5.0, 'AUD': 4.1, 'NZD': 5.5
            }.get(currency, 0.0)
            
            # Sample inflation data
            self.inflation_data[currency] = {
                'USD': 3.1, 'EUR': 2.6, 'GBP': 2.0, 'JPY': 2.8,
                'CHF': 1.0, 'CAD': 2.9, 'AUD': 2.7, 'NZD': 4.0
            }.get(currency, 2.0)
    
    async def update_economic_data(self):
        """Update economic data from official sources"""
        # In a real implementation, this would fetch data from APIs
        # Simulating small random changes
        for currency in self.currencies_to_monitor:
            # Slightly adjust rates and inflation with small random variations
            if currency in self.central_bank_rates:
                variation = (0.5 - (1 * 0.5)) * 0.01  # +/- 0.01
                self.central_bank_rates[currency] += variation
            
            if currency in self.inflation_data:
                variation = (0.5 - (1 * 0.5)) * 0.1  # +/- 0.1
                self.inflation_data[currency] += variation
        
        self.logger.debug("Updated economic data")
    
    async def update_news_sentiment(self):
        """Update news sentiment data"""
        # In a real implementation, this would parse news from APIs
        # Simulating sentiment changes
        for currency in self.currencies_to_monitor:
            # Generate a random sentiment change (-0.2 to +0.2)
            change = (0.5 - (1 * 0.5)) * 0.4
            
            # Update sentiment, keeping it between -1 and 1
            current = self.news_sentiment.get(currency, 0)
            self.news_sentiment[currency] = max(min(current + change, 1.0), -1.0)
        
        self.logger.debug("Updated news sentiment data")
    
    async def analyze_and_broadcast(self):
        """Analyze data and broadcast significant changes"""
        now = datetime.utcnow()
        
        for currency in self.currencies_to_monitor:
            # Check for significant sentiment changes
            sentiment = self.news_sentiment.get(currency, 0)
            if abs(sentiment) > self.sentiment_threshold:
                direction = Direction.LONG if sentiment > 0 else Direction.SHORT
                confidence = Confidence.HIGH if abs(sentiment) > 0.7 else Confidence.MEDIUM
                
                update = FundamentalUpdate(
                    impact_currency=[currency],
                    event=f"News Sentiment Change",
                    actual=sentiment,
                    forecast=None,
                    previous=None,
                    impact_assessment=direction,
                    confidence=confidence,
                    timestamp=now
                )
                
                await self.send_message(
                    MessageType.FUNDAMENTAL_UPDATE,
                    {"update": update.__dict__}
                )
            
            # Check for interesting rate/inflation differentials
            # In real trading, rate differentials are very important
            for other_currency in self.currencies_to_monitor:
                if currency == other_currency:
                    continue
                
                pair = f"{currency}/{other_currency}"
                
                # Calculate interest rate differential
                rate_diff = self.central_bank_rates.get(currency, 0) - self.central_bank_rates.get(other_currency, 0)
                inflation_diff = self.inflation_data.get(currency, 0) - self.inflation_data.get(other_currency, 0)
                
                # Real interest rate differential (rate - inflation)
                real_rate_diff = (self.central_bank_rates.get(currency, 0) - self.inflation_data.get(currency, 0)) - \
                                (self.central_bank_rates.get(other_currency, 0) - self.inflation_data.get(other_currency, 0))
                
                # If there's a significant real rate advantage
                if abs(real_rate_diff) > 1.0:  # 1% differential threshold
                    direction = Direction.LONG if real_rate_diff > 0 else Direction.SHORT
                    
                    update = FundamentalUpdate(
                        impact_currency=[currency, other_currency],
                        event=f"Real Rate Differential",
                        actual=real_rate_diff,
                        forecast=None,
                        previous=None,
                        impact_assessment=direction,
                        confidence=Confidence.MEDIUM,
                        timestamp=now
                    )
                    
                    await self.send_message(
                        MessageType.FUNDAMENTAL_UPDATE,
                        {"update": update.__dict__}
                    )
    
    async def check_upcoming_events(self):
        """Check for upcoming high-impact economic events"""
        now = datetime.utcnow()
        upcoming_window = now + timedelta(hours=24)  # Look 24 hours ahead
        
        # Filter for high-impact events within the window
        upcoming_events = self.economic_calendar[
            (self.economic_calendar['datetime'] > now) &
            (self.economic_calendar['datetime'] <= upcoming_window) &
            (self.economic_calendar['importance'] == 'high')
        ]
        
        for _, event in upcoming_events.iterrows():
            # Calculate how soon the event is happening
            hours_until = (event['datetime'] - now).total_seconds() / 3600
            
            # If the event is within 1 hour and we haven
