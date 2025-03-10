
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class Direction(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"  # No position/neutral


class Confidence(Enum):
    """Confidence level for signals and analysis"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class TechnicalSignal:
    """Technical analysis signal"""
    
    def __init__(
        self,
        symbol: str,
        direction: Direction,
        confidence: Confidence,
        signal_type: str,
        timeframe: str,
        indicators: Dict[str, Any],
        price_level: float,
        expiration_time: Optional[datetime] = None
    ):
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.signal_type = signal_type  # e.g., "trend_following", "reversal", "breakout"
        self.timeframe = timeframe      # e.g., "1m", "5m", "1h", "4h", "1d"
        self.indicators = indicators    # Indicator values that triggered the signal
        self.price_level = price_level  # Current price when signal was generated
        self.timestamp = datetime.utcnow()
        self.expiration_time = expiration_time  # When the signal should be considered stale


class FundamentalUpdate:
    """Fundamental analysis update/event"""
    
    def __init__(
        self,
        impact_currency: List[str],  # List of currencies affected
        event: str,                  # Name of the event
        expected: Any = None,        # Expected value (if applicable)
        actual: Any = None,          # Actual value
        impact: str = "medium",      # Low/medium/high impact
        direction: Optional[Direction] = None,  # Expected price direction
        confidence: Optional[Confidence] = None  # Confidence in the analysis
    ):
        self.impact_currency = impact_currency
        self.event = event
        self.expected = expected
        self.actual = actual
        self.impact = impact
        self.direction = direction
        self.confidence = confidence
        self.timestamp = datetime.utcnow()


class TradeProposal:
    """Proposed trade from strategy to risk management"""
    
    def __init__(
        self,
        symbol: str,
        direction: Direction,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: Confidence,
        strategy_name: str,
        signals: List[Dict],
        position_size: Optional[float] = None,  # Can be specified or determined by risk management
        expiration_time: Optional[datetime] = None
    ):
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.confidence = confidence
        self.strategy_name = strategy_name
        self.signals = signals  # List of signals that contributed to this proposal
        self.position_size = position_size
        self.timestamp = datetime.utcnow()
        self.expiration_time = expiration_time
        self.id = f"trade_{self.timestamp.strftime('%Y%m%d%H%M%S')}_{symbol}"


class TradeExecution:
    """Trade execution details"""
    
    def __init__(
        self,
        trade_id: str,
        symbol: str,
        direction: Direction,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        execution_time: datetime,
        execution_price: Optional[float] = None,
        status: str = "pending",  # pending, executed, rejected, canceled
        metadata: Optional[Dict] = None
    ):
        self.trade_id = trade_id
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.position_size = position_size
        self.execution_time = execution_time
        self.execution_price = execution_price or entry_price
        self.status = status
        self.metadata = metadata or {}


class TradeResult:
    """Completed trade result"""
    
    def __init__(
        self,
        trade_id: str,
        symbol: str,
        direction: Direction,
        entry_price: float,
        exit_price: float,
        position_size: float,
        entry_time: datetime,
        exit_time: datetime,
        profit_loss: float,
        profit_loss_pips: float,
        exit_reason: str,  # "take_profit", "stop_loss", "manual", etc.
        strategy_name: str,
        metadata: Optional[Dict] = None
    ):
        self.trade_id = trade_id
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.position_size = position_size
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.profit_loss = profit_loss
        self.profit_loss_pips = profit_loss_pips
        self.exit_reason = exit_reason
        self.strategy_name = strategy_name
        self.metadata = metadata or {}
        self.duration = exit_time - entry_time
