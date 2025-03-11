
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import numpy as np

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, Confidence, 
    TechnicalSignal, Indicator
)

class TechnicalAnalysisAgent(Agent):
    """
    Agent responsible for analyzing price charts and technical indicators to identify
    potential trade setups using pattern recognition and statistical analysis.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict = None):
        """
        Initialize the Technical Analysis Agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker for communication
            config: Agent configuration dictionary
        """
        super().__init__(agent_id, message_broker)
        self.config = config or {}
        self.agent_id = agent_id  # Store agent_id for compatibility with tests
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Set defaults for test compatibility
        if "analysis_interval_seconds" in self.config:
            self.analysis_interval = self.config["analysis_interval_seconds"]
        elif "analysis_interval" in self.config:
            self.analysis_interval = self.config["analysis_interval"]
        else:
            self.analysis_interval = 60
            
        if "signal_threshold" in self.config:
            self.signal_threshold = self.config["signal_threshold"]
        else:
            self.signal_threshold = 0.7
        
        # Store market data for analysis
        self.market_data = {}  # Symbol -> {timeframe -> price data}
        self.indicators = {}  # Symbol -> {indicator -> values}
        self.last_processed_time = datetime.utcnow()
    
    async def setup(self):
        """Initialize the agent"""
        self.logger.info("Setting up Technical Analysis Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.MARKET_DATA,
            MessageType.TRADE_RESULT  # To learn from past trades
        ])
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Technical Analysis Agent")
    
    async def process_cycle(self):
        """Main processing cycle"""
        # Check if it's time to update
        current_time = datetime.utcnow()
        if (current_time - self.last_processed_time).total_seconds() >= self.analysis_interval:
            self.logger.debug("Running technical analysis cycle")
            
            # Process market data and generate signals
            await self.analyze_market_data()
            
            # Update the last processed time
            self.last_processed_time = current_time
        
        # Sleep to prevent CPU spinning
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.MARKET_DATA:
            # Update market data
            await self.update_market_data(message)
        elif message.type == MessageType.TRADE_RESULT:
            # Learn from trade results to improve signal generation
            pass
    
    async def update_market_data(self, message: Message):
        """
        Update market data based on incoming messages
        
        Args:
            message: Message containing market data
        """
        data = message.content
        if not data:
            return
        
        symbol = data.get("symbol")
        timeframe = data.get("timeframe", "M1")
        
        if not symbol:
            return
            
        # Initialize market data structure if needed
        if symbol not in self.market_data:
            self.market_data[symbol] = {}
        
        if timeframe not in self.market_data[symbol]:
            self.market_data[symbol][timeframe] = {
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": [],
                "timestamp": []
            }
        
        # Add new data
        ohlc = data.get("ohlc")
        if ohlc:
            self.market_data[symbol][timeframe]["open"].append(ohlc["open"])
            self.market_data[symbol][timeframe]["high"].append(ohlc["high"])
            self.market_data[symbol][timeframe]["low"].append(ohlc["low"])
            self.market_data[symbol][timeframe]["close"].append(ohlc["close"])
            self.market_data[symbol][timeframe]["volume"].append(ohlc.get("volume", 0))
            self.market_data[symbol][timeframe]["timestamp"].append(data.get("timestamp", datetime.utcnow().isoformat()))
            
            # Limit data size (keep last 1000 candles)
            max_size = 1000
            if len(self.market_data[symbol][timeframe]["close"]) > max_size:
                for key in self.market_data[symbol][timeframe]:
                    self.market_data[symbol][timeframe][key] = self.market_data[symbol][timeframe][key][-max_size:]
            
            # Calculate indicators after data update
            self._calculate_indicators(symbol, timeframe)
    
    async def analyze_market_data(self):
        """Analyze market data and generate technical signals"""
        for symbol in self.market_data:
            # Analyze each timeframe
            for timeframe in self.market_data[symbol]:
                # Skip if not enough data
                if len(self.market_data[symbol][timeframe]["close"]) < 30:
                    continue
                
                # Generate signals
                signals = self._generate_signals(symbol, timeframe)
                
                # Send signals that meet threshold
                for signal in signals:
                    if signal.confidence >= self.signal_threshold:
                        await self.send_message(
                            MessageType.TECHNICAL_SIGNAL,
                            {
                                "signal": signal.__dict__,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        self.logger.info(f"Sent {signal.indicator} signal for {symbol} on {timeframe}")
    
    def _calculate_indicators(self, symbol: str, timeframe: str):
        """
        Calculate technical indicators for a symbol and timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe of data
        """
        # Initialize indicators for this symbol if needed
        if symbol not in self.indicators:
            self.indicators[symbol] = {}
        
        # Get price data
        close_prices = np.array(self.market_data[symbol][timeframe]["close"])
        high_prices = np.array(self.market_data[symbol][timeframe]["high"])
        low_prices = np.array(self.market_data[symbol][timeframe]["low"])
        
        if len(close_prices) < 30:
            return
        
        # Calculate Simple Moving Averages
        self.indicators[symbol]["SMA20"] = self._calculate_sma(close_prices, 20)
        self.indicators[symbol]["SMA50"] = self._calculate_sma(close_prices, 50)
        
        # Calculate Relative Strength Index
        self.indicators[symbol]["RSI"] = self._calculate_rsi(close_prices)
        
        # Calculate Average True Range (for volatility)
        self.indicators[symbol]["ATR"] = self._calculate_atr(high_prices, low_prices, close_prices)
        
        # Calculate Moving Average Convergence Divergence
        self.indicators[symbol]["MACD"] = self._calculate_macd(close_prices)
        
        # Calculate Bollinger Bands
        self.indicators[symbol]["BBANDS"] = self._calculate_bollinger_bands(close_prices)
    
    def _generate_signals(self, symbol: str, timeframe: str) -> List[TechnicalSignal]:
        """
        Generate technical signals based on indicators
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe of data
            
        Returns:
            List of technical signals
        """
        signals = []
        
        # Check if indicators exist for this symbol
        if symbol not in self.indicators:
            return signals
        
        # Get price data
        close_prices = self.market_data[symbol][timeframe]["close"]
        if len(close_prices) < 2:
            return signals
        
        current_close = close_prices[-1]
        previous_close = close_prices[-2]
        
        # Check Moving Average crossovers
        if "SMA20" in self.indicators[symbol] and "SMA50" in self.indicators[symbol]:
            sma20 = self.indicators[symbol]["SMA20"]
            sma50 = self.indicators[symbol]["SMA50"]
            
            if len(sma20) > 1 and len(sma50) > 1:
                # MA Crossover (SMA20 crosses above SMA50)
                if sma20[-2] < sma50[-2] and sma20[-1] > sma50[-1]:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.MOVING_AVERAGE_CROSSOVER,
                        direction=Direction.LONG,
                        confidence=0.75,
                        value=sma20[-1],
                        description=f"SMA20 crossed above SMA50 at {sma20[-1]:.5f}"
                    ))
                
                # MA Crossover (SMA20 crosses below SMA50)
                elif sma20[-2] > sma50[-2] and sma20[-1] < sma50[-1]:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.MOVING_AVERAGE_CROSSOVER,
                        direction=Direction.SHORT,
                        confidence=0.75,
                        value=sma20[-1],
                        description=f"SMA20 crossed below SMA50 at {sma20[-1]:.5f}"
                    ))
        
        # Check RSI overbought/oversold conditions
        if "RSI" in self.indicators[symbol]:
            rsi = self.indicators[symbol]["RSI"]
            if len(rsi) > 0:
                current_rsi = rsi[-1]
                
                # RSI oversold (potential buy)
                if current_rsi < 30:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.RSI,
                        direction=Direction.LONG,
                        confidence=0.8 if current_rsi < 20 else 0.6,
                        value=current_rsi,
                        description=f"RSI oversold at {current_rsi:.2f}"
                    ))
                
                # RSI overbought (potential sell)
                elif current_rsi > 70:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.RSI,
                        direction=Direction.SHORT,
                        confidence=0.8 if current_rsi > 80 else 0.6,
                        value=current_rsi,
                        description=f"RSI overbought at {current_rsi:.2f}"
                    ))
        
        # Check MACD signals
        if "MACD" in self.indicators[symbol]:
            macd_line, signal_line, histogram = self.indicators[symbol]["MACD"]
            
            if len(macd_line) > 1 and len(signal_line) > 1:
                # MACD crosses above signal line
                if macd_line[-2] < signal_line[-2] and macd_line[-1] > signal_line[-1]:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.MACD,
                        direction=Direction.LONG,
                        confidence=0.7,
                        value=macd_line[-1],
                        description=f"MACD crossed above signal line at {macd_line[-1]:.5f}"
                    ))
                
                # MACD crosses below signal line
                elif macd_line[-2] > signal_line[-2] and macd_line[-1] < signal_line[-1]:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.MACD,
                        direction=Direction.SHORT,
                        confidence=0.7,
                        value=macd_line[-1],
                        description=f"MACD crossed below signal line at {macd_line[-1]:.5f}"
                    ))
        
        # Check Bollinger Bands for price breaking out
        if "BBANDS" in self.indicators[symbol]:
            upper_band, middle_band, lower_band = self.indicators[symbol]["BBANDS"]
            
            if len(upper_band) > 0 and len(lower_band) > 0:
                # Price breaks above upper band
                if current_close > upper_band[-1] and previous_close <= upper_band[-1]:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.BOLLINGER_BANDS,
                        direction=Direction.SHORT,  # Contrarian approach or continuation depends on strategy
                        confidence=0.6,
                        value=upper_band[-1],
                        description=f"Price broke above upper Bollinger Band at {upper_band[-1]:.5f}"
                    ))
                
                # Price breaks below lower band
                elif current_close < lower_band[-1] and previous_close >= lower_band[-1]:
                    signals.append(TechnicalSignal(
                        symbol=symbol,
                        timeframe=timeframe,
                        indicator=Indicator.BOLLINGER_BANDS,
                        direction=Direction.LONG,  # Contrarian approach
                        confidence=0.6,
                        value=lower_band[-1],
                        description=f"Price broke below lower Bollinger Band at {lower_band[-1]:.5f}"
                    ))
        
        return signals
    
    def _calculate_sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        if len(data) < period:
            return np.array([])
        
        return np.convolve(data, np.ones(period)/period, mode='valid')
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index"""
        if len(data) <= period:
            return np.array([])
            
        # Calculate price changes
        deltas = np.diff(data)
        
        # Create arrays for gains and losses
        gains = np.copy(deltas)
        losses = np.copy(deltas)
        
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        # Calculate average gains and losses
        avg_gain = np.array([np.mean(gains[:period])])
        avg_loss = np.array([np.mean(losses[:period])])
        
        # Calculate subsequent values
        for i in range(period, len(deltas)):
            avg_gain = np.append(avg_gain, (avg_gain[-1] * (period - 1) + gains[i]) / period)
            avg_loss = np.append(avg_loss, (avg_loss[-1] * (period - 1) + losses[i]) / period)
        
        # Calculate RS and RSI
        rs = avg_gain / np.where(avg_loss == 0, 0.001, avg_loss)  # Avoid division by zero
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, data: np.ndarray, fast_period: int = 12, 
                       slow_period: int = 26, signal_period: int = 9) -> tuple:
        """Calculate Moving Average Convergence Divergence"""
        if len(data) < slow_period + signal_period:
            return np.array([]), np.array([]), np.array([])
        
        # Calculate exponential moving averages
        ema_fast = self._calculate_ema(data, fast_period)
        ema_slow = self._calculate_ema(data, slow_period)
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = self._calculate_ema(macd_line, signal_period)
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return np.array([])
            
        # Get initial SMA
        sma = np.mean(data[:period])
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Calculate EMA
        ema = np.array([sma])
        for i in range(period, len(data)):
            ema_value = (data[i] - ema[-1]) * multiplier + ema[-1]
            ema = np.append(ema, ema_value)
        
        return ema
    
    def _calculate_bollinger_bands(self, data: np.ndarray, period: int = 20, 
                                  num_std_dev: float = 2.0) -> tuple:
        """Calculate Bollinger Bands"""
        if len(data) < period:
            return np.array([]), np.array([]), np.array([])
        
        # Calculate middle band (SMA)
        middle_band = self._calculate_sma(data, period)
        
        # Calculate standard deviation
        rolling_std = np.array([np.std(data[i:i+period]) for i in range(len(data)-period+1)])
        
        # Calculate upper and lower bands
        upper_band = middle_band + (rolling_std * num_std_dev)
        lower_band = middle_band - (rolling_std * num_std_dev)
        
        return upper_band, middle_band, lower_band
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray, 
                      close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Average True Range"""
        if len(high) < period + 1 or len(low) < period + 1 or len(close) < period + 1:
            return np.array([])
        
        # Calculate true range
        tr = np.zeros(len(high))
        for i in range(1, len(high)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        # Calculate initial ATR as simple average
        atr = np.array([np.mean(tr[1:period+1])])
        
        # Calculate subsequent ATR values
        for i in range(period+1, len(high)):
            atr_value = (atr[-1] * (period - 1) + tr[i]) / period
            atr = np.append(atr, atr_value)
        
        return atr
