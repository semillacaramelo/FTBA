import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime

from system.agent import Agent
from system.core import (
    Message, MessageType, Direction, Confidence, 
    TechnicalSignal, MarketData
)

class TechnicalAnalysisAgent(Agent):
    def __init__(self, agent_id: str, message_broker, config):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.market_data_cache = {}  # Symbol -> DataFrame with OHLCV data
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.signal_threshold = config.get("signal_threshold", 0.7)
        self.analysis_interval = config.get("analysis_interval_seconds", 60)
        self.watchlist = config.get("watchlist", ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"])
        self.last_analysis_time = {}  # Symbol -> last analysis time
    
    async def setup(self):
        """Set up the agent when starting"""
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.TRADE_RESULT
        ])
        for symbol in self.watchlist:
            self.market_data_cache[symbol] = {tf: pd.DataFrame() for tf in self.timeframes}
            self.last_analysis_time[symbol] = datetime.min
        self.logger.info(f"Technical Analysis Agent setup complete. Monitoring {len(self.watchlist)} symbols")
    
    async def cleanup(self):
        """Clean up when agent is stopping"""
        self.market_data_cache = {}
        self.logger.info("Technical Analysis Agent cleaned up")
    
    async def process_cycle(self):
        """Process a single cycle of the agent's main loop"""
        now = datetime.utcnow()
        for symbol in self.watchlist:
            time_since_last = (now - self.last_analysis_time.get(symbol, datetime.min)).total_seconds()
            if time_since_last >= self.analysis_interval:
                await self.analyze_symbol(symbol)
                self.last_analysis_time[symbol] = now
        
        # Sleep to maintain the desired analysis frequency
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.SYSTEM_STATUS:
            # Handle system status updates
            pass
        elif message.type == MessageType.TRADE_RESULT:
            # Learn from trade results to improve future analysis
            if message.content.get("successful"):
                await self.reinforce_successful_strategy(message.content)
    
    async def update_market_data(self, market_data: MarketData):
        """Update market data cache"""
        symbol = market_data.symbol
        timestamp = market_data.timestamp
        
        # Calculate mid price
        mid_price = (market_data.bid + market_data.ask) / 2
        
        # Update caches for each timeframe
        for timeframe in self.timeframes:
            # Logic to convert ticks to OHLCV would go here
            # This is a simplified version
            pass
    
    async def analyze_symbol(self, symbol: str):
        """Analyze a symbol and generate signals"""
        signals = []
        
        # 1. Run technical indicators on different timeframes
        for timeframe in self.timeframes:
            if len(self.market_data_cache[symbol].get(timeframe, pd.DataFrame())) > 50:  # Need enough data
                df = self.market_data_cache[symbol][timeframe]
                
                # Moving Average Crossover
                ema_fast = self.calculate_ema(df, 9)
                ema_slow = self.calculate_ema(df, 21)
                
                if len(ema_fast) > 1 and len(ema_slow) > 1:
                    current_fast = ema_fast[-1]
                    previous_fast = ema_fast[-2]
                    current_slow = ema_slow[-1]
                    previous_slow = ema_slow[-2]
                    
                    # Bullish crossover
                    if previous_fast <= previous_slow and current_fast > current_slow:
                        signals.append(self.create_signal(symbol, "MA_CROSSOVER", Direction.LONG, 
                                                         Confidence.MEDIUM, timeframe))
                    
                    # Bearish crossover
                    elif previous_fast >= previous_slow and current_fast < current_slow:
                        signals.append(self.create_signal(symbol, "MA_CROSSOVER", Direction.SHORT, 
                                                         Confidence.MEDIUM, timeframe))
                
                # RSI analysis
                rsi = self.calculate_rsi(df, 14)
                if len(rsi) > 0:
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
        
        # EMA of gains and losses
        avg_gain = gain.ewm(com=periods-1, adjust=False).mean()
        avg_loss = loss.ewm(com=periods-1, adjust=False).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).tolist()  # Fill NAs with neutral value
    
    def create_signal(self, symbol, indicator, direction, confidence, timeframe):
        """Create a technical signal"""
        return TechnicalSignal(
            symbol=symbol,
            indicator=indicator,
            direction=direction,
            confidence=confidence,
            timeframe=timeframe,
            parameters={},  # Would include indicator parameters
            value=0.0  # Would include the actual indicator value
        )
    
    def consolidate_signals(self, signals: List[TechnicalSignal]) -> List[TechnicalSignal]:
        """Consolidate multiple signals to eliminate noise"""
        # Group signals by symbol and indicator
        grouped_signals = {}
        for signal in signals:
            key = (signal.symbol, signal.indicator)
            if key not in grouped_signals:
                grouped_signals[key] = []
            grouped_signals[key].append(signal)
        
        result = []
        
        # Process each group
        for (symbol, indicator), signal_group in grouped_signals.items():
            # For signals of the same indicator, prioritize longer timeframes
            # and higher confidence levels
            timeframe_weights = {
                "1m": 1, "5m": 2, "15m": 3, 
                "1h": 4, "4h": 5, "1d": 6
            }
            
            # Sort by timeframe importance and confidence
            sorted_signals = sorted(
                signal_group, 
                key=lambda s: (timeframe_weights.get(s.timeframe, 0), s.confidence.value),
                reverse=True
            )
            
            # Take the most significant signal
            if sorted_signals:
                result.append(sorted_signals[0])
        
        return result
    
    async def reinforce_successful_strategy(self, trade_result):
        """Learn from successful trades to improve signal generation"""
        # Update signal thresholds or adjust indicator parameters
        symbol = trade_result.get("symbol")
        strategy = trade_result.get("strategy")
        
        # This would be expanded with actual learning logic
        self.logger.info(f"Reinforcing strategy: {strategy} for {symbol}")
