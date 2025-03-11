
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import numpy as np
import json
import os
from collections import defaultdict

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, Confidence, 
    TradeProposal, TradeStatus,
    TechnicalSignal, FundamentalUpdate
)

class StrategyOptimizationAgent(Agent):
    """
    Agent responsible for leveraging machine learning to continuously refine
    trading strategies based on performance metrics and market conditions.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict = None):
        """
        Initialize the Strategy Optimization Agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker for communication
            config: Agent configuration dictionary
        """
        super().__init__(agent_id, message_broker)
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.update_interval = self.config.get("update_interval_seconds", 300)
        self.learning_rate = self.config.get("learning_rate", 0.1)
        
        # Strategy performance tracking
        self.strategies = {}  # Strategy name -> parameters
        self.strategy_performance = {}  # Strategy name -> performance metrics
        self.active_trades = {}  # Trade ID -> strategy used
        
        # Signal history
        self.technical_signals = defaultdict(list)  # Symbol -> list of signals
        self.fundamental_updates = defaultdict(list)  # Symbol -> list of updates
        
        # Store correlated signals for trade generation
        self.correlated_signals = defaultdict(list)  # Symbol -> list of correlated signals
        
        # Last processed time
        self.last_processed_time = datetime.utcnow()
        
        # Ensure data directory exists
        data_dir = os.path.join("data", "performance")
        os.makedirs(data_dir, exist_ok=True)
        
        # Load strategies if they exist
        self._load_strategies()
    
    async def setup(self):
        """Initialize the agent"""
        self.logger.info("Setting up Strategy Optimization Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.TECHNICAL_SIGNAL,
            MessageType.FUNDAMENTAL_UPDATE,
            MessageType.RISK_UPDATE,
            MessageType.TRADE_APPROVAL,
            MessageType.TRADE_RESULT
        ])
        
        # Initialize default strategies if none exist
        if not self.strategies:
            self._initialize_default_strategies()
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Strategy Optimization Agent")
        
        # Save strategies and performance data
        self._save_strategies()
    
    async def process_cycle(self):
        """Main processing cycle"""
        # Check if it's time to update
        current_time = datetime.utcnow()
        if (current_time - self.last_processed_time).total_seconds() >= self.update_interval:
            self.logger.debug("Running strategy optimization cycle")
            
            # Optimize strategies based on performance
            await self.optimize_strategies()
            
            # Clean up old signals
            await self.clean_old_signals()
            
            # Generate trade proposals based on correlated signals
            await self.generate_trade_proposals()
            
            # Update the last processed time
            self.last_processed_time = current_time
        
        # Sleep to prevent CPU spinning
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TECHNICAL_SIGNAL:
            # Store technical signal
            await self.process_technical_signal(message)
        
        elif message.type == MessageType.FUNDAMENTAL_UPDATE:
            # Store fundamental update
            await self.process_fundamental_update(message)
        
        elif message.type == MessageType.RISK_UPDATE:
            # Update strategy risk parameters
            await self.update_strategy_risk(message)
        
        elif message.type == MessageType.TRADE_APPROVAL:
            # Track approved trades
            await self.track_approved_trade(message)
        
        elif message.type == MessageType.TRADE_RESULT:
            # Update strategy performance based on trade results
            await self.update_strategy_performance(message)
    
    async def process_technical_signal(self, message: Message):
        """
        Process and store technical signals
        
        Args:
            message: Message containing technical signal
        """
        signal_data = message.content.get("signal", {})
        if not signal_data:
            return
        
        # Extract signal details
        symbol = signal_data.get("symbol", "")
        if not symbol:
            return
        
        # Add timestamp to signal
        signal_data["received_time"] = datetime.utcnow().isoformat()
        
        # Store signal
        self.technical_signals[symbol].append(signal_data)
        
        # Check for signal correlation with fundamental data
        await self.correlate_signals(symbol)
    
    async def process_fundamental_update(self, message: Message):
        """
        Process and store fundamental updates
        
        Args:
            message: Message containing fundamental update
        """
        update_data = message.content.get("update", {})
        if not update_data:
            return
        
        # Extract update details
        impact_currency = update_data.get("impact_currency", [])
        
        # Skip if no currencies are affected
        if not impact_currency:
            return
        
        # Add timestamp to update
        update_data["received_time"] = datetime.utcnow().isoformat()
        
        # Store update for each affected currency
        for currency in impact_currency:
            # Find symbols that contain this currency
            for symbol in set(list(self.technical_signals.keys())):
                base_currency = symbol.split('/')[0]
                quote_currency = symbol.split('/')[1]
                
                if currency == base_currency or currency == quote_currency:
                    self.fundamental_updates[symbol].append(update_data)
                    
                    # Check for signal correlation with technical data
                    await self.correlate_signals(symbol)
    
    async def correlate_signals(self, symbol: str):
        """
        Correlate technical and fundamental signals for a symbol
        
        Args:
            symbol: Trading symbol
        """
        # Get recent technical signals (last 60 minutes)
        recent_cutoff = datetime.utcnow() - timedelta(minutes=60)
        recent_technical = [
            signal for signal in self.technical_signals[symbol]
            if datetime.fromisoformat(signal.get("received_time", "")) > recent_cutoff
        ]
        
        # Get recent fundamental updates (last 24 hours)
        day_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_fundamental = [
            update for update in self.fundamental_updates[symbol]
            if datetime.fromisoformat(update.get("received_time", "")) > day_cutoff
        ]
        
        # If we have both technical and fundamental signals
        if recent_technical and recent_fundamental:
            for tech_signal in recent_technical:
                for fund_update in recent_fundamental:
                    # Check if directions align or oppose
                    tech_direction = tech_signal.get("direction", Direction.NEUTRAL)
                    fund_direction = fund_update.get("impact_assessment", Direction.NEUTRAL)
                    
                    # Skip neutral signals
                    if tech_direction == Direction.NEUTRAL or fund_direction == Direction.NEUTRAL:
                        continue
                    
                    # Calculate correlation score based on direction agreement and confidence
                    direction_agreement = (tech_direction == fund_direction)
                    tech_confidence = tech_signal.get("confidence", 0.5)
                    fund_confidence = {
                        Confidence.VERY_LOW: 0.1,
                        Confidence.LOW: 0.3,
                        Confidence.MEDIUM: 0.5,
                        Confidence.HIGH: 0.7,
                        Confidence.VERY_HIGH: 0.9
                    }.get(fund_update.get("confidence", Confidence.MEDIUM), 0.5)
                    
                    # Higher score for agreeing signals with high confidence
                    if direction_agreement:
                        correlation_score = tech_confidence * fund_confidence * 2.0
                    else:
                        # Lower score for opposing signals, weighted by confidence
                        correlation_score = -0.5 * tech_confidence * fund_confidence
                    
                    # Store correlated signal if score is significant
                    if abs(correlation_score) > 0.3:
                        correlated_signal = {
                            "symbol": symbol,
                            "technical_signal": tech_signal,
                            "fundamental_update": fund_update,
                            "correlation_score": correlation_score,
                            "direction": tech_direction if correlation_score > 0 else Direction.LONG if tech_direction == Direction.SHORT else Direction.SHORT,
                            "confidence": abs(correlation_score),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        self.correlated_signals[symbol].append(correlated_signal)
                        self.logger.info(f"Created correlated signal for {symbol} with score {correlation_score:.2f}")
    
    async def generate_trade_proposals(self):
        """Generate trade proposals based on correlated signals"""
        # Process each symbol's correlated signals
        for symbol, signals in self.correlated_signals.items():
            # Skip if no signals
            if not signals:
                continue
            
            # Get recent signals (last 30 minutes)
            recent_cutoff = datetime.utcnow() - timedelta(minutes=30)
            recent_signals = [
                signal for signal in signals
                if datetime.fromisoformat(signal.get("timestamp", "")) > recent_cutoff
            ]
            
            # Skip if no recent signals
            if not recent_signals:
                continue
            
            # Get the strongest signal
            strongest_signal = max(recent_signals, key=lambda x: x.get("confidence", 0))
            
            # Check if confidence meets threshold
            if strongest_signal.get("confidence", 0) < 0.6:
                continue
            
            # Select a strategy for this trade
            strategy_name = self._select_strategy_for_signal(strongest_signal)
            if not strategy_name:
                continue
            
            # Get strategy parameters
            strategy = self.strategies.get(strategy_name, {})
            
            # Create trade proposal
            direction = strongest_signal.get("direction", Direction.NEUTRAL)
            if direction == Direction.NEUTRAL:
                continue
                
            trade_id = f"trade_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{symbol}"
            
            # Default size and entry price (would be refined in a real system)
            size = 0.1  # Default size
            entry_price = None  # Market order
            
            # Create the proposal
            proposal = TradeProposal(
                id=trade_id,
                symbol=symbol,
                direction=direction,
                size=size,
                entry_price=entry_price,
                stop_loss=None,  # Let risk agent decide
                take_profit=None,  # Let risk agent decide
                status=TradeStatus.PROPOSED,
                strategy=strategy_name,
                signal_confidence=strongest_signal.get("confidence", 0.6),
                creation_time=datetime.utcnow().isoformat()
            )
            
            # Track which strategy is used for this proposal
            self.active_trades[trade_id] = {
                "strategy": strategy_name,
                "proposal": proposal.__dict__,
                "correlated_signal": strongest_signal
            }
            
            # Send the proposal
            await self.send_message(
                MessageType.TRADE_PROPOSAL,
                {
                    "proposal": proposal.__dict__,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(f"Sent trade proposal {trade_id} for {symbol} using {strategy_name} strategy")
            
            # Remove this signal so we don't propose again
            self.correlated_signals[symbol].remove(strongest_signal)
    
    async def track_approved_trade(self, message: Message):
        """
        Track approved trades
        
        Args:
            message: Message containing trade approval
        """
        proposal_id = message.content.get("proposal_id")
        if not proposal_id or proposal_id not in self.active_trades:
            return
        
        # Update trade status
        self.active_trades[proposal_id]["status"] = "APPROVED"
        self.active_trades[proposal_id]["approval_time"] = datetime.utcnow().isoformat()
        
        # Update adjusted proposal
        adjusted_proposal = message.content.get("adjusted_proposal")
        if adjusted_proposal:
            self.active_trades[proposal_id]["adjusted_proposal"] = adjusted_proposal
        
        self.logger.info(f"Tracked approved trade {proposal_id}")
    
    async def update_strategy_performance(self, message: Message):
        """
        Update strategy performance based on trade results
        
        Args:
            message: Message containing trade result
        """
        result_data = message.content.get("result", {})
        if not result_data:
            return
        
        # Extract result details
        trade_id = result_data.get("trade_id", "unknown")
        profit_loss = result_data.get("profit_loss", 0)
        
        # Skip if trade not tracked
        if trade_id not in self.active_trades:
            return
        
        # Get strategy used for this trade
        trade_info = self.active_trades[trade_id]
        strategy_name = trade_info.get("strategy")
        
        if not strategy_name or strategy_name not in self.strategies:
            return
        
        # Initialize strategy performance if needed
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = {
                "trades_count": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit_loss": 0,
                "avg_profit_per_trade": 0,
                "avg_loss_per_trade": 0,
                "max_profit": 0,
                "max_loss": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "recent_trades": []
            }
        
        # Update performance metrics
        perf = self.strategy_performance[strategy_name]
        perf["trades_count"] += 1
        perf["total_profit_loss"] += profit_loss
        
        if profit_loss > 0:
            perf["winning_trades"] += 1
            perf["max_profit"] = max(perf["max_profit"], profit_loss)
        else:
            perf["losing_trades"] += 1
            perf["max_loss"] = min(perf["max_loss"], profit_loss)
        
        # Calculate derived metrics
        if perf["trades_count"] > 0:
            perf["win_rate"] = perf["winning_trades"] / perf["trades_count"]
        
        if perf["winning_trades"] > 0:
            perf["avg_profit_per_trade"] = perf["total_profit_loss"] / perf["winning_trades"]
        
        if perf["losing_trades"] > 0:
            perf["avg_loss_per_trade"] = perf["total_profit_loss"] / perf["losing_trades"]
        
        # Store recent trade
        perf["recent_trades"].append({
            "trade_id": trade_id,
            "profit_loss": profit_loss,
            "timestamp": datetime.utcnow().isoformat(),
            "proposal": trade_info.get("proposal", {}),
            "signal": trade_info.get("correlated_signal", {})
        })
        
        # Keep only last 100 trades
        if len(perf["recent_trades"]) > 100:
            perf["recent_trades"] = perf["recent_trades"][-100:]
        
        self.logger.info(f"Updated performance for {strategy_name}: P&L {profit_loss}, Win rate {perf['win_rate']:.2f}")
        
        # Remove from active trades
        del self.active_trades[trade_id]
    
    async def update_strategy_risk(self, message: Message):
        """
        Update strategy risk parameters based on risk updates
        
        Args:
            message: Message containing risk update
        """
        symbol = message.content.get("symbol")
        assessment = message.content.get("assessment", {})
        
        if not symbol or not assessment:
            return
        
        # Update strategies that trade this symbol
        for strategy_name, strategy in self.strategies.items():
            # Skip if strategy doesn't trade this symbol
            if "symbols" in strategy and symbol not in strategy["symbols"]:
                continue
            
            # Update risk parameters
            if "risk_parameters" not in strategy:
                strategy["risk_parameters"] = {}
            
            strategy["risk_parameters"][symbol] = {
                "max_position_size": assessment.get("max_position_size"),
                "stop_loss_pips": assessment.get("stop_loss_pips"),
                "take_profit_pips": assessment.get("take_profit_pips"),
                "market_volatility": assessment.get("market_volatility"),
                "updated_at": datetime.utcnow().isoformat()
            }
    
    async def optimize_strategies(self):
        """Optimize strategies based on performance metrics"""
        for strategy_name, performance in self.strategy_performance.items():
            # Skip if not enough trades
            if performance.get("trades_count", 0) < 10:
                continue
            
            # Get strategy
            strategy = self.strategies.get(strategy_name)
            if not strategy:
                continue
            
            # Check if strategy is performing poorly
            win_rate = performance.get("win_rate", 0)
            if win_rate < 0.4:
                # Adjust parameters to improve performance
                await self._adjust_strategy_parameters(strategy_name, performance)
                self.logger.info(f"Adjusted parameters for {strategy_name} due to low win rate {win_rate:.2f}")
            
            # Check if strategy needs minor tuning
            elif 0.4 <= win_rate < 0.55:
                # Fine-tune parameters
                await self._fine_tune_strategy(strategy_name, performance)
                self.logger.info(f"Fine-tuned {strategy_name} with win rate {win_rate:.2f}")
            
            # Save performance data
            self._save_strategy_performance(strategy_name, performance)
    
    async def clean_old_signals(self):
        """Clean up old signals to prevent memory bloat"""
        # Define cutoff times
        tech_cutoff = datetime.utcnow() - timedelta(hours=4)
        fund_cutoff = datetime.utcnow() - timedelta(days=2)
        corr_cutoff = datetime.utcnow() - timedelta(hours=6)
        
        # Clean technical signals
        for symbol in self.technical_signals:
            self.technical_signals[symbol] = [
                signal for signal in self.technical_signals[symbol]
                if datetime.fromisoformat(signal.get("received_time", "2000-01-01")) > tech_cutoff
            ]
        
        # Clean fundamental updates
        for symbol in self.fundamental_updates:
            self.fundamental_updates[symbol] = [
                update for update in self.fundamental_updates[symbol]
                if datetime.fromisoformat(update.get("received_time", "2000-01-01")) > fund_cutoff
            ]
        
        # Clean correlated signals
        for symbol in self.correlated_signals:
            self.correlated_signals[symbol] = [
                signal for signal in self.correlated_signals[symbol]
                if datetime.fromisoformat(signal.get("timestamp", "2000-01-01")) > corr_cutoff
            ]
    
    async def _adjust_strategy_parameters(self, strategy_name: str, performance: Dict):
        """
        Make significant adjustments to poorly performing strategies
        
        Args:
            strategy_name: Strategy to adjust
            performance: Performance metrics
        """
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return
        
        # Get parameters
        params = strategy.get("parameters", {})
        
        # Adjust signal threshold (make more conservative)
        if "signal_threshold" in params:
            params["signal_threshold"] = min(0.9, params["signal_threshold"] + self.learning_rate)
        
        # Adjust hold time (try different durations)
        if "hold_time_minutes" in params:
            # Increase or decrease based on recent performance trend
            recent_trades = performance.get("recent_trades", [])
            if recent_trades:
                recent_pl = sum(trade.get("profit_loss", 0) for trade in recent_trades[-5:])
                if recent_pl < 0:
                    # Change direction drastically if recent trades are losing
                    if params["hold_time_minutes"] < 60:
                        params["hold_time_minutes"] *= 2
                    else:
                        params["hold_time_minutes"] = max(5, params["hold_time_minutes"] // 2)
        
        # Update strategy with adjusted parameters
        strategy["parameters"] = params
        strategy["last_optimized"] = datetime.utcnow().isoformat()
    
    async def _fine_tune_strategy(self, strategy_name: str, performance: Dict):
        """
        Fine-tune a strategy with minor adjustments
        
        Args:
            strategy_name: Strategy to fine-tune
            performance: Performance metrics
        """
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return
        
        # Get parameters
        params = strategy.get("parameters", {})
        
        # Small adjustments to signal threshold
        if "signal_threshold" in params:
            # Adjust based on win rate
            win_rate = performance.get("win_rate", 0.5)
            if win_rate < 0.5:
                # Slightly more conservative
                params["signal_threshold"] = min(0.9, params["signal_threshold"] + (self.learning_rate * 0.5))
            else:
                # Slightly more aggressive if winning
                params["signal_threshold"] = max(0.5, params["signal_threshold"] - (self.learning_rate * 0.2))
        
        # Adjust profit taking based on market conditions
        if "take_profit_factor" in params:
            avg_profit = performance.get("avg_profit_per_trade", 0)
            avg_loss = performance.get("avg_loss_per_trade", 0)
            
            if avg_profit < -avg_loss:
                # Not taking enough profit
                params["take_profit_factor"] *= (1 + self.learning_rate * 0.5)
            else:
                # Taking too much profit (getting stopped out)
                params["take_profit_factor"] *= (1 - self.learning_rate * 0.2)
        
        # Update strategy with fine-tuned parameters
        strategy["parameters"] = params
        strategy["last_optimized"] = datetime.utcnow().isoformat()
    
    def _select_strategy_for_signal(self, signal: Dict) -> Optional[str]:
        """
        Select the best strategy for a signal
        
        Args:
            signal: Correlated signal
            
        Returns:
            str: Selected strategy name or None
        """
        if not self.strategies:
            return None
        
        symbol = signal.get("symbol")
        direction = signal.get("direction")
        confidence = signal.get("confidence", 0)
        
        # Filter strategies that are applicable
        applicable_strategies = []
        for name, strategy in self.strategies.items():
            # Skip if strategy doesn't trade this symbol
            if "symbols" in strategy and symbol not in strategy["symbols"]:
                continue
            
            # Check if strategy handles this direction
            direction_match = True
            if "allowed_directions" in strategy:
                direction_match = direction in strategy["allowed_directions"]
            
            # Check if signal confidence meets threshold
            confidence_match = True
            if "parameters" in strategy and "signal_threshold" in strategy["parameters"]:
                confidence_match = confidence >= strategy["parameters"]["signal_threshold"]
            
            if direction_match and confidence_match:
                applicable_strategies.append(name)
        
        if not applicable_strategies:
            return None
        
        # Check performance of applicable strategies
        if self.strategy_performance:
            # Sort by win rate
            strategy_win_rates = []
            for name in applicable_strategies:
                if name in self.strategy_performance:
                    win_rate = self.strategy_performance[name].get("win_rate", 0)
                    strategy_win_rates.append((name, win_rate))
            
            if strategy_win_rates:
                # Select the best performing strategy
                return max(strategy_win_rates, key=lambda x: x[1])[0]
        
        # If no performance data, choose randomly
        return np.random.choice(applicable_strategies)
    
    def _initialize_default_strategies(self):
        """Initialize default trading strategies"""
        self.strategies = {
            "trend_following": {
                "description": "Follows established trends using moving average crossovers",
                "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
                "allowed_directions": [Direction.LONG, Direction.SHORT],
                "parameters": {
                    "signal_threshold": 0.7,
                    "hold_time_minutes": 240,
                    "take_profit_factor": 1.5,
                    "stop_loss_factor": 1.0
                },
                "indicators": ["MOVING_AVERAGE_CROSSOVER", "MACD"],
                "created_at": datetime.utcnow().isoformat()
            },
            "breakout": {
                "description": "Captures breakouts from key support and resistance levels",
                "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
                "allowed_directions": [Direction.LONG, Direction.SHORT],
                "parameters": {
                    "signal_threshold": 0.75,
                    "hold_time_minutes": 120,
                    "take_profit_factor": 2.0,
                    "stop_loss_factor": 1.0
                },
                "indicators": ["BOLLINGER_BANDS", "ATR"],
                "created_at": datetime.utcnow().isoformat()
            },
            "reversal": {
                "description": "Identifies potential reversals at overbought/oversold levels",
                "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
                "allowed_directions": [Direction.LONG, Direction.SHORT],
                "parameters": {
                    "signal_threshold": 0.8,
                    "hold_time_minutes": 60,
                    "take_profit_factor": 1.2,
                    "stop_loss_factor": 1.0
                },
                "indicators": ["RSI", "STOCHASTIC"],
                "created_at": datetime.utcnow().isoformat()
            }
        }
        
        self.logger.info(f"Initialized {len(self.strategies)} default strategies")
    
    def _load_strategies(self):
        """Load strategies from disk"""
        try:
            strategies_file = os.path.join("data", "performance", "strategies.json")
            if os.path.exists(strategies_file) and os.path.getsize(strategies_file) > 0:
                try:
                    with open(strategies_file, 'r') as f:
                        self.strategies = json.load(f)
                    self.logger.info(f"Loaded {len(self.strategies)} strategies from disk")
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Corrupted strategies file: {e}. Will use defaults.")
                    # Remove corrupted file
                    os.remove(strategies_file)
            
            performance_file = os.path.join("data", "performance", "strategy_performance.json")
            if os.path.exists(performance_file) and os.path.getsize(performance_file) > 0:
                try:
                    with open(performance_file, 'r') as f:
                        self.strategy_performance = json.load(f)
                    self.logger.info(f"Loaded performance data for {len(self.strategy_performance)} strategies")
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Corrupted performance file: {e}. Starting with fresh data.")
                    # Remove corrupted file
                    os.remove(performance_file)
                    self.strategy_performance = {}
        except Exception as e:
            self.logger.error(f"Error loading strategies: {e}")
            # Initialize with defaults if loading fails
            self._initialize_default_strategies()
    
    def _save_strategies(self):
        """Save strategies to disk"""
        try:
            # Serialize strategies with proper handling of Enum objects
            strategies_serializable = self._prepare_for_serialization(self.strategies)
            performance_serializable = self._prepare_for_serialization(self.strategy_performance)
            
            strategies_file = os.path.join("data", "performance", "strategies.json")
            with open(strategies_file, 'w') as f:
                json.dump(strategies_serializable, f, indent=2)
            
            performance_file = os.path.join("data", "performance", "strategy_performance.json")
            with open(performance_file, 'w') as f:
                json.dump(performance_serializable, f, indent=2)
                
            self.logger.info(f"Saved {len(self.strategies)} strategies to disk")
        except Exception as e:
            self.logger.error(f"Error saving strategies: {e}")
            
    def _prepare_for_serialization(self, obj):
        """
        Prepare an object for JSON serialization by converting Enum objects to strings
        
        Args:
            obj: Object to prepare
            
        Returns:
            Serializable version of the object
        """
        if isinstance(obj, dict):
            return {k: self._prepare_for_serialization(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_serialization(item) for item in obj]
        elif isinstance(obj, Direction):
            return obj.value
        elif isinstance(obj, Confidence):
            return obj.value
        elif hasattr(obj, '__dict__'):
            # Handle custom objects by converting to dict
            serialized = {}
            for attr, value in obj.__dict__.items():
                serialized[attr] = self._prepare_for_serialization(value)
            return serialized
        else:
            return obj
    
    def _save_strategy_performance(self, strategy_name: str, performance: Dict):
        """
        Save performance data for a specific strategy
        
        Args:
            strategy_name: Strategy name
            performance: Performance data
        """
        try:
            # Create directory if needed
            strategy_dir = os.path.join("data", "performance", "strategies")
            os.makedirs(strategy_dir, exist_ok=True)
            
            # Save to strategy-specific file
            file_path = os.path.join(strategy_dir, f"{strategy_name}.json")
            with open(file_path, 'w') as f:
                performance_copy = performance.copy()
                
                # Limit the size of recent trades
                if "recent_trades" in performance_copy:
                    performance_copy["recent_trades"] = performance_copy["recent_trades"][-20:]
                
                json.dump(performance_copy, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving performance for {strategy_name}: {e}")
