import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, Confidence, 
    TradeProposal, TechnicalSignal
)

class RiskManagementAgent(Agent):
    def __init__(self, agent_id: str, message_broker, config):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.max_account_risk = config.get("max_account_risk_percent", 2.0) / 100
        self.max_position_size_percent = config.get("max_position_size_percent", 5.0) / 100
        self.account_balance = config.get("initial_balance", 100000.0)
        self.open_positions = {}  # symbol -> position details
        self.daily_pnl = 0.0
        self.max_daily_loss = config.get("max_daily_loss_percent", 5.0) / 100
        self.correlation_matrix = {}  # symbol pairs -> correlation
        self.volatility_data = {}  # symbol -> historic volatility
        self.update_interval = config.get("update_interval_seconds", 60)  # 1 minute
        self.last_update_time = datetime.min
        
    async def setup(self):
        """Set up the agent when starting"""
        await self.subscribe_to([
            MessageType.TRADE_PROPOSAL,
            MessageType.TRADE_EXECUTION, 
            MessageType.TRADE_RESULT,
            MessageType.TECHNICAL_SIGNAL,
            MessageType.FUNDAMENTAL_UPDATE
        ])
        await self.initialize_risk_models()
        self.logger.info("Risk Management Agent setup complete.")
    
    async def cleanup(self):
        """Clean up when agent is stopping"""
        self.open_positions = {}
        self.logger.info("Risk Management Agent cleaned up")
    
    async def process_cycle(self):
        """Process a single cycle of the agent's main loop"""
        now = datetime.utcnow()
        
        # Check if it's time to update risk models
        time_since_last = (now - self.last_update_time).total_seconds()
        if time_since_last >= self.update_interval:
            await self.update_risk_models()
            self.last_update_time = now
        
        # Check for breached risk thresholds
        await self.check_portfolio_risk()
        
        # Sleep to maintain the desired update frequency
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TRADE_PROPOSAL:
            # Evaluate and approve/reject trade proposals
            await self.evaluate_trade_proposal(message.content.get("proposal"))
        
        elif message.type == MessageType.TRADE_EXECUTION:
            # Update position tracking
            execution = message.content.get("execution")
            await self.update_positions(execution)
        
        elif message.type == MessageType.TRADE_RESULT:
            # Update PnL and risk metrics
            result = message.content
            await self.update_pnl(result)
        
        elif message.type == MessageType.TECHNICAL_SIGNAL:
            # Use technical data to update volatility models
            signal = message.content.get("signal")
            if signal:
                await self.update_volatility_from_signal(signal)
        
        elif message.type == MessageType.FUNDAMENTAL_UPDATE:
            # Use fundamental data to adjust risk parameters
            update = message.content.get("update")
            if update:
                await self.adjust_risk_from_fundamental(update)
    
    async def initialize_risk_models(self):
        """Initialize risk models with historical data"""
        # In a real implementation, this would load historical volatility and correlation data
        # Here we'll initialize with sample values
        
        # Sample forex pairs
        pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD", "USD/CAD", "EUR/GBP"]
        
        # Initialize volatility data (typical daily % volatility)
        for pair in pairs:
            self.volatility_data[pair] = {
                "EUR/USD": 0.5, "GBP/USD": 0.7, "USD/JPY": 0.6, 
                "USD/CHF": 0.6, "AUD/USD": 0.8, "NZD/USD": 0.9,
                "USD/CAD": 0.6, "EUR/GBP": 0.5
            }.get(pair, 0.7)  # Default 0.7% daily volatility
        
        # Initialize correlation matrix
        # In a real system, this would be calculated from historical price movements
        # Here we use typical forex correlations
        for pair1 in pairs:
            for pair2 in pairs:
                key = f"{pair1}_{pair2}"
                if pair1 == pair2:
                    self.correlation_matrix[key] = 1.0  # Self correlation is 1.0
                elif "EUR" in pair1 and "EUR" in pair2:
                    self.correlation_matrix[key] = 0.8  # EUR pairs tend to be correlated
                elif "USD" in pair1 and "USD" in pair2:
                    self.correlation_matrix[key] = 0.6  # USD pairs have moderate correlation
                else:
                    # Random correlation between -0.5 and 0.5 for other pairs
                    self.correlation_matrix[key] = (np.random.random() - 0.5)
        
        self.logger.info(f"Initialized risk models for {len(pairs)} currency pairs")
    
    async def update_risk_models(self):
        """Update risk models with recent data"""
        # In a real implementation, this would recalculate volatility and correlations
        # based on recent price movements. Here we simulate small changes.
        
        # Update volatility with small random changes
        for pair in self.volatility_data:
            change = (np.random.random() - 0.5) * 0.1  # +/- 0.05%
            self.volatility_data[pair] = max(0.1, self.volatility_data[pair] + change)
        
        # In a real system, correlations would also be updated
        # Here we'll leave them static for simplicity
        
        self.logger.debug("Updated risk models")
    
    async def check_portfolio_risk(self):
        """Check for overall portfolio risk thresholds"""
        # Calculate current exposure by currency
        currency_exposure = {}
        total_exposure = 0.0
        
        for symbol, position in self.open_positions.items():
            size = position.get("size", 0)
            direction_mult = 1 if position.get("direction") == Direction.LONG else -1
            exposure = size * direction_mult
            
            # Extract currencies from the symbol
            if "/" in symbol:
                base, quote = symbol.split("/")
                
                # Base currency exposure
                if base not in currency_exposure:
                    currency_exposure[base] = 0
                currency_exposure[base] += exposure
                
                # Quote currency exposure (opposite sign)
                if quote not in currency_exposure:
                    currency_exposure[quote] = 0
                currency_exposure[quote] -= exposure
            
            total_exposure += abs(exposure)
        
        # Check if we're over-exposed to any single currency
        max_currency_exposure = self.account_balance * self.max_account_risk * 2
        for currency, exposure in currency_exposure.items():
            if abs(exposure) > max_currency_exposure:
                await self.send_risk_alert(f"Over-exposed to {currency}: {exposure:.2f}")
        
        # Check daily PnL against max daily loss
        if self.daily_pnl < -self.account_balance * self.max_daily_loss:
            await self.send_risk_alert(f"Daily loss threshold breached: {self.daily_pnl:.2f}")
            # In a real system, this might trigger an automatic trading halt
    
    async def evaluate_trade_proposal(self, proposal_dict):
        """Evaluate a trade proposal and approve/reject based on risk parameters"""
        if not proposal_dict:
            return
        
        # Convert dictionary to object for easier handling
        proposal = TradeProposal(**proposal_dict)
        symbol = proposal.symbol
        direction = proposal.direction
        size = proposal.size
        
        # Assign a risk score based on various factors
        risk_score = 0.0
        
        # 1. Check position size against max allowed
        max_position_size = self.account_balance * self.max_position_size_percent
        if size > max_position_size:
            risk_score += 0.5
            size = max_position_size  # Cap the size
        
        # 2. Check volatility
        volatility = self.volatility_data.get(symbol, 1.0)
        risk_score += volatility * 0.2  # Higher volatility = higher risk
        
        # 3. Check correlation with existing positions
        for open_symbol, position in self.open_positions.items():
            corr_key = f"{symbol}_{open_symbol}"
            correlation = self.correlation_matrix.get(corr_key, 0)
            open_direction = position.get("direction")
            
            # If directions match and correlation is positive, risk increases
            # If directions oppose and correlation is positive, risk decreases
            direction_mult = 1 if direction == open_direction else -1
            risk_score += correlation * direction_mult * 0.1
        
        # 4. Adjust stop loss based on volatility
        volatility_atr = volatility * 100  # Convert to pips approximation
        
        # Ensure stop loss is at least 1x daily volatility
        min_stop_distance = volatility_atr * 1.0
        if proposal.stop_loss < min_stop_distance:
            proposal.stop_loss = min_stop_distance
        
        # Calculate maximum risk per trade as % of account
        max_risk_per_trade = self.account_balance * self.max_account_risk
        
        # Calculate potential loss in account currency
        potential_loss = size * (proposal.stop_loss / 10000)  # Convert pips to price change
        
        # Adjust size if risk is too high
        if potential_loss > max_risk_per_trade:
            size = max_risk_per_trade / (proposal.stop_loss / 10000)
            proposal.size = size
        
        # Make the decision
        approved = risk_score < 1.0 and self.daily_pnl > -self.account_balance * self.max_daily_loss * 0.8
        
        # Create risk assessment
        assessment = RiskAssessment(
            symbol=symbol,
            max_position_size=max_position_size,
            recommended_leverage=5.0,  # Default leverage
            stop_loss_pips=proposal.stop_loss,
            take_profit_pips=proposal.take_profit,
            max_daily_loss=self.account_balance * self.max_daily_loss,
            current_exposure=self.open_positions,
            market_volatility=volatility
        )
        
        # Update proposal with our assessment
        proposal.risk_score = risk_score
        proposal.size = size  # Potentially adjusted size
        
        # Update status based on our decision
        if approved:
            proposal.status = TradeStatus.APPROVED
            self.logger.info(f"Trade proposal approved: {symbol} {direction.value} {size}")
        else:
            proposal.status = TradeStatus.REJECTED
            self.logger.info(f"Trade proposal rejected: {symbol} {direction.value} {size}, risk_score: {risk_score}")
        
        # Send back our assessment and updated proposal
        await self.send_message(
            MessageType.RISK_ASSESSMENT,
            {
                "assessment": assessment.__dict__,
                "proposal": proposal.__dict__,
                "approved": approved
            },
            recipients=[proposal_dict.get("sender", "")]
        )
    
    async def update_positions(self, execution):
        """Update position tracking based on trade execution"""
        if not execution:
            return
        
        symbol = execution.get("symbol")
        direction = execution.get("direction")
        size = execution.get("executed_size", 0)
        price = execution.get("executed_price", 0)
        status = execution.get("status")
        
        # If position was opened
        if status == TradeStatus.EXECUTED.value:
            # If we already have a position in this symbol
            if symbol in self.open_positions:
                existing = self.open_positions[symbol]
                existing_size = existing.get("size", 0)
                existing_direction = existing.get("direction")
                
                # If same direction, add to position
                if direction == existing_direction:
                    new_size = existing_size + size
                    avg_price = (existing.get("price", 0) * existing_size + price * size) / new_size
                    self.open_positions[symbol].update({
                        "size": new_size,
                        "price": avg_price
                    })
                else:
                    # If opposite direction, reduce position
                    new_size = existing_size - size
                    if new_size > 0:
                        # Original position is larger, just reduce size
                        self.open_positions[symbol]["size"] = new_size
                    elif new_size < 0:
                        # New position is larger, flip direction and update size
                        self.open_positions[symbol] = {
                            "size": abs(new_size),
                            "price": price,
                            "direction": direction
                        }
                    else:
                        # Positions cancel out exactly
                        del self.open_positions[symbol]
            else:
                # New position
                self.open_positions[symbol] = {
                    "size": size,
                    "price": price,
                    "direction": direction
                }
            
            self.logger.info(f"Updated position tracking for {symbol}: {self.open_positions.get(symbol)}")
    
    async def update_pnl(self, result):
        """Update profit and loss tracking"""
        if not result:
            return
        
        profit = result.get("profit", 0)
        self.daily_pnl += profit
        self.account_balance += profit
        
        symbol = result.get("symbol")
        if symbol in self.open_positions and result.get("position_closed", False):
            del self.open_positions[symbol]
            self.logger.info(f"Position closed for {symbol}, profit: {profit}")
    
    async def update_volatility_from_signal(self, signal):
        """Update volatility models based on technical signals"""
        if not signal:
            return
        
        symbol = signal.get("symbol")
        if symbol and symbol in self.volatility_data:
            # Adjust volatility slightly based on signal confidence
            confidence = signal.get("confidence")
            if confidence:
                # Convert confidence to numeric value
                conf_value = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}.get(confidence, 0)
                
                # Higher confidence signals might indicate more volatile market conditions
                if conf_value >= 3:  # HIGH or VERY_HIGH
                    self.volatility_data[symbol] *= 1.05  # Increase volatility estimate by 5%
    
    async def adjust_risk_from_fundamental(self, update):
        """Adjust risk parameters based on fundamental updates"""
        if not update:
            return
        
        event = update.get("event")
        
        # If this is a high-impact event notification
        if event and "Upcoming Event" in event:
            # Extract currency
            impact_currency = update.get("impact_currency", [])
            if impact_currency:
                currency = impact_currency[0]
                
                # Temporarily increase volatility expectations for pairs with this currency
                for symbol in self.volatility_data:
                    if currency in symbol:
                        self.volatility_data[symbol] *= 1.2  # Increase volatility expectation by 20%
                        self.logger.info(f"Increased volatility for {symbol} due to upcoming event for {currency}")
    
    async def send_risk_alert(self, message):
        """Send a risk alert to other agents"""
        await self.send_message(
            MessageType.SYSTEM_STATUS,
            {
                "alert": "RISK_ALERT",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        self.logger.warning(f"RISK ALERT: {message}")
