
"""
Core data structures and enumerations for the multi-agent forex trading system.
These serve as the foundation for communication and data representation throughout the system.
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union, Callable, Set, Awaitable


class Direction(Enum):
    """Trade direction enumeration"""
    LONG = "LONG"     # Buy / bullish position
    SHORT = "SHORT"   # Sell / bearish position
    NEUTRAL = "NEUTRAL"  # No directional bias


class TradeStatus(Enum):
    """Trade status enumeration for tracking lifecycle"""
    PROPOSED = "PROPOSED"    # Initial proposal
    APPROVED = "APPROVED"    # Approved by risk manager
    REJECTED = "REJECTED"    # Rejected by risk manager
    PENDING = "PENDING"      # Pending execution
    EXECUTED = "EXECUTED"    # Successfully executed
    CANCELED = "CANCELED"    # Canceled before execution
    CLOSED = "CLOSED"        # Position closed
    EXPIRED = "EXPIRED"      # Expired without execution


class Confidence(Enum):
    """Confidence level enumeration"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Timeframe(Enum):
    """Trading timeframe enumeration"""
    M1 = "1m"     # 1 minute
    M5 = "5m"     # 5 minutes
    M15 = "15m"   # 15 minutes
    M30 = "30m"   # 30 minutes
    H1 = "1h"     # 1 hour
    H4 = "4h"     # 4 hours
    D1 = "1d"     # 1 day
    W1 = "1w"     # 1 week


class Indicator(Enum):
    """Technical indicator enumeration"""
    MOVING_AVERAGE_CROSSOVER = "MOVING_AVERAGE_CROSSOVER"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    ATR = "ATR"
    STOCHASTIC = "STOCHASTIC"


@dataclass
class TechnicalSignal:
    """Technical analysis signal data structure"""
    symbol: str
    timeframe: Union[str, Timeframe]
    indicator: str
    direction: Direction
    confidence: Confidence
    value: float
    threshold: float
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Convert fields to proper types after initialization"""
        if isinstance(self.timeframe, str):
            try:
                self.timeframe = Timeframe(self.timeframe)
            except ValueError:
                # Keep as string if not matching any Timeframe enum
                pass
        
        if isinstance(self.direction, str):
            self.direction = Direction(self.direction)
            
        if isinstance(self.confidence, str):
            self.confidence = Confidence(self.confidence)
            
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class FundamentalUpdate:
    """Fundamental analysis update data structure"""
    event: str
    impact_currency: List[str]
    impact_assessment: Direction
    confidence: Confidence
    forecast: Optional[float] = None
    previous: Optional[float] = None
    actual: Optional[float] = None
    timestamp: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Convert fields to proper types after initialization"""
        if isinstance(self.impact_assessment, str):
            self.impact_assessment = Direction(self.impact_assessment)
            
        if isinstance(self.confidence, str):
            self.confidence = Confidence(self.confidence)
            
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class TradeProposal:
    """Trade proposal data structure"""
    id: str
    symbol: str
    direction: Direction
    size: float
    strategy_name: str
    technical_confidence: Confidence
    fundamental_alignment: Confidence
    risk_score: float
    status: TradeStatus
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_limit_seconds: int = 3600
    expiry_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Convert fields to proper types after initialization"""
        if isinstance(self.direction, str):
            self.direction = Direction(self.direction)
            
        if isinstance(self.technical_confidence, str):
            self.technical_confidence = Confidence(self.technical_confidence)
            
        if isinstance(self.fundamental_alignment, str):
            self.fundamental_alignment = Confidence(self.fundamental_alignment)
            
        if isinstance(self.status, str):
            self.status = TradeStatus(self.status)
            
        if self.expiry_time is None and self.time_limit_seconds > 0:
            expiry_dt = datetime.utcnow().timestamp() + self.time_limit_seconds
            self.expiry_time = datetime.fromtimestamp(expiry_dt).isoformat()


@dataclass
class TradeExecution:
    """Trade execution data structure"""
    proposal_id: str
    execution_id: str
    symbol: str
    direction: Direction
    executed_size: float
    executed_price: float
    execution_time: datetime
    status: TradeStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Convert fields to proper types after initialization"""
        if isinstance(self.direction, str):
            self.direction = Direction(self.direction)
            
        if isinstance(self.status, str):
            self.status = TradeStatus(self.status)
            
        if isinstance(self.execution_time, str):
            self.execution_time = datetime.fromisoformat(self.execution_time)


