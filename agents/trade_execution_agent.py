
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from system.agent import Agent
from system.core import Message, MessageType, TradeStatus, TradeExecution, TradeProposal

class TradeExecutionAgent(Agent):
    """
    Agent responsible for managing order submission, monitoring open positions,
    and handling trade lifecycle events.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.check_interval = config.get("check_interval_seconds", 1)
        self.gateway_type = config.get("gateway_type", "simulation")
        self.slippage_model = config.get("slippage_model", "fixed")
        self.fixed_slippage_pips = config.get("fixed_slippage_pips", 1.0)
        
        # Internal state
        self.pending_proposals = {}  # Trade proposals pending execution
        self.open_trades = {}        # Currently open trades
        self.current_prices = {}     # Latest market prices
        
    async def setup(self):
        """Initialize the agent and subscribe to relevant message types"""
        await self.subscribe_to([
            MessageType.RISK_ASSESSMENT,
            MessageType.MARKET_DATA,
            MessageType.SYSTEM_STATUS
        ])
        
        self.logger.info(f"Trade Execution Agent initialized with {self.gateway_type} gateway")
        
        # Set up trade gateway
        await self.setup_trade_gateway()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.close_trade_gateway()
        self.logger.info("Trade Execution Agent shutting down")
    
    async def process_cycle(self):
        """Main processing loop - check pending orders and monitor open positions"""
        await self.check_pending_proposals()
        await self.monitor_open_positions()
        await asyncio.sleep(self.check_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.RISK_ASSESSMENT:
            await self.process_risk_assessment(message)
        
        elif message.type == MessageType.MARKET_DATA:
            self.update_market_data(message.content)
    
    async def setup_trade_gateway(self):
        """Set up the trade execution gateway based on configuration"""
        # In a real implementation, this would connect to a broker or exchange
        # For this example, we'll just set up a simulation gateway
        
        if self.gateway_type == "simulation":
            self.logger.info("Using simulation gateway - no real trades will be executed")
            # No actual connection needed for simulation
        else:
            # Here would be code to connect to a real broker API
            self.logger.info(f"Connecting to {self.gateway_type} gateway")
            # Placeholder for connection logic
    
    async def close_trade_gateway(self):
        """Close the trade gateway connection"""
        if self.gateway_type != "simulation":
            # Close connection to broker API
            self.logger.info("Closing gateway connection")
            # Placeholder for disconnection logic
    
    async def process_risk_assessment(self, message: Message):
        """Process a risk assessment message"""
        proposal_id = message.content.get("proposal_id")
        approved = message.content.get("approved", False)
        
        if not approved:
            # Proposal was rejected, log and move on
            reason = message.content.get("reason", "Unknown reason")
            self.logger.info(f"Trade proposal {proposal_id} rejected by risk management: {reason}")
            return
        
        # Get the adjusted proposal from risk management
        adjusted_proposal_dict = message.content.get("adjusted_proposal", {})
        
        # Create a TradeProposal object
        try:
            proposal = TradeProposal(
                id=adjusted_proposal_dict.get("id"),
                symbol=adjusted_proposal_dict.get("symbol"),
                direction=adjusted_proposal_dict.get("direction"),
                size=adjusted_proposal_dict.get("size"),
                entry_price=adjusted_proposal_dict.get("entry_price"),
                stop_loss=adjusted_proposal_dict.get("stop_loss"),
                take_profit=adjusted_proposal_dict.get("take_profit"),
                time_limit_seconds=adjusted_proposal_dict.get("time_limit_seconds"),
                strategy_name=adjusted_proposal_dict.get("strategy_name"),
                technical_confidence=adjusted_proposal_dict.get("technical_confidence"),
                fundamental_alignment=adjusted_proposal_dict.get("fundamental_alignment"),
                risk_score=adjusted_proposal_dict.get("risk_score"),
                status=TradeStatus.APPROVED
            )
            
            # Store proposal for execution
            self.pending_proposals[proposal_id] = {
                "proposal": proposal,
                "timestamp": datetime.utcnow(),
                "assessment": message.content.get("assessment", {})
            }
            
            self.logger.info(f"Received approved trade proposal {proposal_id} for {proposal.symbol}")
            
            # Check if we can execute immediately
            await self.attempt_execution(proposal_id)
            
        except Exception as e:
            self.logger.error(f"Error processing approved proposal {proposal_id}: {e}")
    
    async def check_pending_proposals(self):
        """Check all pending proposals for execution or expiry"""
        now = datetime.utcnow()
        expired_proposals = []
        
        for proposal_id, data in self.pending_proposals.items():
            proposal = data["proposal"]
            timestamp = data["timestamp"]
            
            # Check if proposal has expired
            age_seconds = (now - timestamp).total_seconds()
            if age_seconds > proposal.time_limit_seconds:
                self.logger.info(f"Trade proposal {proposal_id} expired after {age_seconds:.0f} seconds")
                expired_proposals.append(proposal_id)
                await self.send_execution_result(proposal, TradeStatus.EXPIRED)
                continue
            
            # Try to execute proposal
            await self.attempt_execution(proposal_id)
        
        # Clean up expired proposals
        for proposal_id in expired_proposals:
            if proposal_id in self.pending_proposals:
                del self.pending_proposals[proposal_id]
    
    async def attempt_execution(self, proposal_id):
        """Attempt to execute a trade proposal"""
        if proposal_id not in self.pending_proposals:
            return
            
        data = self.pending_proposals[proposal_id]
        proposal = data["proposal"]
        
        # Check if we have current price for this symbol
        symbol = proposal.symbol
        if symbol not in self.current_prices:
            self.logger.warning(f"Cannot execute proposal {proposal_id} - no current price for {symbol}")
            return
        
        # Get current bid/ask prices
        bid = self.current_prices[symbol].get("bid")
        ask = self.current_prices[symbol].get("ask")
        
        if bid is None or ask is None:
            self.logger.warning(f"Cannot execute proposal {proposal_id} - incomplete price data for {symbol}")
            return
        
        # Determine execution price based on direction
        execution_price = None
        if proposal.direction.value == "long":
            execution_price = ask
        elif proposal.direction.value == "short":
            execution_price = bid
        
        if execution_price is None:
            self.logger.warning(f"Cannot determine execution price for proposal {proposal_id}")
            return
        
        # Apply slippage model
        execution_price = self.apply_slippage(execution_price, proposal.direction.value)
        
        # Check if market moved unfavorably beyond tolerance
        if proposal.entry_price:
            # Calculate price deviation as percentage
            deviation = abs(execution_price - proposal.entry_price) / proposal.entry_price
            
            # If price moved more than 0.2% unfavorably, don't execute
            if deviation > 0.002:
                if (proposal.direction.value == "long" and execution_price > proposal.entry_price) or \
                   (proposal.direction.value == "short" and execution_price < proposal.entry_price):
                    self.logger.warning(f"Market moved unfavorably for {proposal_id} - delaying execution")
                    return
        
        # Execute the trade
        execution_id = f"exec_{proposal_id}_{int(datetime.utcnow().timestamp())}"
        
        # In simulation mode, we just pretend to execute
        execution_result = await self.execute_trade(
            proposal.symbol,
            proposal.direction.value,
            proposal.size,
            execution_price,
            proposal.stop_loss,
            proposal.take_profit,
            execution_id,
            proposal_id
        )
        
        if execution_result["success"]:
            # Create execution record
            execution = TradeExecution(
                proposal_id=proposal_id,
                execution_id=execution_id,
                symbol=proposal.symbol,
                direction=proposal.direction,
                executed_size=proposal.size,
                executed_price=execution_price,
                execution_time=datetime.utcnow(),
                status=TradeStatus.EXECUTED,
                metadata={
                    "stop_loss": proposal.stop_loss,
                    "take_profit": proposal.take_profit,
                    "strategy": proposal.strategy_name
                }
            )
            
            # Store in open trades
            self.open_trades[execution_id] = {
                "execution": execution,
                "proposal": proposal
            }
            
            # Send execution result
            await self.send_execution_result(proposal, TradeStatus.EXECUTED, execution)
            
            # Remove from pending proposals
            del self.pending_proposals[proposal_id]
            
            self.logger.info(f"Executed trade {execution_id} for symbol {proposal.symbol} at price {execution_price}")
        else:
            self.logger.warning(f"Failed to execute trade for proposal {proposal_id}: {execution_result['error']}")
    
    async def monitor_open_positions(self):
        """Monitor all open positions for stop loss, take profit, or other exit conditions"""
        # Skip if no open trades or no market data
        if not self.open_trades or not self.current_prices:
            return
            
        trades_to_close = []
        
        for execution_id, trade_data in self.open_trades.items():
            execution = trade_data["execution"]
            proposal = trade_data["proposal"]
            symbol = execution.symbol
            
            # Check if we have current price for this symbol
            if symbol not in self.current_prices:
                continue
                
            # Get current bid/ask prices
            bid = self.current_prices[symbol].get("bid")
            ask = self.current_prices[symbol].get("ask")
            
            if bid is None or ask is None:
                continue
            
            # Determine the price to check against based on direction
            current_price = None
            if execution.direction.value == "long":
                current_price = bid  # For long positions, we check against bid for exit
            elif execution.direction.value == "short":
                current_price = ask  # For short positions, we check against ask for exit
            
            if current_price is None:
                continue
            
            # Check stop loss hit
            stop_loss_hit = False
            if proposal.stop_loss:
                if execution.direction.value == "long" and current_price <= proposal.stop_loss:
                    stop_loss_hit = True
                elif execution.direction.value == "short" and current_price >= proposal.stop_loss:
                    stop_loss_hit = True
            
            # Check take profit hit
            take_profit_hit = False
            if proposal.take_profit:
                if execution.direction.value == "long" and current_price >= proposal.take_profit:
                    take_profit_hit = True
                elif execution.direction.value == "short" and current_price <= proposal.take_profit:
                    take_profit_hit = True
            
            # If either hit, close the position
            if stop_loss_hit or take_profit_hit:
                reason = "stop_loss" if stop_loss_hit else "take_profit"
                self.logger.info(f"Trade {execution_id} {reason} triggered at price {current_price}")
                
                # Close the position
                close_result = await self.close_trade(
                    execution_id,
                    current_price,
                    reason
                )
                
                if close_result["success"]:
                    trades_to_close.append(execution_id)
                    
                    # Calculate P&L
                    pnl = self.calculate_pnl(execution, current_price)
                    
                    # Send trade result message
                    await self.send_message(
                        MessageType.TRADE_RESULT,
                        {
                            "execution": execution.__dict__,
                            "exit_price": current_price,
                            "exit_reason": reason,
                            "exit_time": datetime.utcnow().isoformat(),
                            "pnl": pnl
                        }
                    )
                    
                    self.logger.info(f"Closed trade {execution_id} with P&L: {pnl}")
        
        # Clean up closed trades
        for execution_id in trades_to_close:
            if execution_id in self.open_trades:
                del self.open_trades[execution_id]
    
    async def execute_trade(self, symbol, direction, size, price, stop_loss, take_profit, execution_id, proposal_id):
        """Execute a trade through the gateway"""
        # In a real implementation, this would send the order to the broker
        # For this example, we'll simulate successful execution
        
        # Simulation mode always succeeds
        if self.gateway_type == "simulation":
            return {
                "success": True,
                "order_id": execution_id
            }
        
        # For other gateway types, this would contain the actual broker API calls
        # and handle various error conditions
        
        # Placeholder for real execution code
        return {
            "success": False,
            "error": "Not implemented"
        }
    
    async def close_trade(self, execution_id, price, reason):
        """Close an open trade"""
        # In a real implementation, this would send the close order to the broker
        # For this example, we'll simulate successful closing
        
        if self.gateway_type == "simulation":
            return {
                "success": True
            }
        
        # Placeholder for real trade closing code
        return {
            "success": False,
            "error": "Not implemented"
        }
    
    async def send_execution_result(self, proposal, status, execution=None):
        """Send the result of a trade execution attempt"""
        content = {
            "proposal_id": proposal.id,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if execution:
            content["execution"] = execution.__dict__
        
        await self.send_message(
            MessageType.TRADE_EXECUTION,
            content
        )
    
    def update_market_data(self, data):
        """Update current market price data"""
        symbol = data.get("symbol")
        if not symbol:
            return
            
        # Store only the data we need
        self.current_prices[symbol] = {
            "timestamp": data.get("timestamp"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "last": data.get("last")
        }
    
    def apply_slippage(self, price, direction):
        """Apply slippage model to price"""
        if self.slippage_model == "fixed":
            # Apply fixed pip slippage
            slippage_amount = self.fixed_slippage_pips / 10000.0
            
            if direction == "long":
                return price + slippage_amount  # Long positions get worse prices (higher)
            else:
                return price - slippage_amount  # Short positions get worse prices (lower)
        
        # Other slippage models could be implemented here
        return price
    
    def calculate_pnl(self, execution, exit_price):
        """Calculate profit/loss for a trade"""
        entry_price = execution.executed_price
        size = execution.executed_size
        direction = execution.direction.value
        
        if direction == "long":
            return size * (exit_price - entry_price)
        else:  # short
            return size * (entry_price - exit_price)
