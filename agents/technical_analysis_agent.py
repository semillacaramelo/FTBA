
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import pandas as pd

from system.agent import Agent
from system.core import Message, MessageType, Direction, Confidence, TechnicalSignal

class TechnicalAnalysisAgent(Agent):
    """
    Agent responsible for analyzing price charts and technical indicators
    to identify potential trade setups using pattern recognition and statistical analysis.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.analysis_interval = config.get("analysis_interval_seconds", 60)
        self.signal_threshold = config.get("signal_threshold", 0.7)
        self.market_data = {}  # Cache for market data
        self.indicators = {}   # Cache for calculated indicators
        
    async def setup(self):
        """Initialize the agent and subscribe to relevant message types"""
        await self.subscribe_to([
            MessageType.MARKET_DATA,
            MessageType.SYSTEM_STATUS
        ])
        self.logger.info("Technical Analysis Agent initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Technical Analysis Agent shutting down")
    
    async def process_cycle(self):
        """Main processing loop - analyze technical indicators and generate signals"""
        # Process technical analysis at the configured interval
        await self.analyze_all_symbols()
        await asyncio.sleep(self.analysis_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.MARKET_DATA:
            symbol = message.content.get("symbol")
            if symbol:
                self.update_market_data(symbol, message.content)
                
        elif message.type == MessageType.SYSTEM_STATUS:
            # Handle system status messages if needed
            pass
    
    def update_market_data(self, symbol: str, data: Dict):
        """Update our cached market data for a symbol"""
        if symbol not in self.market_data:
            self.market_data[symbol] = []
        
        # Add new data point
        self.market_data[symbol].append({
            "timestamp": datetime.fromisoformat(data.get("timestamp")),
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "close": data.get("close"),
            "volume": data.get("volume")
        })
        
        # Limit the size of the data cache
        max_points = 1000  # Store up to 1000 data points per symbol
        if len(self.market_data[symbol]) > max_points:
            self.market_data[symbol] = self.market_data[symbol][-max_points:]
    
    async def analyze_all_symbols(self):
        """Analyze all symbols in our market data cache"""
        for symbol in self.market_data:
            if len(self.market_data[symbol]) > 50:  # Need minimum data for analysis
                await self.analyze_symbol(symbol)
    
    async def analyze_symbol(self, symbol: str):
        """Analyze a specific symbol and generate signals if appropriate"""
        # Convert cached data to DataFrame for easier analysis
        df = pd.DataFrame(self.market_data[symbol])
        
        # Skip if not enough data
        if len(df) < 50:
            return
        
        signals = []
        
        # Analyze across multiple timeframes
        timeframes = ["5m", "15m", "1h", "4h", "1d"]
        for timeframe in timeframes:
            # Resample data to the specific timeframe
            # (In a real implementation, we would properly resample based on timeframe)
            # For this example, we'll just use the raw data
            
            # Calculate various indicators
            ema9 = self.calculate_ema(df, 9)
            ema20 = self.calculate_ema(df, 20)
            ema50 = self.calculate_ema(df, 50)
            rsi = self.calculate_rsi(df, 14)
            
            # Skip if we couldn't calculate indicators
            if not ema9 or not ema20 or not ema50 or not rsi:
                continue
            
            # Check for EMA crossovers
            if len(ema9) > 2 and len(ema20) > 2:
                # Check for bullish crossover (EMA9 crosses above EMA20)
                if ema9[-2] <= ema20[-2] and ema9[-1] > ema20[-1]:
                    signals.append(self.create_signal(symbol, "EMA Crossover", Direction.LONG, 
                                                     Confidence.MEDIUM, timeframe))
                
                # Check for bearish crossover (EMA9 crosses below EMA20)
                elif ema9[-2] >= ema20[-2] and ema9[-1] < ema20[-1]:
                    signals.append(self.create_signal(symbol, "EMA Crossover", Direction.SHORT, 
                                                     Confidence.MEDIUM, timeframe))
            
            # Check RSI for overbought/oversold conditions
            if rsi and len(rsi) > 0:
                current_rsi = rsi[-1]
                if current_rsi < 30:
                    signals.append(self.create_signal(symbol, "RSI", Direction.LONG, 
                                                    Confidence.MEDIUM, timeframe))
                elif current_rsi > 70:
                    signals.append(self.create_signal(symbol, "RSI", Direction.SHORT, 
                                                    Confidence.MEDIUM, timeframe))
        
        # 2. Consolidate signals from different timeframes
        if signals:
            consolidated = self.consolidate_signals(signals)
            
            # 3. Broadcast significant signals
            for signal in consolidated:
                await self.send_message(
                    MessageType.TECHNICAL_SIGNAL,
                    {
                        "signal": signal.__dict__,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                self.logger.info(f"Sent {signal.indicator} {signal.direction.value} signal for {symbol} on {signal.timeframe}")
    
    def calculate_ema(self, df, periods):
        """Calculate Exponential Moving Average"""
        if 'close' not in df.columns or len(df) < periods:
            return []
        ema = df['close'].ewm(span=periods, adjust=False).mean()
        return ema.tolist()
    
    def calculate_rsi(self, df, periods):
        """Calculate Relative Strength Index"""
        if 'close' not in df.columns or len(df) < periods + 1:
            return []
            
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss over the specified period
        avg_gain = gain.rolling(window=periods).mean()
        avg_loss = loss.rolling(window=periods).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.tolist()
    
    def create_signal(self, symbol, indicator, direction, confidence, timeframe):
        """Create a technical signal object"""
        return TechnicalSignal(
            symbol=symbol,
            indicator=indicator,
            direction=direction,
            confidence=confidence,
            timeframe=timeframe,
            parameters={},  # Would contain indicator-specific parameters
            value=0.0       # Would contain the actual indicator value
        )
    
    def consolidate_signals(self, signals):
        """Consolidate multiple signals based on significance and agreement"""
        # Simple implementation - just filter signals by confidence
        # In a real implementation, this would be more sophisticated
        return [s for s in signals if s.confidence in [Confidence.HIGH, Confidence.VERY_HIGH]]
