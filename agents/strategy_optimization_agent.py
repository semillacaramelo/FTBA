
import asyncio
import logging
import json
import random
from datetime import datetime
from typing import Dict, List, Any

from system.agent import Agent
from system.core import Message, MessageType, Direction, Confidence, TradeProposal, TradeStatus

class StrategyOptimizationAgent(Agent):
    """
    Agent responsible for leveraging machine learning to continuously refine trading strategies
    based on performance metrics and market conditions.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.update_interval = config.get("update_interval_seconds", 300)
        self.learning_rate = config.get("learning_rate", 0.1)
        
        # Strategy parameters and performance metrics
        self.strategies = {}
        self.strategy_performance = {}
        self.market_regime = "neutral"  # Current market regime (trending, ranging, volatile)
        self.signals_cache = {}        # Recent technical and fundamental signals
        self.trades_history = []       # Recent trades for performance analysis
        
    async def setup(self):
        """Initialize the agent and subscribe to relevant message types"""
        await self.subscribe_to([
            MessageType.TECHNICAL_SIGNAL,
            MessageType.FUNDAMENTAL_UPDATE,
            MessageType.RISK_ASSESSMENT,
            MessageType.TRADE_RESULT,
            MessageType.SYSTEM_STATUS
        ])
        
        # Load strategy definitions
        await self.load_strategies()
        
        self.logger.info("Strategy Optimization Agent initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Strategy Optimization Agent shutting down")
    
    async def process_cycle(self):
        """Main processing loop - optimize strategies and generate trade proposals"""
        await self.analyze_performance()
        await self.optimize_strategies()
        await self.detect_market_regime()
        await self.generate_trade_proposals()
        await asyncio.sleep(self.update_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TECHNICAL_SIGNAL:
            await self.process_technical_signal(message)
        
        elif message.type == MessageType.FUNDAMENTAL_UPDATE:
            await self.process_fundamental_update(message)
        
        elif message.type == MessageType.RISK_ASSESSMENT:
            await self.process_risk_assessment(message)
        
        elif message.type == MessageType.TRADE_RESULT:
            await self.process_trade_result(message)
    
    async def load_strategies(self):
        """Load trading strategies and their parameters"""
        # In a real implementation, this would load from a database or configuration
        # For this example, we'll define some hardcoded strategy definitions
        
        self.strategies = {
            "trend_following": {
                "description": "Follows medium to long-term market trends",
                "parameters": {
                    "ema_short": 9,
                    "ema_long": 21,
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "confidence_threshold": 0.7
                },
                "best_regime": "trending",
                "timeframes": ["1h", "4h", "1d"],
                "enabled": True
            },
            "mean_reversion": {
                "description": "Trades price reversals to the mean",
                "parameters": {
                    "bollinger_period": 20,
                    "bollinger_std": 2.0,
                    "rsi_period": 7,
                    "rsi_overbought": 80,
                    "rsi_oversold": 20,
                    "confidence_threshold": 0.65
                },
                "best_regime": "ranging",
                "timeframes": ["15m", "1h"],
                "enabled": True
            },
            "breakout": {
                "description": "Trades price breakouts from consolidation",
                "parameters": {
                    "atr_period": 14,
                    "breakout_factor": 1.5,
                    "volume_increase_threshold": 2.0,
                    "consolidation_bars": 10,
                    "confidence_threshold": 0.75
                },
                "best_regime": "volatile",
                "timeframes": ["15m", "1h", "4h"],
                "enabled": True
            }
        }
        
        # Initialize performance metrics for each strategy
        for strategy_name in self.strategies:
            self.strategy_performance[strategy_name] = {
                "trades_count": 0,
                "win_rate": 0.5,  # Initial value
                "profit_factor": 1.0,  # Initial value
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "consecutive_losses": 0
            }
        
        self.logger.info(f"Loaded {len(self.strategies)} strategies")
    
    async def process_technical_signal(self, message: Message):
        """Process technical analysis signals"""
        signal_data = message.content.get("signal", {})
        timestamp = message.content.get("timestamp")
        
        if not signal_data:
            return
            
        symbol = signal_data.get("symbol")
        if not symbol:
            return
            
        # Cache the signal
        if symbol not in self.signals_cache:
            self.signals_cache[symbol] = {
                "technical": [],
                "fundamental": []
            }
        
        # Add to cache and limit size
        self.signals_cache[symbol]["technical"].append({
            "timestamp": timestamp,
            "data": signal_data
        })
        
        # Keep only latest 20 signals per symbol
        self.signals_cache[symbol]["technical"] = self.signals_cache[symbol]["technical"][-20:]
        
        # Check if we have enough signals to evaluate a trading opportunity
        await self.evaluate_trading_opportunity(symbol)
    
    async def process_fundamental_update(self, message: Message):
        """Process fundamental analysis updates"""
        update_data = message.content.get("update", {})
        timestamp = message.content.get("timestamp")
        
        if not update_data:
            return
            
        impact_currencies = update_data.get("impact_currency", [])
        
        # Cache the update for each impacted currency
        for currency in impact_currencies:
            # Find symbols that include this currency
            symbols = self.get_symbols_with_currency(currency)
            
            for symbol in symbols:
                if symbol not in self.signals_cache:
                    self.signals_cache[symbol] = {
                        "technical": [],
                        "fundamental": []
                    }
                
                self.signals_cache[symbol]["fundamental"].append({
                    "timestamp": timestamp,
                    "data": update_data
                })
                
                # Keep only latest 10 updates per symbol
                self.signals_cache[symbol]["fundamental"] = self.signals_cache[symbol]["fundamental"][-10:]
                
                # Check if we have a trading opportunity
                await self.evaluate_trading_opportunity(symbol)
    
    async def process_risk_assessment(self, message: Message):
        """Process risk assessment response"""
        approved = message.content.get("approved", False)
        proposal_id = message.content.get("proposal_id")
        
        if not approved:
            reason = message.content.get("reason", "Unknown reason")
            self.logger.info(f"Trade proposal {proposal_id} rejected: {reason}")
            
            # Update strategy performance based on rejected proposal
            strategy_name = self.get_strategy_for_proposal(proposal_id)
            if strategy_name:
                # Penalize the strategy slightly for rejected proposals
                self.update_strategy_confidence(strategy_name, -0.01)
        else:
            self.logger.info(f"Trade proposal {proposal_id} approved")
    
    async def process_trade_result(self, message: Message):
        """Process trade execution results"""
        result = message.content
        execution = result.get("execution", {})
        proposal_id = execution.get("proposal_id")
        pnl = result.get("pnl", 0.0)
        
        # Update trade history
        self.trades_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "proposal_id": proposal_id,
            "symbol": execution.get("symbol"),
            "direction": execution.get("direction"),
            "size": execution.get("executed_size"),
            "entry_price": execution.get("executed_price"),
            "exit_price": result.get("exit_price"),
            "pnl": pnl,
            "status": execution.get("status")
        })
        
        # Limit history size
        self.trades_history = self.trades_history[-100:]
        
        # Update strategy performance metrics
        strategy_name = self.get_strategy_for_proposal(proposal_id)
        if strategy_name:
            self.update_strategy_performance(strategy_name, pnl)
    
    async def evaluate_trading_opportunity(self, symbol):
        """Evaluate if there's a trading opportunity for a symbol"""
        if symbol not in self.signals_cache:
            return
            
        technical_signals = self.signals_cache[symbol].get("technical", [])
        fundamental_updates = self.signals_cache[symbol].get("fundamental", [])
        
        # Need at least some signals to proceed
        if not technical_signals:
            return
            
        # Evaluate each strategy for this symbol
        for strategy_name, strategy in self.strategies.items():
            if not strategy.get("enabled", True):
                continue
                
            # Check if strategy is suitable for current market regime
            if strategy.get("best_regime") != self.market_regime and random.random() > 0.3:
                # 70% chance to skip strategies not optimal for current regime
                continue
                
            # Check if we have technical signals in the strategy's preferred timeframes
            valid_signals = [
                s for s in technical_signals 
                if s["data"].get("timeframe") in strategy.get("timeframes", [])
            ]
            
            if not valid_signals:
                continue
                
            # Basic implementation - check for directional agreement in latest signals
            latest_signals = valid_signals[-3:]  # Last 3 signals
            
            if not latest_signals:
                continue
                
            # Count signals by direction
            long_signals = sum(1 for s in latest_signals if s["data"].get("direction") == Direction.LONG.value)
            short_signals = sum(1 for s in latest_signals if s["data"].get("direction") == Direction.SHORT.value)
            
            # Determine overall direction
            direction = None
            if long_signals > short_signals and long_signals >= 2:
                direction = Direction.LONG
            elif short_signals > long_signals and short_signals >= 2:
                direction = Direction.SHORT
            else:
                continue  # No clear direction
            
            # Calculate confidence based on signal agreement and strategy performance
            confidence = (max(long_signals, short_signals) / len(latest_signals)) * \
                         self.strategy_performance[strategy_name].get("win_rate", 0.5)
            
            # Check fundamental alignment if available
            fundamental_alignment = Confidence.MEDIUM  # Default
            if fundamental_updates:
                # Simple check if any fundamental updates align with the direction
                aligned_updates = sum(1 for u in fundamental_updates[-3:] 
                                  if u["data"].get("impact_assessment") == direction.value)
                
                if aligned_updates > 0:
                    fundamental_alignment = Confidence.HIGH
                elif aligned_updates < 0:
                    fundamental_alignment = Confidence.LOW
            
            # Apply confidence threshold from strategy
            confidence_threshold = strategy["parameters"].get("confidence_threshold", 0.65)
            if confidence >= confidence_threshold:
                # Generate trade proposal
                await self.create_trade_proposal(
                    symbol, 
                    direction, 
                    strategy_name,
                    self.confidence_level_from_value(confidence),
                    fundamental_alignment
                )
    
    async def create_trade_proposal(self, symbol, direction, strategy_name, 
                                   technical_confidence, fundamental_alignment):
        """Create and send a trade proposal"""
        # Generate a unique proposal ID
        proposal_id = f"prop_{strategy_name}_{int(datetime.utcnow().timestamp())}"
        
        # Get current price (in a real implementation, this would come from market data)
        current_price = 1.1000  # Placeholder
        
        # Calculate entry, stop loss and take profit levels
        entry_price = current_price
        
        # Simple fixed pip values (in a real implementation, these would be dynamic)
        stop_pips = 30
        target_pips = 50
        
        if direction == Direction.LONG:
            stop_loss = entry_price - (stop_pips / 10000)
            take_profit = entry_price + (target_pips / 10000)
        else:  # SHORT
            stop_loss = entry_price + (stop_pips / 10000)
            take_profit = entry_price - (target_pips / 10000)
        
        # Calculate position size (in a real implementation, this would be based on risk models)
        size = 0.1  # Placeholder standard lot size
        
        # Calculate overall risk score (0-100, higher is riskier)
        risk_score = 50.0  # Default medium risk
        
        # Adjust risk based on confidence levels
        if technical_confidence == Confidence.HIGH:
            risk_score -= 10
        elif technical_confidence == Confidence.LOW:
            risk_score += 10
            
        if fundamental_alignment == Confidence.HIGH:
            risk_score -= 10
        elif fundamental_alignment == Confidence.LOW:
            risk_score += 10
        
        # Create the trade proposal
        proposal = TradeProposal(
            id=proposal_id,
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_limit_seconds=3600,  # 1 hour expiry
            strategy_name=strategy_name,
            technical_confidence=technical_confidence,
            fundamental_alignment=fundamental_alignment,
            risk_score=risk_score,
            status=TradeStatus.PROPOSED
        )
        
        # Send the proposal to the Risk Management Agent
        await self.send_message(
            MessageType.TRADE_PROPOSAL,
            {
                "proposal": proposal.__dict__,
                "timestamp": datetime.utcnow().isoformat()
            },
            recipients=["risk_management"]
        )
        
        self.logger.info(f"Sent trade proposal {proposal_id} for {symbol} {direction.value}")
    
    async def analyze_performance(self):
        """Analyze trading performance to inform strategy optimization"""
        if not self.trades_history:
            return
            
        # Calculate overall performance metrics
        total_trades = len(self.trades_history)
        profitable_trades = sum(1 for t in self.trades_history if t.get("pnl", 0) > 0)
        losing_trades = sum(1 for t in self.trades_history if t.get("pnl", 0) < 0)
        
        if total_trades > 0:
            win_rate = profitable_trades / total_trades
            self.logger.info(f"Overall performance: {win_rate:.2f} win rate over {total_trades} trades")
        
        # Analyze performance by strategy, symbol, timeframe, etc.
        # This would be much more detailed in a real implementation
    
    async def optimize_strategies(self):
        """Optimize strategy parameters based on performance"""
        # In a real implementation, this would use machine learning techniques
        # For this example, we'll make simple adjustments based on performance
        
        for strategy_name, performance in self.strategy_performance.items():
            if strategy_name not in self.strategies:
                continue
                
            # Skip optimization if not enough data
            if performance.get("trades_count", 0) < 10:
                continue
                
            strategy = self.strategies[strategy_name]
            
            # Adjust confidence threshold based on win rate
            win_rate = performance.get("win_rate", 0.5)
            current_threshold = strategy["parameters"].get("confidence_threshold", 0.65)
            
            if win_rate < 0.4:
                # Increase threshold if win rate is low (more conservative)
                new_threshold = min(0.9, current_threshold + self.learning_rate)
                strategy["parameters"]["confidence_threshold"] = new_threshold
                self.logger.info(f"Increased confidence threshold for {strategy_name} to {new_threshold:.2f}")
            
            elif win_rate > 0.6:
                # Decrease threshold if win rate is high (more aggressive)
                new_threshold = max(0.5, current_threshold - self.learning_rate / 2)
                strategy["parameters"]["confidence_threshold"] = new_threshold
                self.logger.info(f"Decreased confidence threshold for {strategy_name} to {new_threshold:.2f}")
            
            # Additional parameter optimization would go here
            # This could include adjusting indicator periods, factor values, etc.
    
    async def detect_market_regime(self):
        """Detect the current market regime (trending, ranging, volatile)"""
        # In a real implementation, this would analyze market conditions
        # For this example, we'll use a simple placeholder
        
        # Simple random change occasionally for demonstration
        if random.random() < 0.1:  # 10% chance to change regime
            regimes = ["trending", "ranging", "volatile"]
            new_regime = random.choice(regimes)
            
            if new_regime != self.market_regime:
                self.logger.info(f"Market regime changed from {self.market_regime} to {new_regime}")
                self.market_regime = new_regime
    
    async def generate_trade_proposals(self):
        """Proactively generate trade proposals based on current market conditions"""
        # Most proposals will be generated in response to signals
        # This method could generate proposals for specific strategies
        # that don't rely on immediate signals (e.g., scheduled trades)
        pass
    
    def update_strategy_performance(self, strategy_name, pnl):
        """Update performance metrics for a strategy based on trade result"""
        if strategy_name not in self.strategy_performance:
            return
            
        perf = self.strategy_performance[strategy_name]
        
        # Update trade count
        perf["trades_count"] = perf.get("trades_count", 0) + 1
        
        # Update win/loss metrics
        if pnl > 0:
            # Profitable trade
            perf["consecutive_losses"] = 0
            profitable_trades = perf.get("trades_count", 1) * perf.get("win_rate", 0.5)
            profitable_trades += 1
            perf["win_rate"] = profitable_trades / perf["trades_count"]
            
            # Update average profit
            perf["avg_profit"] = (perf.get("avg_profit", 0) * (profitable_trades - 1) + pnl) / profitable_trades
            
        elif pnl < 0:
            # Losing trade
            perf["consecutive_losses"] = perf.get("consecutive_losses", 0) + 1
            profitable_trades = perf.get("trades_count", 1) * perf.get("win_rate", 0.5)
            perf["win_rate"] = profitable_trades / perf["trades_count"]
            
            # Update average loss
            losing_trades = perf["trades_count"] - profitable_trades
            perf["avg_loss"] = (perf.get("avg_loss", 0) * (losing_trades - 1) + abs(pnl)) / losing_trades
        
        # Calculate profit factor
        if perf.get("avg_loss", 0) > 0:
            perf["profit_factor"] = (perf.get("avg_profit", 0) * perf.get("win_rate", 0)) / \
                                   (perf.get("avg_loss", 1) * (1 - perf.get("win_rate", 0)))
        
        # Disable strategy if too many consecutive losses
        if perf["consecutive_losses"] >= 5:
            self.logger.warning(f"Strategy {strategy_name} has {perf['consecutive_losses']} consecutive losses. Disabling.")
            self.strategies[strategy_name]["enabled"] = False
    
    def update_strategy_confidence(self, strategy_name, adjustment):
        """Adjust strategy confidence based on feedback"""
        if strategy_name not in self.strategy_performance:
            return
            
        # Simple adjustment to win rate (proxy for confidence)
        current_win_rate = self.strategy_performance[strategy_name].get("win_rate", 0.5)
        new_win_rate = max(0.1, min(0.9, current_win_rate + adjustment))
        self.strategy_performance[strategy_name]["win_rate"] = new_win_rate
    
    def get_strategy_for_proposal(self, proposal_id):
        """Find the strategy that generated a proposal"""
        # In a real implementation, this would look up in a database
        # For this example, we'll parse from the proposal ID format we used
        if proposal_id and proposal_id.startswith("prop_"):
            parts = proposal_id.split("_")
            if len(parts) > 1:
                return parts[1]
        return None
    
    def get_symbols_with_currency(self, currency):
        """Get forex pairs that include a specific currency"""
        # In a real implementation, this would come from configuration or market data
        # For this example, we'll use a simple mapping
        currency_map = {
            "USD": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
            "EUR": ["EUR/USD", "EUR/JPY", "EUR/GBP", "EUR/CHF"],
            "GBP": ["GBP/USD", "EUR/GBP", "GBP/JPY"],
            "JPY": ["USD/JPY", "EUR/JPY", "GBP/JPY"],
            "CHF": ["USD/CHF", "EUR/CHF"],
            "AUD": ["AUD/USD", "AUD/JPY"]
        }
        
        return currency_map.get(currency, [])
    
    def confidence_level_from_value(self, value):
        """Convert a numeric confidence value to a Confidence enum"""
        if value >= 0.8:
            return Confidence.VERY_HIGH
        elif value >= 0.65:
            return Confidence.HIGH
        elif value >= 0.4:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW
