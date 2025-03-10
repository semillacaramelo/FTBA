import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import uuid

from system.agent import Agent
from system.core import (
    Message, MessageType, Direction, Confidence,
    TradeProposal, TradeStatus, TechnicalSignal, FundamentalUpdate
)

class StrategyOptimizationAgent(Agent):
    def __init__(self, agent_id: str, message_broker, config):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.strategies = {}  # strategy_name -> strategy_config
        self.strategy_performance = {}  # strategy_name -> performance metrics
        self.technical_signals = {}  # symbol -> list of recent signals
        self.fundamental_updates = {}  # symbol -> list of recent updates
        self.risk_assessments = {}  # symbol -> latest risk assessment
        self.trade_history = []  # List of past trades and results
        self.learning_rate = config.get("learning_rate", 0.1)
        self.update_interval = config.get("update_interval_seconds", 300)  # 5 minutes
        self.last_update_time = datetime.min
        self.watchlist = config.get("watchlist", ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"])
        
    async def setup(self):
        """Set up the agent when starting"""
        await self.subscribe_to([
            MessageType.TECHNICAL_SIGNAL,
            MessageType.FUNDAMENTAL_UPDATE,
            MessageType.RISK_ASSESSMENT,
            MessageType.TRADE_RESULT
        ])
        await self.initialize_strategies()
        self.logger.info("Strategy Optimization Agent setup complete.")
    
    async def cleanup(self):
        """Clean up when agent is stopping"""
        # Save strategy performance metrics for future sessions
        self.logger.info("Strategy Optimization Agent cleaned up")
    
    async def process_cycle(self):
        """Process a single cycle of the agent's main loop"""
        now = datetime.utcnow()
        
        # Check if it's time to update strategies
        time_since_last = (now - self.last_update_time).total_seconds()
        if time_since_last >= self.update_interval:
            await self.optimize_strategies()
            self.last_update_time = now
        
        # Check for trading opportunities
        await self.identify_trading_opportunities()
        
        # Clean up old data
        await self.clean_old_data()
        
        # Sleep to maintain the desired update frequency
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TECHNICAL_SIGNAL:
            # Store technical signals for strategy application
            signal = message.content.get("signal")
            if signal:
                await self.process_technical_signal(signal)
        
        elif message.type == MessageType.FUNDAMENTAL_UPDATE:
            # Store fundamental updates for strategy application
            update = message.content.get("update")
            if update:
                await self.process_fundamental_update(update)
        
        elif message.type == MessageType.RISK_ASSESSMENT:
            # Update our risk parameters based on risk assessment
            assessment = message.content.get("assessment")
            if assessment:
                symbol = assessment.get("symbol")
                if symbol:
                    self.risk_assessments[symbol] = assessment
        
        elif message.type == MessageType.TRADE_RESULT:
            # Learn from trade results
            await self.learn_from_trade_result(message.content)
    
    async def initialize_strategies(self):
        """Initialize trading strategies"""
        # Define some basic strategies
        self.strategies = {
            "trend_following": {
                "type": "trend",
                "description": "Follows medium-term trends identified by technical indicators",
                "timeframes": ["1h", "4h"],
                "technical_weight": 0.7,
                "fundamental_weight": 0.3,
                "required_signal_strength": 2.0,
                "profit_target_pips": 100,
                "stop_loss_pips": 50,
                "performance": {
                    "win_rate": 0.55,
                    "profit_factor": 1.2,
                    "avg_win_pips": 80,
                    "avg_loss_pips": 40,
                    "trades_count": 0
                }
            },
            "breakout": {
                "type": "breakout",
                "description": "Identifies and trades breakouts from consolidation patterns",
                "timeframes": ["15m", "1h"],
                "technical_weight": 0.8,
                "fundamental_weight": 0.2,
                "required_signal_strength": 2.5,
                "profit_target_pips": 50,
                "stop_loss_pips": 30,
                "performance": {
                    "win_rate": 0.48,
                    "profit_factor": 1.3,
                    "avg_win_pips": 45,
                    "avg_loss_pips": 25,
                    "trades_count": 0
                }
            },
            "mean_reversion": {
                "type": "reversion",
                "description": "Trades reversals back to the mean after price extremes",
                "timeframes": ["1h", "4h"],
                "technical_weight": 0.6,
                "fundamental_weight": 0.4,
                "required_signal_strength": 2.2,
                "profit_target_pips": 60,
                "stop_loss_pips": 40,
                "performance": {
                    "win_rate": 0.6,
                    "profit_factor": 1.1,
                    "avg_win_pips": 40,
                    "avg_loss_pips": 35,
                    "trades_count": 0
                }
            },
            "news_momentum": {
                "type": "news",
                "description": "Trades momentum after significant economic news releases",
                "timeframes": ["5m", "15m"],
                "technical_weight": 0.3,
                "fundamental_weight": 0.7,
                "required_signal_strength": 3.0,
                "profit_target_pips": 40,
                "stop_loss_pips": 25,
                "performance": {
                    "win_rate": 0.52,
                    "profit_factor": 1.25,
                    "avg_win_pips": 35,
                    "avg_loss_pips": 20,
                    "trades_count": 0
                }
            }
        }
        
        self.logger.info(f"Initialized {len(self.strategies)} trading strategies")
    
    async def optimize_strategies(self):
        """Optimize strategies based on recent performance"""
        # In a real system, this would run ML algorithms to optimize parameters
        # Here we'll do some simple adjustments based on recent performance
        
        for name, strategy in self.strategies.items():
            performance = strategy.get("performance", {})
            trades_count = performance.get("trades_count", 0)
            
            if trades_count > 10:  # Only optimize if we have enough data
                win_rate = performance.get("win_rate", 0.5)
                profit_factor = performance.get("profit_factor", 1.0)
                
                # Adjust stop loss and take profit based on performance
                if win_rate > 0.55 and profit_factor > 1.2:
                    # Strategy is doing well - can we increase profit target?
                    strategy["profit_target_pips"] *= 1.05  # Increase by 5%
                    self.logger.info(f"Increased profit target for strategy {name}")
                elif win_rate < 0.45 or profit_factor < 0.95:
                    # Strategy is struggling - reduce stop loss to cut losses faster
                    strategy["stop_loss_pips"] *= 0.95  # Decrease by 5%
                    self.logger.info(f"Decreased stop loss for strategy {name}")
        
        self.logger.debug("Optimized trading strategies")
    
    async def identify_trading_opportunities(self):
        """Identify potential trading opportunities based on signals and strategies"""
        for symbol in self.watchlist:
            # Skip if we don't have enough data
            if symbol not in self.technical_signals or not self.technical_signals[symbol]:
                continue
            
            # Evaluate each strategy for this symbol
            for strategy_name, strategy in self.strategies.items():
                score, direction = await self.score_opportunity(symbol, strategy)
                
                # If score exceeds threshold, propose a trade
                if score >= strategy["required_signal_strength"]:
                    await self.propose_trade(symbol, direction, strategy_name, strategy, score)
    
    async def score_opportunity(self, symbol, strategy):
        """Score a trading opportunity for a specific symbol and strategy"""
        tech_weight = strategy.get("technical_weight", 0.5)
        fund_weight = strategy.get("fundamental_weight", 0.5)
        strategy_type = strategy.get("type")
        timeframes = strategy.get("timeframes", [])
        
        # Calculate technical score
        tech_score = 0
        tech_count = 0
        tech_direction = Direction.NEUTRAL
        
        if symbol in self.technical_signals:
            for signal in self.technical_signals[symbol]:
                # Skip old signals
                if (datetime.utcnow() - datetime.fromisoformat(signal.get("timestamp", ""))).total_seconds() > 3600:
                    continue
                
                # Check if signal matches timeframe for the strategy
                signal_timeframe = signal.get("timeframe")
                if signal_timeframe in timeframes:
                    # Determine signal strength based on confidence
                    confidence = signal.get("confidence", "MEDIUM")
                    conf_value = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}.get(confidence, 2)
                    
                    # Direction impact
                    direction = signal.get("direction")
                    dir_value = 1 if direction == Direction.LONG.value else -1 if direction == Direction.SHORT.value else 0
                    
                    tech_score += dir_value * conf_value
                    tech_count += 1
                    
                    # For trend strategy, prioritize signals on longer timeframes
                    if strategy_type == "trend" and signal_timeframe in ["1h", "4h", "1d"]:
                        tech_score += dir_value * conf_value * 0.5  # Extra weight
                    
                    # For breakout strategy, prioritize high momentum signals
                    if strategy_type == "breakout" and conf_value >= 3:
                        tech_score += dir_value * conf_value * 0.5  # Extra weight
                    
                    # For mean reversion, look for extreme signals in opposite direction
                    if strategy_type == "reversion" and conf_value >= 3:
                        tech_score -= dir_value * conf_value * 0.5  # Reverse logic
        
        # Normalize technical score
        if tech_count > 0:
            tech_score = tech_score / tech_count
            tech_direction = Direction.LONG if tech_score > 0 else Direction.SHORT if tech_score < 0 else Direction.NEUTRAL
        
        # Calculate fundamental score
        fund_score = 0
        fund_count = 0
        fund_direction = Direction.NEUTRAL
        
        # Extract currencies from symbol
        base_currency = quote_currency = None
        if "/" in symbol:
            base_currency, quote_currency = symbol.split("/")
        
        if base_currency and quote_currency:
            # Look at fundamental updates for both currencies
            for currency in [base_currency, quote_currency]:
                if currency in self.fundamental_updates: