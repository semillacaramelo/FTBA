
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import logging

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, Confidence, TradeStatus,
    TradeProposal, TechnicalSignal, RiskAssessment
)

class RiskManagementAgent(Agent):
    """
    Agent responsible for evaluating trade proposals against risk parameters,
    ensuring portfolio-level risk control, and preventing excessive exposure.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict = None):
        """
        Initialize the Risk Management Agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker for communication
            config: Agent configuration dictionary
        """
        super().__init__(agent_id, message_broker)
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.update_interval = self.config.get("update_interval_seconds", 60)
        
        # Risk parameters
        self.max_account_risk_percent = self.config.get("max_account_risk_percent", 2.0)
        self.max_position_size_percent = self.config.get("max_position_size_percent", 5.0)
        self.max_daily_loss_percent = self.config.get("max_daily_loss_percent", 5.0)
        
        # Portfolio tracking
        self.account_balance = 10000.0  # Default starting balance
        self.open_positions = {}  # Symbol -> position details
        self.daily_pnl = 0.0
        self.risk_assessments = {}  # Symbol -> risk assessment
        self.last_processed_time = datetime.utcnow()
        
        # Volatility tracking
        self.market_volatility = {}  # Symbol -> volatility
    
    async def setup(self):
        """Initialize the agent"""
        self.logger.info("Setting up Risk Management Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.TRADE_PROPOSAL,
            MessageType.TRADE_EXECUTION,
            MessageType.TRADE_RESULT,
            MessageType.TECHNICAL_SIGNAL,
            MessageType.FUNDAMENTAL_UPDATE
        ])
        
        # Initialize risk assessments for common symbols
        common_symbols = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"]
        for symbol in common_symbols:
            self.risk_assessments[symbol] = self._create_default_risk_assessment(symbol)
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Risk Management Agent")
    
    async def process_cycle(self):
        """Main processing cycle"""
        # Check if it's time to update
        current_time = datetime.utcnow()
        if (current_time - self.last_processed_time).total_seconds() >= self.update_interval:
            self.logger.debug("Running risk management cycle")
            
            # Update risk assessments
            await self.update_risk_assessments()
            
            # Check circuit breakers (trading halts due to excessive losses)
            await self.check_circuit_breakers()
            
            # Update the last processed time
            self.last_processed_time = current_time
        
        # Sleep to prevent CPU spinning
        await asyncio.sleep(1)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TRADE_PROPOSAL:
            # Evaluate trade proposal against risk parameters
            await self.evaluate_trade_proposal(message)
        
        elif message.type == MessageType.TRADE_EXECUTION:
            # Update portfolio with new trade
            await self.update_portfolio_with_trade(message)
        
        elif message.type == MessageType.TRADE_RESULT:
            # Update performance metrics with trade result
            await self.update_performance_metrics(message)
        
        elif message.type == MessageType.TECHNICAL_SIGNAL:
            # Update volatility metrics based on technical signals
            await self.update_volatility_metrics(message)
        
        elif message.type == MessageType.FUNDAMENTAL_UPDATE:
            # Adjust risk assessments based on fundamental data
            await self.adjust_risk_for_fundamental_update(message)
    
    async def evaluate_trade_proposal(self, message: Message):
        """
        Evaluate a trade proposal against risk parameters
        
        Args:
            message: Message containing the trade proposal
        """
        self.logger.info("Evaluating trade proposal")
        
        # Extract trade proposal from message
        proposal_data = message.content.get("proposal", {})
        try:
            if isinstance(proposal_data, dict):
                proposal = TradeProposal(**proposal_data)
            else:
                proposal = proposal_data
            
            symbol = proposal.symbol
            direction = proposal.direction
            size = proposal.size
            
            # Get risk assessment for this symbol
            risk_assessment = self.risk_assessments.get(
                symbol, self._create_default_risk_assessment(symbol)
            )
            
            # Check if proposal exceeds maximum position size
            if size > risk_assessment.max_position_size:
                await self.reject_trade(proposal, f"Position size {size} exceeds maximum {risk_assessment.max_position_size}")
                return
            
            # Check if adding this position would exceed account risk limit
            current_exposure = sum(pos.get("risk_amount", 0) for pos in self.open_positions.values())
            proposal_risk = self._calculate_proposal_risk(proposal, risk_assessment)
            
            if (current_exposure + proposal_risk) / self.account_balance > self.max_account_risk_percent / 100:
                await self.reject_trade(proposal, "Trade would exceed maximum account risk")
                return
            
            # Check correlation risk (avoid too many correlated positions)
            if self._check_correlation_risk(proposal):
                await self.reject_trade(proposal, "Trade would create excessive correlation risk")
                return
            
            # If we get here, the trade is approved
            # Adjust position size if needed
            adjusted_size = self._adjust_position_size(proposal, risk_assessment)
            if adjusted_size != proposal.size:
                proposal.size = adjusted_size
                self.logger.info(f"Adjusted position size to {adjusted_size}")
            
            # Set appropriate stop loss and take profit levels if not set
            if not proposal.stop_loss or not proposal.take_profit:
                stop_loss, take_profit = self._calculate_exit_levels(proposal, risk_assessment)
                if not proposal.stop_loss:
                    proposal.stop_loss = stop_loss
                if not proposal.take_profit:
                    proposal.take_profit = take_profit
            
            # Approve the trade
            await self.approve_trade(proposal)
            
        except Exception as e:
            self.logger.error(f"Error evaluating trade proposal: {e}")
            if 'proposal' in locals():
                await self.reject_trade(proposal, f"Error in risk evaluation: {str(e)}")
    
    async def approve_trade(self, proposal: TradeProposal):
        """
        Approve a trade proposal
        
        Args:
            proposal: The trade proposal to approve
        """
        # Update the proposal status
        proposal.status = TradeStatus.APPROVED
        
        # Send approval message
        await self.send_message(
            MessageType.TRADE_APPROVAL,
            {
                "proposal_id": proposal.id,
                "approval_time": datetime.utcnow().isoformat(),
                "adjusted_proposal": proposal.__dict__
            }
        )
        
        self.logger.info(f"Approved trade proposal {proposal.id} for {proposal.symbol}")
    
    async def reject_trade(self, proposal: TradeProposal, reason: str):
        """
        Reject a trade proposal
        
        Args:
            proposal: The trade proposal to reject
            reason: Reason for rejection
        """
        # Update the proposal status
        proposal.status = TradeStatus.REJECTED
        
        # Send rejection message
        await self.send_message(
            MessageType.TRADE_REJECTION,
            {
                "proposal_id": proposal.id,
                "rejection_time": datetime.utcnow().isoformat(),
                "reason": reason,
                "proposal": proposal.__dict__
            }
        )
        
        self.logger.info(f"Rejected trade proposal {proposal.id}: {reason}")
    
    async def update_portfolio_with_trade(self, message: Message):
        """
        Update portfolio with a new trade execution
        
        Args:
            message: Message containing trade execution details
        """
        execution_data = message.content.get("execution", {})
        if not execution_data:
            return
        
        # Extract execution details
        execution_id = execution_data.get("execution_id", "unknown")
        proposal_id = execution_data.get("proposal_id", "unknown")
        symbol = execution_data.get("symbol", "")
        direction = execution_data.get("direction", Direction.NEUTRAL)
        size = execution_data.get("executed_size", 0)
        price = execution_data.get("executed_price", 0)
        
        # Calculate risk amount
        risk_assessment = self.risk_assessments.get(
            symbol, self._create_default_risk_assessment(symbol)
        )
        stop_loss_pips = risk_assessment.stop_loss_pips
        pip_value = 0.0001 if not symbol.endswith("JPY") else 0.01
        risk_amount = size * stop_loss_pips * pip_value
        
        # Add to open positions
        self.open_positions[execution_id] = {
            "proposal_id": proposal_id,
            "symbol": symbol,
            "direction": direction,
            "size": size,
            "entry_price": price,
            "risk_amount": risk_amount,
            "entry_time": datetime.utcnow()
        }
        
        self.logger.info(f"Added new position to portfolio: {execution_id} for {symbol}")
    
    async def update_performance_metrics(self, message: Message):
        """
        Update performance metrics with a trade result
        
        Args:
            message: Message containing trade result
        """
        result_data = message.content.get("result", {})
        if not result_data:
            return
        
        # Extract result details
        trade_id = result_data.get("trade_id", "unknown")
        profit_loss = result_data.get("profit_loss", 0)
        
        # Update daily P&L
        self.daily_pnl += profit_loss
        
        # Update account balance
        self.account_balance += profit_loss
        
        # Remove from open positions if closed
        if trade_id in self.open_positions:
            del self.open_positions[trade_id]
        
        self.logger.info(f"Updated performance metrics: P&L {profit_loss}, Balance {self.account_balance}")
    
    async def update_volatility_metrics(self, message: Message):
        """
        Update volatility metrics based on technical signals
        
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
        
        # Update volatility for the symbol (simplified)
        # In a real implementation, this would be more sophisticated
        if "ATR" in signal_data.get("indicator", ""):
            value = signal_data.get("value", 0)
            self.market_volatility[symbol] = value
            
            # Update risk assessment with new volatility
            if symbol in self.risk_assessments:
                self.risk_assessments[symbol].market_volatility = value
    
    async def adjust_risk_for_fundamental_update(self, message: Message):
        """
        Adjust risk assessments based on fundamental data
        
        Args:
            message: Message containing fundamental update
        """
        update_data = message.content.get("update", {})
        if not update_data:
            return
        
        # Extract update details
        impact_currency = update_data.get("impact_currency", [])
        impact_assessment = update_data.get("impact_assessment", Direction.NEUTRAL)
        confidence = update_data.get("confidence", Confidence.LOW)
        
        # Adjust risk for affected symbols
        for symbol in self.risk_assessments:
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1]
            
            # If either currency in the symbol is affected
            if base_currency in impact_currency or quote_currency in impact_currency:
                risk_adjustment = self._calculate_fundamental_risk_adjustment(
                    impact_assessment, confidence, base_currency, quote_currency, impact_currency
                )
                
                # Apply adjustment to risk assessment
                current = self.risk_assessments[symbol]
                
                # Adjust max position size (decrease for higher risk)
                current.max_position_size *= (1 - risk_adjustment)
                
                # Adjust stop loss and take profit (widen for higher risk)
                current.stop_loss_pips *= (1 + risk_adjustment)
                current.take_profit_pips *= (1 + risk_adjustment)
                
                self.logger.info(f"Adjusted risk for {symbol} based on fundamental data: {risk_adjustment}")
    
    async def update_risk_assessments(self):
        """Update risk assessments for all symbols"""
        for symbol in self.risk_assessments:
            # Calculate new risk parameters based on market conditions
            volatility = self.market_volatility.get(symbol, 0.001)
            
            # Update stop loss and take profit levels based on volatility
            self.risk_assessments[symbol].stop_loss_pips = max(10, int(volatility * 10000))
            self.risk_assessments[symbol].take_profit_pips = max(15, int(volatility * 15000))
            
            # Send risk assessment update to other agents
            await self.send_message(
                MessageType.RISK_UPDATE,
                {
                    "symbol": symbol,
                    "assessment": self.risk_assessments[symbol].to_dict(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def check_circuit_breakers(self):
        """Check if circuit breakers should be triggered due to excessive losses"""
        # Check if daily loss exceeds threshold
        if abs(self.daily_pnl) > self.account_balance * (self.max_daily_loss_percent / 100) and self.daily_pnl < 0:
            self.logger.warning(f"Circuit breaker triggered: Daily loss {self.daily_pnl} exceeds threshold")
            
            # Send circuit breaker alert
            await self.send_message(
                MessageType.RISK_ASSESSMENT,
                {
                    "circuit_breaker": True,
                    "reason": "Daily loss threshold exceeded",
                    "daily_pnl": self.daily_pnl,
                    "threshold": self.account_balance * (self.max_daily_loss_percent / 100),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    def _create_default_risk_assessment(self, symbol: str) -> RiskAssessment:
        """
        Create a default risk assessment for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            RiskAssessment: Default risk assessment
        """
        return RiskAssessment(
            symbol=symbol,
            max_position_size=self.account_balance * (self.max_position_size_percent / 100),
            recommended_leverage=3.0,
            stop_loss_pips=20,
            take_profit_pips=30,
            max_daily_loss=self.account_balance * (self.max_daily_loss_percent / 100),
            current_exposure={"total": 0, "positions": []},
            market_volatility=0.001
        )
    
    def _calculate_proposal_risk(self, proposal: TradeProposal, risk_assessment: RiskAssessment) -> float:
        """
        Calculate the risk amount for a trade proposal
        
        Args:
            proposal: Trade proposal
            risk_assessment: Risk assessment for the symbol
            
        Returns:
            float: Risk amount
        """
        # Default to using the risk assessment stop loss if not specified in proposal
        stop_loss_pips = risk_assessment.stop_loss_pips
        
        # But if the proposal has entry and stop loss prices, use those
        if proposal.entry_price and proposal.stop_loss:
            pip_value = 0.0001 if not proposal.symbol.endswith("JPY") else 0.01
            stop_loss_pips = abs(proposal.entry_price - proposal.stop_loss) / pip_value
        
        # Calculate risk amount
        pip_value = 0.0001 if not proposal.symbol.endswith("JPY") else 0.01
        risk_amount = proposal.size * stop_loss_pips * pip_value
        
        return risk_amount
    
    def _check_correlation_risk(self, proposal: TradeProposal) -> bool:
        """
        Check if adding this position would create excessive correlation risk
        
        Args:
            proposal: Trade proposal
            
        Returns:
            bool: True if there is excessive correlation risk
        """
        # Count positions by currency
        currency_exposure = {}
        
        # Count existing positions
        for pos in self.open_positions.values():
            symbol = pos["symbol"]
            base = symbol.split('/')[0]
            quote = symbol.split('/')[1]
            
            if base not in currency_exposure:
                currency_exposure[base] = 0
            if quote not in currency_exposure:
                currency_exposure[quote] = 0
            
            if pos["direction"] == Direction.LONG:
                currency_exposure[base] += pos["size"]
                currency_exposure[quote] -= pos["size"]
            else:  # SHORT
                currency_exposure[base] -= pos["size"]
                currency_exposure[quote] += pos["size"]
        
        # Add proposed position
        symbol = proposal.symbol
        base = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        
        if base not in currency_exposure:
            currency_exposure[base] = 0
        if quote not in currency_exposure:
            currency_exposure[quote] = 0
        
        if proposal.direction == Direction.LONG:
            currency_exposure[base] += proposal.size
            currency_exposure[quote] -= proposal.size
        else:  # SHORT
            currency_exposure[base] -= proposal.size
            currency_exposure[quote] += proposal.size
        
        # Check if any currency exposure exceeds 50% of account balance
        for currency, exposure in currency_exposure.items():
            if abs(exposure) > self.account_balance * 0.5:
                return True
        
        return False
    
    def _adjust_position_size(self, proposal: TradeProposal, risk_assessment: RiskAssessment) -> float:
        """
        Adjust position size to fit within risk parameters
        
        Args:
            proposal: Trade proposal
            risk_assessment: Risk assessment for the symbol
            
        Returns:
            float: Adjusted position size
        """
        # Calculate risk per unit size
        pip_value = 0.0001 if not proposal.symbol.endswith("JPY") else 0.01
        risk_per_unit = risk_assessment.stop_loss_pips * pip_value
        
        # Calculate maximum size based on account risk
        max_risk_amount = self.account_balance * (self.max_account_risk_percent / 100)
        max_size = max_risk_amount / risk_per_unit
        
        # Ensure size doesn't exceed risk assessment max
        max_size = min(max_size, risk_assessment.max_position_size)
        
        # Return the smaller of proposed size and maximum allowed size
        return min(proposal.size, max_size)
    
    def _calculate_exit_levels(self, proposal: TradeProposal, risk_assessment: RiskAssessment) -> tuple:
        """
        Calculate appropriate stop loss and take profit levels
        
        Args:
            proposal: Trade proposal
            risk_assessment: Risk assessment for the symbol
            
        Returns:
            tuple: (stop_loss_price, take_profit_price)
        """
        if not proposal.entry_price:
            return None, None
            
        pip_value = 0.0001 if not proposal.symbol.endswith("JPY") else 0.01
        
        if proposal.direction == Direction.LONG:
            stop_loss = proposal.entry_price - (risk_assessment.stop_loss_pips * pip_value)
            take_profit = proposal.entry_price + (risk_assessment.take_profit_pips * pip_value)
        else:  # SHORT
            stop_loss = proposal.entry_price + (risk_assessment.stop_loss_pips * pip_value)
            take_profit = proposal.entry_price - (risk_assessment.take_profit_pips * pip_value)
        
        return stop_loss, take_profit
    
    def _calculate_fundamental_risk_adjustment(self, impact: Direction, 
                                             confidence: Confidence, 
                                             base_currency: str, 
                                             quote_currency: str,
                                             impact_currency: List[str]) -> float:
        """
        Calculate risk adjustment factor based on fundamental data
        
        Args:
            impact: Impact direction
            confidence: Confidence level
            base_currency: Base currency of the symbol
            quote_currency: Quote currency of the symbol
            impact_currency: List of currencies impacted
            
        Returns:
            float: Risk adjustment factor (0-0.5)
        """
        # Convert confidence to numeric value
        confidence_value = {
            Confidence.VERY_LOW: 0.1,
            Confidence.LOW: 0.2,
            Confidence.MEDIUM: 0.3,
            Confidence.HIGH: 0.4,
            Confidence.VERY_HIGH: 0.5
        }.get(confidence, 0.1)
        
        # If both currencies are affected, double the adjustment
        factor = 1.0
        if base_currency in impact_currency and quote_currency in impact_currency:
            factor = 2.0
        
        # Calculate adjustment (0-0.5 range)
        adjustment = confidence_value * factor * 0.5
        
        return min(adjustment, 0.5)  # Cap at 0.5 (50% adjustment)
