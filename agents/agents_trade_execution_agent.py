import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, Confidence,
    TradeProposal, TradeExecution
)

class TradeExecutionAgent(Agent):
    def __init__(self, agent_id: str, message_broker, config):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.pending_trades = {}  # proposal_id -> trade proposal
        self.active_trades = {}  # execution_id -> trade details
        self.market_data = {}  # symbol -> latest market data
        self.execution_gateway = None  # Trading gateway interface
        self.check_interval = config.get("check_interval_seconds", 1)  # 1 second
        self.slippage_model = config.get("slippage_model", "fixed")  # fixed or proportional
        self.fixed_slippage_pips = config.get("fixed_slippage_pips", 1.0)  # 1 pip
        self.proportional_slippage = config.get("proportional_slippage", 0.0001)  # 0.01%
        
    async def setup(self):
        """Set up the agent when starting"""
        await self.subscribe_to([
            MessageType.RISK_ASSESSMENT,
            MessageType.SYSTEM_STATUS
        ])
        await self.initialize_execution_gateway()
        self.logger.info("Trade Execution Agent setup complete.")
    
    async def cleanup(self):
        """Clean up when agent is stopping"""
        # Close any pending trades
        for proposal_id, proposal in list(self.pending_trades.items()):
            await self.cancel_trade(proposal_id, "Agent shutting down")
        
        # Disconnect from trading gateway
        if self.execution_gateway:
            await self.execution_gateway.disconnect()
        
        self.logger.info("Trade Execution Agent cleaned up")
    
    async def process_cycle(self):
        """Process a single cycle of the agent's main loop"""
        # Check pending trades for expiry or execution
        await self.process_pending_trades()
        
        # Check active trades for stop loss, take profit, or trailing stop adjustment
        await self.monitor_active_trades()
        
        # Sleep to maintain the desired update frequency
        await asyncio.sleep(self.check_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.RISK_ASSESSMENT:
            # Process risk assessment and execute trades if approved
            proposal = message.content.get("proposal")
            approved = message.content.get("approved", False)
            
            if proposal and approved:
                await self.handle_approved_trade(proposal)
        
        elif message.type == MessageType.SYSTEM_STATUS:
            # Check for risk alerts or system status changes
            if message.content.get("alert") == "RISK_ALERT":
                # If there's a serious risk alert, cancel pending trades
                risk_message = message.content.get("message", "")
                if "threshold breached" in risk_message:
                    await self.cancel_all_pending_trades("Risk threshold breached")
    
    async def initialize_execution_gateway(self):
        """Initialize connection to trading gateway"""
        # In a real system, this would connect to an actual trading API
        # For this prototype, we'll use a simulated gateway
        gateway_type = self.config.get("gateway_type", "simulation")
        
        if gateway_type == "simulation":
            self.execution_gateway = SimulatedTradingGateway(
                slippage_model=self.slippage_model,
                fixed_slippage_pips=self.fixed_slippage_pips,
                proportional_slippage=self.proportional_slippage,
                logger=self.logger
            )
        else:
            # This would initialize a real trading gateway connection
            # self.execution_gateway = RealTradingGateway(...)
            self.logger.warning(f"Gateway type {gateway_type} not implemented, using simulation")
            self.execution_gateway = SimulatedTradingGateway(
                slippage_model=self.slippage_model,
                fixed_slippage_pips=self.fixed_slippage_pips,
                proportional_slippage=self.proportional_slippage,
                logger=self.logger
            )
        
        await self.execution_gateway.connect()
        self.logger.info(f"Connected to {gateway_type} trading gateway")
    
    async def handle_approved_trade(self, proposal):
        """Process an approved trade proposal"""
        proposal_id = proposal.get("id")
        if not proposal_id:
            return
        
        # Store in pending trades
        self.pending_trades[proposal_id] = proposal
        
        # Set expiry time
        time_limit = proposal.get("time_limit_seconds", 3600)  # Default 1 hour
        expiry_time = datetime.utcnow() + timedelta(seconds=time_limit)
        self.pending_trades[proposal_id]["expiry_time"] = expiry_time
        
        self.logger.info(f"Received approved trade proposal {proposal_id} for {proposal.get('symbol')}")
        
        # Attempt immediate execution
        await self.execute_trade(proposal_id)
    
    async def execute_trade(self, proposal_id):
        """Execute a trade based on a proposal"""
        proposal = self.pending_trades.get(proposal_id)
        if not proposal:
            self.logger.warning(f"Trade proposal {proposal_id} not found")
            return
        
        symbol = proposal.get("symbol")
        direction = proposal.get("direction")
        size = proposal.get("size")
        entry_price = proposal.get("entry_price")  # None for market order
        
        # Request execution from gateway
        execution_result = await self.execution_gateway.execute_trade(
            symbol=symbol,
            direction=direction,
            size=size,
            order_type="MARKET" if entry_price is None else "LIMIT",
            limit_price=entry_price
        )
        
        if execution_result.get("success"):
            # Create execution record
            execution_id = str(uuid.uuid4())
            execution = TradeExecution(
                proposal_id=proposal_id,
                execution_id=execution_id,
                symbol=symbol,
                direction=Direction[direction] if isinstance(direction, str) else direction,
                executed_size=execution_result.get("executed_size"),
                executed_price=execution_result.get("executed_price"),
                execution_time=datetime.utcnow(),
                status=TradeStatus.EXECUTED,
                metadata={
                    "strategy_name": proposal.get("strategy_name"),
                    "stop_loss": proposal.get("stop_loss"),
                    "take_profit": proposal.get("take_profit")
                }
            )
            
            # Record the active trade
            self.active_trades[execution_id] = {
                "execution": execution.__dict__,
                "stop_loss_price": self.calculate_stop_price(execution, proposal),
                "take_profit_price": self.calculate_take_profit_price(execution, proposal)
            }
            
            # Remove from pending trades
            del self.pending_trades[proposal_id]
            
            # Broadcast execution
            await self.send_message(
                MessageType.TRADE_EXECUTION,
                {"execution": execution.__dict__}
            )
            
            self.logger.info(f"Executed trade for {symbol}: {direction} {execution.executed_size} @ {execution.executed_price}")
        else:
            # Handle execution failure
            error = execution_result.get("error", "Unknown error")
            self.logger.error(f"Trade execution failed: {error}")
            
            # Retry later if it's a temporary error
            if "temporary" in error.lower():
                self.logger.info(f"Will retry execution for {proposal_id} later")
            else:
                # Cancel the trade for permanent errors
                await self.cancel_trade(proposal_id, f"Execution failed: {error}")
    
    async def cancel_trade(self, proposal_id, reason):
        """Cancel a pending trade"""
        if proposal_id in self.pending_trades:
            proposal = self.pending_trades[proposal_id]
            symbol = proposal.get("symbol")
            
            # Create execution with canceled status
            execution = TradeExecution(
                proposal_id=proposal_id,
                execution_id=str(uuid.uuid4()),
                symbol=symbol,
                direction=Direction[proposal.get("direction")] if isinstance(proposal.get("direction"), str) else proposal.get("direction"),
                executed_size=0,
                executed_price=0,
                execution_time=datetime.utcnow(),
                status=TradeStatus.CANCELED,
                metadata={"reason": reason}
            )
            
            # Remove from pending
            del self.pending_trades[proposal_id]
            
            # Broadcast cancellation
            await self.send_message(
                MessageType.TRADE_EXECUTION,
                {"execution": execution.__dict__}
            )
            
            self.logger.info(f"Canceled trade {proposal_id} for {symbol}: {reason}")
    
    async def cancel_all_pending_trades(self, reason):
        """Cancel all pending trades"""
        proposal_ids = list(self.pending_trades.keys())
        for proposal_id in proposal_ids:
            await self.cancel_trade(proposal_id, reason)
        
        self.logger.warning(f"Canceled all pending trades: {reason}")
    
    async def process_pending_trades(self):
        """Process pending trades for execution or expiry"""
        now = datetime.utcnow()
        
        for proposal_id, proposal in list(self.pending_trades.items()):
            # Check for expiry
            expiry_time = proposal.get("expiry_time")
            if expiry_time and now > expiry_time:
                await self.cancel_trade(proposal_id, "Trade proposal expired")
                continue
            
            # Attempt execution for market orders or limit orders if the price is right
            entry_price = proposal.get("entry_price")
            if entry_price is None:  # Market order
                await self.execute_trade(proposal_id)
            else:
                # For limit orders, check if the market price has reached the limit price
                symbol = proposal.get("symbol")
                direction = proposal.get("direction")
                
                if symbol in self.market_data:
                    current_bid = self.market_data[symbol].get("bid", 0)
                    current_ask = self.market_data[symbol].get("ask", 0)
                    
                    # Check if limit price is reached
                    if (direction == Direction.LONG and current_ask <= entry_price) or \
                       (direction == Direction.SHORT and current_bid >= entry_price):
                        await self.execute_trade(proposal_id)
    
    async def monitor_active_trades(self):
        """Monitor active trades for stop loss, take profit, or trailing stop adjustment"""
        # Update market data first
        await self.update_market_data()
        
        # Check each active trade
        for execution_id, trade in list(self.active_trades.items()):
            execution = trade.get("execution", {})
            symbol = execution.get("symbol")
            
            if symbol not in self.market_data:
                continue
            
            current_bid = self.market_data[symbol].get("bid", 0)
            current_ask = self.market_data[symbol].get("ask", 0)
            direction = execution.get("direction")
            
            # Determine current price based on direction (for calculating P/L)
            current_price = current_bid if direction == Direction.LONG.value else current_ask
            entry_price = execution.get("executed_price", 0)
            
            # Calculate unrealized P/L
            direction_mult = 1 if direction == Direction.LONG.value else -1
            pips_factor = 10000  # Assuming 4 decimal places for forex
            unrealized_pips = (current_price - entry_price) * direction_mult * pips_factor
            
            # Check stop loss
            stop_loss_price = trade.get("stop_loss_price")
            if stop_loss_price and ((direction == Direction.LONG.value and current_bid <= stop_loss_price) or 
                                   (direction == Direction.SHORT.value and current_ask >= stop_loss_price)):
                await self.close_trade(execution_id, "Stop loss triggered", current_price, unrealized_pips)
                continue
            
            # Check take profit
            take_profit_price = trade.get("take_profit_price")
            if take_profit_price and ((direction == Direction.LONG.value and current_bid >= take_profit_price) or 
                                     (direction == Direction.SHORT.value and current_ask <= take_profit_price)):
                await self.close_trade(execution_id, "Take profit reached", current_price, unrealized_pips)
                continue
            
            # Update trailing stop if applicable
            if "trailing_stop" in trade and trade["trailing_stop"]["enabled"]:
                await self.update_trailing_stop(execution_id, trade, current_price, unrealized_pips)
    
    async def close_trade(self, execution_id, reason, close_price, profit_pips):
        """Close an active trade"""
        if execution_id not in self.active_trades:
            return
        
        trade = self.active_trades[execution_id]
        execution = trade.get("execution", {})
        symbol = execution.get("symbol")
        direction = execution.get("direction")
        size = execution.get("executed_size")
        
        # Calculate actual profit
        position_size_usd = size / 10000  # Convert from standard lots to USD value
        pip_value = position_size_usd * 10  # Assuming $10 per pip for each $100,000
        profit_amount = profit_pips * pip_value / 10000  # Convert to dollar amount
        
        # Request trade closure from gateway
        close_result = await self.execution_gateway.close_trade(
            trade_id=execution_id,
            symbol=symbol,
            direction=Direction.SHORT.value if direction == Direction.LONG.value else Direction.LONG.value,
            size=size
        )
        
        if close_result.get("success"):
            # Create trade result
            trade_result = {
                "execution_id": execution_id,
                "proposal_id": execution.get("proposal_id"),
                "symbol": symbol,
                "direction": direction,
                "open_price": execution.get("executed_price"),
                "close_price": close_price,
                "size": size,
                "profit_pips": profit_pips,
                "profit": profit_amount,
                "open_time": execution.get("execution_time"),
                "close_time": datetime.utcnow().isoformat(),
                "reason": reason,
                "strategy_name": execution.get("metadata", {}).get("strategy_name"),
                "successful": profit_pips > 0,
                "position_closed": True
            }
            
            # Remove from active trades
            del self.active_trades[execution_id]
            
            # Broadcast trade result
            await self.send_message(
                MessageType.TRADE_RESULT,
                trade_result
            )
            
            self.logger.info(f"Closed trade {execution_id} for {symbol}: {reason}, profit: {profit_pips:.1f} pips (${profit_amount:.2f})")
        else:
            # Handle closure failure
            error = close_result.get("error", "Unknown error")
            self.logger.error(f"Trade closure failed: {error}")
    
    async def update_trailing_stop(self, execution_id, trade, current_price, unrealized_pips):
        """Update trailing stop loss if market has moved in favorable direction"""
        execution = trade.get("execution", {})
        direction = execution.get("direction")
        trailing_stop = trade["trailing_stop"]
        
        # Calculate the new stop loss level based on current price and trailing distance
        trailing_distance = trailing_stop.get("distance_pips", 50) / 10000
        
        if direction == Direction.LONG.value and current_price - trailing_distance > trade["stop_loss_price"]:
            # Update stop loss to trail price (preserving the distance)
            new_stop = current_price - trailing_distance
            trade["stop_loss_price"] = new_stop
            self.logger.info(f"Updated trailing stop for {execution_id} to {new_stop}")
        
        elif direction == Direction.SHORT.value and current_price + trailing_distance < trade["stop_loss_price"]:
            # Update stop loss to trail price (preserving the distance)
            new_stop = current_price + trailing_distance
            trade["stop_loss_price"] = new_stop
            self.logger.info(f"Updated trailing stop for {execution_id} to {new_stop}")
    
    async def update_market_data(self):
        """Update market data for all actively traded symbols"""
        # Collect symbols from pending and active trades
        symbols = set()
        
        for proposal in self.pending_trades.values():
            symbols.add(proposal.get("symbol"))
        
        for trade in self.active_trades.values():
            execution = trade.get("execution", {})
            symbols.add(execution.get("symbol"))
        
        # Fetch market data for each symbol
        for symbol in symbols:
            market_data = await self.execution_gateway.get_market_data(symbol)
            if market_data:
                self.market_data[symbol] = market_data
    
    def calculate_stop_price(self, execution, proposal):
        """Calculate the actual stop loss price"""
        direction = execution.executed_direction
        executed_price = execution.executed_price
        stop_loss_pips = proposal.get("stop_loss", 50)
        
        # Convert pips to price distance
        stop_distance = stop_loss_pips / 10000
        
        if direction == Direction.LONG:
            return executed_price - stop_distance
        else:  # SHORT
            return executed_price + stop_distance
    
    def calculate_take_profit_price(self, execution, proposal):
        """Calculate the actual take profit price"""
        direction = execution.executed_direction
        executed_price = execution.executed_price
        take_profit_pips = proposal.get("take_profit", 100)
        
        # Convert pips to price distance
        tp_distance = take_profit_pips / 10000
        
        if direction == Direction.LONG:
            return executed_price + tp_distance
        else:  # SHORT
            return executed_price - tp_distance


class SimulatedTradingGateway:
    """A simulated trading gateway for backtesting and development"""
    
    def __init__(self, slippage_model="fixed", fixed_slippage_pips=1.0, proportional_slippage=0.0001, logger=None):
        self.slippage_model = slippage_model
        self.fixed_slippage_pips = fixed_slippage_pips
        self.proportional_slippage = proportional_slippage
        self.logger = logger
        self.connected = False
        self.market_data = {}
        self.executed_trades = {}
        self.next_trade_id = 1
    
    async def connect(self):
        """Connect to the simulated trading environment"""
        self.connected = True
        
        # Initialize simulated market data for common forex pairs
        pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD", "USD/CAD", "EUR/GBP"]
        
        for pair in pairs:
            self.market_data[pair] = {
                # Typical spreads for major pairs
                "bid": self._get_initial_price(pair),
                "ask": self._get_initial_price(pair) + self._get_spread(pair),
                "time": datetime.utcnow().isoformat(),
                "volume": 0
            }
        
        if self.logger:
            self.logger.info("Connected to simulated trading environment")
    
    async def disconnect(self):
        """Disconnect from the simulated trading environment"""
        self.connected = False
        if self.logger:
            self.logger.info("Disconnected from simulated trading environment")
    
    async def execute_trade(self, symbol, direction, size, order_type="MARKET", limit_price=None):
        """Execute a simulated trade"""
        if not self.connected:
            return {"success": False, "error": "Not connected"}
        
        if symbol not in self.market_data:
            return {"success": False, "error": f"Symbol {symbol} not found"}
        
        # Get current market data
        market = self.market_data[symbol]
        
        # Apply slippage to determine execution price
        if direction == Direction.LONG or direction == Direction.LONG.value:
            base_price = market["ask"]
            slippage = self._calculate_slippage(base_price, True)
            executed_price = base_price + slippage
        else:  # SHORT
            base_price = market["bid"]
            slippage = self._calculate_slippage(base_price, False)
            executed_price = base_price - slippage
        
        # For limit orders, check if the price is acceptable
        if order_type == "LIMIT" and limit_price is not None:
            if
