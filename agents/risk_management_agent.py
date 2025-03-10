
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from system.agent import Agent
from system.core import Message, MessageType, TradeProposal, TradeStatus, RiskAssessment

class RiskManagementAgent(Agent):
    """
    Agent responsible for evaluating trade proposals against risk parameters, 
    ensuring portfolio-level risk control, and preventing excessive exposure.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.update_interval = config.get("update_interval_seconds", 60)
        
        # Risk parameters from configuration
        self.max_account_risk_percent = config.get("max_account_risk_percent", 2.0)
        self.max_position_size_percent = config.get("max_position_size_percent", 5.0)
        self.max_daily_loss_percent = config.get("max_daily_loss_percent", 5.0)
        
        # Internal state
        self.account_balance = 10000.0  # Placeholder for account balance
        self.open_positions = {}        # Current open positions
        self.daily_pnl = 0.0            # Daily profit/loss tracking
        self.market_volatility = {}     # Volatility data by symbol
        
    async def setup(self):
        """Initialize the agent and subscribe to relevant message types"""
        await self.subscribe_to([
            MessageType.TRADE_PROPOSAL,
            MessageType.TRADE_RESULT,
            MessageType.SYSTEM_STATUS,
            MessageType.MARKET_DATA
        ])
        self.logger.info("Risk Management Agent initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Risk Management Agent shutting down")
    
    async def process_cycle(self):
        """Main processing loop - periodically reassess risk and positions"""
        await self.update_risk_metrics()
        await asyncio.sleep(self.update_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TRADE_PROPOSAL:
            await self.evaluate_trade_proposal(message)
        
        elif message.type == MessageType.TRADE_RESULT:
            await self.process_trade_result(message)
        
        elif message.type == MessageType.MARKET_DATA:
            self.update_market_data(message.content)
    
    async def evaluate_trade_proposal(self, message: Message):
        """Evaluate a trade proposal against risk parameters"""
        proposal_dict = message.content.get("proposal", {})
        proposal_id = proposal_dict.get("id")
        
        try:
            # Create a TradeProposal object from the message content
            proposal = TradeProposal(
                id=proposal_id,
                symbol=proposal_dict.get("symbol"),
                direction=proposal_dict.get("direction"),
                size=proposal_dict.get("size"),
                entry_price=proposal_dict.get("entry_price"),
                stop_loss=proposal_dict.get("stop_loss"),
                take_profit=proposal_dict.get("take_profit"),
                time_limit_seconds=proposal_dict.get("time_limit_seconds"),
                strategy_name=proposal_dict.get("strategy_name"),
                technical_confidence=proposal_dict.get("technical_confidence"),
                fundamental_alignment=proposal_dict.get("fundamental_alignment"),
                risk_score=proposal_dict.get("risk_score"),
                status=TradeStatus.PROPOSED
            )
            
            # Check if we're within daily loss limit
            if self.daily_pnl < -self.max_daily_loss_percent * self.account_balance / 100.0:
                self.logger.warning(f"Daily loss limit reached, rejecting proposal {proposal_id}")
                await self.reject_proposal(proposal_id, "Daily loss limit reached")
                return
            
            # Calculate potential loss if stop-loss is hit
            potential_loss = self.calculate_potential_loss(proposal)
            
            # Check if this loss exceeds account risk limit
            account_risk_percent = (potential_loss / self.account_balance) * 100.0
            if account_risk_percent > self.max_account_risk_percent:
                self.logger.warning(f"Proposal {proposal_id} exceeds account risk limit")
                
                # Adjust size to meet risk limit and approve if still valid
                adjusted_size = proposal.size * (self.max_account_risk_percent / account_risk_percent)
                if adjusted_size >= 0.01:  # Minimum viable position size
                    proposal.size = adjusted_size
                    self.logger.info(f"Adjusted size for proposal {proposal_id} to {adjusted_size}")
                    await self.approve_proposal(proposal)
                else:
                    await self.reject_proposal(proposal_id, "Position size too small after risk adjustment")
                return
            
            # Check total exposure to this symbol
            symbol_exposure = self.calculate_symbol_exposure(proposal.symbol)
            if symbol_exposure + proposal.size > self.max_position_size_percent * self.account_balance / 100.0:
                self.logger.warning(f"Proposal {proposal_id} would exceed maximum exposure for {proposal.symbol}")
                await self.reject_proposal(proposal_id, f"Maximum exposure for {proposal.symbol} reached")
                return
            
            # Check current market volatility
            volatility = self.market_volatility.get(proposal.symbol, 1.0)
            if volatility > 2.0:  # Arbitrary threshold for high volatility
                self.logger.warning(f"High volatility for {proposal.symbol}, adjusting risk")
                # Reduce position size in high volatility
                proposal.size = proposal.size * 0.5
            
            # All checks passed, approve the proposal
            await self.approve_proposal(proposal)
            
        except Exception as e:
            self.logger.error(f"Error evaluating trade proposal {proposal_id}: {e}")
            await self.reject_proposal(proposal_id, f"Error in risk evaluation: {str(e)}")
    
    async def approve_proposal(self, proposal):
        """Approve a trade proposal and send it to the execution agent"""
        proposal.status = TradeStatus.APPROVED
        
        # Create risk assessment
        risk_assessment = RiskAssessment(
            symbol=proposal.symbol,
            max_position_size=proposal.size,
            recommended_leverage=1.0,  # Default leverage
            stop_loss_pips=abs(proposal.entry_price - proposal.stop_loss) * 10000 if proposal.entry_price else 0,
            take_profit_pips=abs(proposal.take_profit - proposal.entry_price) * 10000 if proposal.entry_price else 0,
            max_daily_loss=self.max_daily_loss_percent * self.account_balance / 100.0,
            current_exposure=self.get_current_exposure(),
            market_volatility=self.market_volatility.get(proposal.symbol, 1.0)
        )
        
        await self.send_message(
            MessageType.RISK_ASSESSMENT,
            {
                "proposal_id": proposal.id,
                "assessment": risk_assessment.__dict__,
                "approved": True,
                "adjusted_proposal": proposal.__dict__,
                "timestamp": datetime.utcnow().isoformat()
            },
            recipients=["trade_execution"]
        )
        
        self.logger.info(f"Approved trade proposal {proposal.id} for {proposal.symbol}")
    
    async def reject_proposal(self, proposal_id, reason):
        """Reject a trade proposal"""
        await self.send_message(
            MessageType.RISK_ASSESSMENT,
            {
                "proposal_id": proposal_id,
                "approved": False,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            },
            recipients=["strategy_optimization", "trade_execution"]
        )
        self.logger.info(f"Rejected trade proposal {proposal_id}: {reason}")
    
    async def process_trade_result(self, message: Message):
        """Process the result of a trade execution"""
        result = message.content
        
        # Update our internal state based on the trade result
        trade_pnl = result.get("pnl", 0.0)
        self.daily_pnl += trade_pnl
        
        # Update open positions
        execution = result.get("execution", {})
        symbol = execution.get("symbol")
        
        if execution.get("status") == TradeStatus.EXECUTED.value:
            # Add to open positions
            if symbol not in self.open_positions:
                self.open_positions[symbol] = 0
            self.open_positions[symbol] += execution.get("executed_size", 0)
        
        elif execution.get("status") in [TradeStatus.CANCELED.value, TradeStatus.EXPIRED.value]:
            # Position was closed
            if symbol in self.open_positions:
                self.open_positions[symbol] -= execution.get("executed_size", 0)
                if self.open_positions[symbol] <= 0:
                    del self.open_positions[symbol]
    
    async def update_risk_metrics(self):
        """Update risk metrics based on current market conditions and positions"""
        # Calculate current exposure for all symbols
        total_exposure = sum(self.open_positions.values())
        account_exposure_percent = (total_exposure / self.account_balance) * 100.0
        
        self.logger.info(f"Current account exposure: {account_exposure_percent:.2f}%")
        self.logger.info(f"Daily P&L: {self.daily_pnl:.2f}")
        
        # Check if we need to reduce exposure
        if account_exposure_percent > self.max_account_risk_percent * 1.5:  # Over 150% of limit
            self.logger.warning("Total exposure exceeds safe limits, considering position reduction")
            # In a real implementation, might send signals to reduce positions
    
    def update_market_data(self, data):
        """Update market data for risk calculations"""
        symbol = data.get("symbol")
        if not symbol:
            return
            
        # Update volatility calculation
        # In a real implementation, this would be a more sophisticated calculation
        # For this example, we'll use a very simple placeholder
        if "high" in data and "low" in data:
            daily_range = data["high"] - data["low"]
            avg_price = (data["high"] + data["low"]) / 2
            volatility = daily_range / avg_price
            self.market_volatility[symbol] = volatility
    
    def calculate_potential_loss(self, proposal):
        """Calculate potential loss if stop-loss is hit"""
        if not proposal.entry_price or not proposal.stop_loss:
            # If market order, use placeholder risk calculation
            return proposal.size * 0.01  # Assume 1% risk
            
        price_distance = abs(proposal.entry_price - proposal.stop_loss)
        return proposal.size * price_distance
    
    def calculate_symbol_exposure(self, symbol):
        """Calculate current exposure to a specific symbol"""
        return self.open_positions.get(symbol, 0.0)
    
    def get_current_exposure(self):
        """Get the current exposure for all symbols"""
        return self.open_positions.copy()