@dataclass
class TradeResult:
    """Trade result data structure"""
    trade_id: str
    symbol: str
    direction: Direction
    entry_price: float
    exit_price: float
    position_size: float
    entry_time: datetime
    exit_time: datetime
    profit_loss: float
    profit_loss_pips: float
    exit_reason: str
    strategy_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Convert fields to proper types after initialization"""
        if isinstance(self.direction, str):
            self.direction = Direction(self.direction)
            
        if isinstance(self.entry_time, str):
            self.entry_time = datetime.fromisoformat(self.entry_time)
            
        if isinstance(self.exit_time, str):
            self.exit_time = datetime.fromisoformat(self.exit_time)


@dataclass
class RiskAssessment:
    """Risk assessment data structure"""
    symbol: str
    max_position_size: float
    recommended_leverage: float
    stop_loss_pips: float
    take_profit_pips: float
    max_daily_loss: float
    current_exposure: Dict[str, Any]
    market_volatility: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for message passing"""
        return {
            "symbol": self.symbol,
            "max_position_size": self.max_position_size,
            "recommended_leverage": self.recommended_leverage,
            "stop_loss_pips": self.stop_loss_pips,
            "take_profit_pips": self.take_profit_pips,
            "max_daily_loss": self.max_daily_loss,
            "current_exposure": self.current_exposure,
            "market_volatility": self.market_volatility
        }


@dataclass
class MarketData:
    """Market data structure for price and related information"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    timeframe: Optional[Timeframe] = None
    
    def __post_init__(self):
        """Convert fields to proper types after initialization"""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
            
        if isinstance(self.timeframe, str):
            try:
                self.timeframe = Timeframe(self.timeframe)
            except ValueError:
                # Keep as None if not matching any Timeframe enum
                self.timeframe = None


class MessageBroker:
    """
    Central message broker for system-wide event distribution.
    Implements a publish-subscribe pattern for decoupled agent communication.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("message_broker")
        self.subscribers = defaultdict(set)
        self.message_queue = asyncio.Queue()
        self._running = False
        self._processor_task = None
    
    async def start(self):
        """Start the message processor"""
        if self._running:
            return
            
        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        self.logger.info("Message broker started")
    
    async def stop(self):
        """Stop the message processor"""
        if not self._running:
            return
            
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
        self.logger.info("Message broker stopped")
    
    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Subscribe to a topic with a callback function"""
        self.subscribers[topic].add(callback)
        self.logger.debug(f"Subscribed to topic: {topic}")
    
    def unsubscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Unsubscribe from a topic"""
        if topic in self.subscribers and callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)
            self.logger.debug(f"Unsubscribed from topic: {topic}")
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """Publish a message to a topic"""
        await self.message_queue.put((topic, message))
        self.logger.debug(f"Published message to topic: {topic}")
    
    async def _process_messages(self):
        """Process messages from the queue and distribute to subscribers"""
        self.logger.debug("Message processor started")
        
        while self._running:
            try:
                topic, message = await self.message_queue.get()
                
                if topic in self.subscribers:
                    for callback in self.subscribers[topic]:
                        try:
                            await callback(message)
                        except Exception as e:
                            self.logger.error(f"Error in subscriber callback: {e}", exc_info=True)
                
                self.message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)
        
        self.logger.debug("Message processor stopped")
