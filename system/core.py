from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
import uuid

class MessageType(Enum):
    TECHNICAL_SIGNAL = "technical_signal"
    FUNDAMENTAL_UPDATE = "fundamental_update"
    RISK_ASSESSMENT = "risk_assessment"
    STRATEGY_RECOMMENDATION = "strategy_recommendation"
    TRADE_PROPOSAL = "trade_proposal"
    TRADE_EXECUTION = "trade_execution"
    TRADE_RESULT = "trade_result"
    SYSTEM_STATUS = "system_status"
    AGENT_STATUS = "agent_status"

class Direction(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"

class Confidence(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

class TradeStatus(Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    PARTIALLY_EXECUTED = "partially_executed"
    CANCELED = "canceled"
    EXPIRED = "expired"

@dataclass
class Message:
    """Base message class for agent communication"""
    id: str
    type: MessageType
    sender: str
    timestamp: datetime
    content: Dict
    recipients: List[str] = None
    correlation_id: Optional[str] = None
    
    @classmethod
    def create(cls, msg_type: MessageType, sender: str, content: Dict, recipients=None):
        """Factory method to create a new message"""
        return cls(
            id=str(uuid.uuid4()),
            type=msg_type,
            sender=sender,
            timestamp=datetime.utcnow(),
            content=content,
            recipients=recipients
        )

@dataclass
class MarketData:
    """Container for market data"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    volume: float
    additional_data: Dict = None

@dataclass
class TechnicalSignal:
    """Technical analysis signal"""
    symbol: str
    indicator: str
    direction: Direction
    confidence: Confidence
    timeframe: str
    parameters: Dict
    value: float

@dataclass
class FundamentalUpdate:
    """Fundamental analysis update"""
    impact_currency: List[str]
    event: str
    actual: Optional[float]
    forecast: Optional[float]
    previous: Optional[float]
    impact_assessment: Direction
    confidence: Confidence
    timestamp: datetime

@dataclass
class RiskAssessment:
    """Risk management assessment"""
    symbol: str
    max_position_size: float
    recommended_leverage: float
    stop_loss_pips: float
    take_profit_pips: float
    max_daily_loss: float
    current_exposure: Dict
    market_volatility: float

@dataclass
class TradeProposal:
    """Trade proposal from the strategy agent"""
    id: str
    symbol: str
    direction: Direction
    size: float
    entry_price: Optional[float]
    stop_loss: float
    take_profit: float
    time_limit_seconds: int
    strategy_name: str
    technical_confidence: Confidence
    fundamental_alignment: Confidence
    risk_score: float
    status: TradeStatus = TradeStatus.PROPOSED

@dataclass
class TradeExecution:
    """Trade execution details"""
    proposal_id: str
    execution_id: str
    symbol: str
    direction: Direction
    executed_size: float
    executed_price: float
    execution_time: datetime
    status: TradeStatus
    metadata: Dict = None
