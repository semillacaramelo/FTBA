
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import uuid

from system.agent import Agent, Message, MessageType
from system.core import (
    Direction, TradeStatus,
    TradeProposal, TradeExecution, TradeResult
)
from system.deriv_api_client import DerivApiClient

class TradeExecutionAgent(Agent):
    """
    Agent responsible for managing order submission, monitoring open positions,
    and handling the trade lifecycle.
    """
    
    def __init__(self, agent_id: str, message_broker, config: Dict = None):
        """
        Initialize the Trade Execution Agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker for communication
            config: Agent configuration dictionary
        """
        super().__init__(agent_id, message_broker)
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.check_interval = self.config.get("check_interval_seconds", 1)
        
        # Trading parameters
        self.slippage_model = self.config.get("slippage_model", "fixed")
        self.fixed_slippage_pips = self.config.get("fixed_slippage_pips", 1.0)
        
        # Determine which gateway to use
        self.gateway_type = self.config.get("gateway_type", "simulation")
        self.use_demo_account = self.config.get("use_demo_account", True)
        
        # Trading state
        self.approved_proposals = {}  # proposal_id -> proposal
        self.open_trades = {}  # trade_id -> trade details
        self.trade_history = {}  # trade_id -> trade history
        
        # API client (will be initialized in setup)
        self.api_client = None
        
        # Last processed time
        self.last_processed_time = datetime.utcnow()
    
    async def setup(self):
        """Initialize the agent"""
        self.logger.info("Setting up Trade Execution Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.SYSTEM_STATUS,
            MessageType.TRADE_APPROVAL,
            MessageType.MARKET_DATA
        ])
        
        # Initialize API client based on gateway type
        if self.gateway_type == "deriv":
            from system.deriv_api_client import DerivApiClient
            self.api_client = DerivApiClient(
                app_id=self.config.get("app_id", ""),
                use_demo=self.use_demo_account,
                config=self.config
            )
            await self.api_client.connect()
        else:
            # Use simulation mode
            self.api_client = SimulationGateway(
                symbols=self.config.get("symbols", ["EUR/USD"]),
                config=self.config
            )
            await self.api_client.connect()
        
        self.logger.info(f"Connected to {self.gateway_type} gateway")
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Trade Execution Agent")
        
        # Close all open trades
        if self.open_trades:
            self.logger.info(f"Closing {len(self.open_trades)} open trades")
            for trade_id in list(self.open_trades.keys()):
                try:
                    await self.close_trade(trade_id, "System shutdown")
                except Exception as e:
                    self.logger.error(f"Error closing trade {trade_id}: {e}")
        
        # Disconnect API client
        if self.api_client:
            await self.api_client.disconnect()
    
    async def process_cycle(self):
        """Main processing cycle"""
        # Check if it's time to update
        current_time = datetime.utcnow()
        if (current_time - self.last_processed_time).total_seconds() >= self.check_interval:
            # Process approved proposals
            await self.process_approved_proposals()
            
            # Monitor open trades
            await self.monitor_open_trades()
            
            # Update the last processed time
            self.last_processed_time = current_time
        
        # Sleep to prevent CPU spinning
        await asyncio.sleep(self.check_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TRADE_APPROVAL:
            # Store approved trade proposal
            await self.handle_trade_approval(message)
        
        elif message.type == MessageType.MARKET_DATA:
            # Update market prices (for simulation or monitoring)
            await self.handle_market_data(message)
    
    async def handle_trade_approval(self, message: Message):
        """
        Handle trade approval message
        
        Args:
            message: Message containing trade approval
        """
        proposal_id = message.content.get("proposal_id")
        adjusted_proposal = message.content.get("adjusted_proposal")
        
        if not proposal_id or not adjusted_proposal:
            return
        
        # Store the approved proposal
        self.approved_proposals[proposal_id] = adjusted_proposal
        self.logger.info(f"Received approval for trade proposal {proposal_id}")
    
    async def handle_market_data(self, message: Message):
        """
        Handle market data update
        
        Args:
            message: Message containing market data
        """
        data = message.content
        if not data:
            return
        
        # Update API client with market data (for simulation)
        if hasattr(self.api_client, 'update_market_data'):
            await self.api_client.update_market_data(data)
    
    async def process_approved_proposals(self):
        """Process approved trade proposals and execute trades"""
        if not self.approved_proposals:
            return
        
        # Get proposals to process
        proposals_to_process = list(self.approved_proposals.items())
        
        # Process each proposal
        for proposal_id, proposal_data in proposals_to_process:
            try:
                # Convert to TradeProposal object if needed
                if isinstance(proposal_data, dict):
                    proposal = TradeProposal(**proposal_data)
                else:
                    proposal = proposal_data
                
                # Execute the trade
                execution_result = await self.execute_trade(proposal)
                
                # Remove from approved proposals
                del self.approved_proposals[proposal_id]
                
                # Send execution notification
                if execution_result:
                    await self.send_message(
                        MessageType.TRADE_EXECUTION,
                        {
                            "execution": execution_result.__dict__,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    self.logger.info(f"Executed trade for proposal {proposal_id}")
            
            except Exception as e:
                self.logger.error(f"Error executing trade for proposal {proposal_id}: {e}")
                
                # Remove from approved proposals after a few retries
                # In a real system, we would implement retry logic here
                del self.approved_proposals[proposal_id]
    
    async def execute_trade(self, proposal: TradeProposal) -> Optional[TradeExecution]:
        """
        Execute a trade based on the proposal
        
        Args:
            proposal: Trade proposal to execute
            
        Returns:
            TradeExecution: Execution details or None if failed
        """
        if not self.api_client:
            self.logger.error("API client not initialized")
            return None
        
        # Generate execution ID
        execution_id = f"exec_{uuid.uuid4().hex[:8]}_{datetime.utcnow().strftime('%H%M%S')}"
        
        try:
            # Submit order via API client
            result = await self.api_client.place_order(
                symbol=proposal.symbol,
                direction=proposal.direction,
                size=proposal.size,
                order_type="MARKET",  # Currently only supporting market orders
                price=proposal.entry_price,
                stop_loss=proposal.stop_loss,
                take_profit=proposal.take_profit
            )
            
            if not result.get("success", False):
                self.logger.error(f"Order execution failed: {result.get('error', 'Unknown error')}")
                return None
            
            # Get executed price and order ID
            executed_price = result.get("executed_price", proposal.entry_price)
            order_id = result.get("order_id", execution_id)
            
            # Calculate slippage
            entry_price = proposal.entry_price or executed_price
            slippage = abs(executed_price - entry_price) if proposal.entry_price else 0
            
            # Create execution record
            execution = TradeExecution(
                execution_id=execution_id,
                proposal_id=proposal.id,
                order_id=order_id,
                symbol=proposal.symbol,
                direction=proposal.direction,
                requested_size=proposal.size,
                executed_size=result.get("executed_size", proposal.size),
                requested_price=proposal.entry_price,
                executed_price=executed_price,
                stop_loss=proposal.stop_loss,
                take_profit=proposal.take_profit,
                execution_time=datetime.utcnow().isoformat(),
                slippage=slippage,
                status=TradeStatus.OPEN,
                gateway_type=self.gateway_type
            )
            
            # Store in open trades
            self.open_trades[execution_id] = {
                "execution": execution.__dict__,
                "proposal": proposal.__dict__,
                "order_id": order_id,
                "entry_time": datetime.utcnow(),
                "last_check_time": datetime.utcnow(),
                "current_price": executed_price,
                "unrealized_pnl": 0.0
            }
            
            self.logger.info(f"Trade executed: {proposal.symbol} {proposal.direction} at {executed_price}")
            return execution
        
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return None
    
    async def monitor_open_trades(self):
        """Monitor open trades for stop loss, take profit, or manual closing"""
        if not self.open_trades:
            return
        
        # Check each open trade
        for trade_id in list(self.open_trades.keys()):
            trade = self.open_trades[trade_id]
            
            try:
                # Get current price from API client
                symbol = trade["execution"]["symbol"]
                current_price = await self.api_client.get_current_price(symbol)
                
                if current_price is None:
                    continue
                
                # Update trade with current price
                trade["current_price"] = current_price
                trade["last_check_time"] = datetime.utcnow()
                
                # Calculate unrealized P&L
                direction = trade["execution"]["direction"]
                entry_price = trade["execution"]["executed_price"]
                size = trade["execution"]["executed_size"]
                
                pip_value = 0.0001 if not symbol.endswith("JPY") else 0.01
                price_diff = current_price - entry_price
                
                if direction == Direction.SHORT:
                    price_diff = -price_diff
                
                # Simple P&L calculation (in account currency)
                unrealized_pnl = price_diff * size / pip_value
                trade["unrealized_pnl"] = unrealized_pnl
                
                # Check stop loss and take profit
                stop_loss = trade["execution"].get("stop_loss")
                take_profit = trade["execution"].get("take_profit")
                
                # Check if stop loss hit
                if stop_loss is not None:
                    if (direction == Direction.LONG and current_price <= stop_loss) or \
                       (direction == Direction.SHORT and current_price >= stop_loss):
                        # Close trade at stop loss
                        await self.close_trade(trade_id, "Stop loss hit")
                        continue
                
                # Check if take profit hit
                if take_profit is not None:
                    if (direction == Direction.LONG and current_price >= take_profit) or \
                       (direction == Direction.SHORT and current_price <= take_profit):
                        # Close trade at take profit
                        await self.close_trade(trade_id, "Take profit hit")
                        continue
                
                # Check if trade has been open too long
                max_hold_time = trade.get("max_hold_minutes", 1440)  # Default to 24 hours
                if (datetime.utcnow() - trade["entry_time"]).total_seconds() / 60 > max_hold_time:
                    # Close trade due to max hold time
                    await self.close_trade(trade_id, "Maximum hold time reached")
                    continue
            
            except Exception as e:
                self.logger.error(f"Error monitoring trade {trade_id}: {e}")
    
    async def close_trade(self, trade_id: str, reason: str):
        """
        Close an open trade
        
        Args:
            trade_id: ID of trade to close
            reason: Reason for closing
        """
        if trade_id not in self.open_trades:
            self.logger.warning(f"Attempted to close non-existent trade {trade_id}")
            return
        
        trade = self.open_trades[trade_id]
        
        try:
            # Close position via API client
            result = await self.api_client.close_order(
                symbol=trade["execution"]["symbol"],
                order_id=trade["order_id"],
                size=trade["execution"]["executed_size"]
            )
            
            if not result.get("success", False):
                self.logger.error(f"Failed to close trade {trade_id}: {result.get('error', 'Unknown error')}")
                return
            
            # Get closing price
            closing_price = result.get("executed_price", trade["current_price"])
            
            # Calculate profit/loss
            entry_price = trade["execution"]["executed_price"]
            size = trade["execution"]["executed_size"]
            direction = trade["execution"]["direction"]
            
            price_diff = closing_price - entry_price
            if direction == Direction.SHORT:
                price_diff = -price_diff
            
            pip_value = 0.0001 if not trade["execution"]["symbol"].endswith("JPY") else 0.01
            profit_loss = price_diff * size / pip_value
            
            # Create trade result
            trade_result = TradeResult(
                trade_id=trade_id,
                proposal_id=trade["execution"]["proposal_id"],
                symbol=trade["execution"]["symbol"],
                direction=trade["execution"]["direction"],
                entry_price=entry_price,
                exit_price=closing_price,
                size=size,
                entry_time=trade["entry_time"].isoformat(),
                exit_time=datetime.utcnow().isoformat(),
                profit_loss=profit_loss,
                reason=reason,
                holding_time_minutes=round((datetime.utcnow() - trade["entry_time"]).total_seconds() / 60),
                strategy=trade["proposal"].get("strategy", "unknown")
            )
            
            # Move from open trades to history
            self.trade_history[trade_id] = {
                **trade,
                "result": trade_result.__dict__,
                "close_time": datetime.utcnow()
            }
            
            # Remove from open trades
            del self.open_trades[trade_id]
            
            # Send trade result message
            await self.send_message(
                MessageType.TRADE_RESULT,
                {
                    "result": trade_result.__dict__,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(f"Closed trade {trade_id}: {reason}, P&L: {profit_loss:.2f}")
        
        except Exception as e:
            self.logger.error(f"Error closing trade {trade_id}: {e}")


class SimulationGateway:
    """Simple simulation gateway for testing"""
    
    def __init__(self, symbols: List[str], config: Dict = None):
        """Initialize simulation gateway"""
        self.symbols = symbols
        self.config = config or {}
        self.logger = logging.getLogger("simulation_gateway")
        self.connected = False
        self.market_prices = {}  # symbol -> price
        self.open_orders = {}  # order_id -> order details
        
        # Initialize with default prices
        for symbol in symbols:
            self.market_prices[symbol] = 1.0
    
    async def connect(self):
        """Connect to simulated gateway"""
        self.connected = True
        return True
    
    async def disconnect(self):
        """Disconnect from simulated gateway"""
        self.connected = False
        return True
    
    async def update_market_data(self, data: Dict):
        """Update market data"""
        symbol = data.get("symbol")
        if not symbol or symbol not in self.symbols:
            return
        
        # Update price if OHLC data is available
        ohlc = data.get("ohlc")
        if ohlc and "close" in ohlc:
            self.market_prices[symbol] = ohlc["close"]
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        if not self.connected:
            return None
        
        return self.market_prices.get(symbol)
    
    async def place_order(self, symbol: str, direction: str, size: float, 
                        order_type: str, price: Optional[float] = None,
                        stop_loss: Optional[float] = None, 
                        take_profit: Optional[float] = None) -> Dict:
        """
        Place a simulated order
        
        Args:
            symbol: Trading symbol
            direction: Trade direction
            size: Trade size
            order_type: Order type (MARKET, LIMIT)
            price: Limit price (for LIMIT orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Dict: Order execution result
        """
        if not self.connected:
            return {"success": False, "error": "Gateway not connected"}
        
        if symbol not in self.market_prices:
            return {"success": False, "error": f"Symbol {symbol} not found"}
        
        # Get current price
        current_price = self.market_prices[symbol]
        
        # Add small random slippage
        import random
        slippage_pips = random.uniform(-2, 2)
        pip_value = 0.0001 if not symbol.endswith("JPY") else 0.01
        executed_price = current_price + (slippage_pips * pip_value)
        
        # Generate order ID
        order_id = f"sim_{uuid.uuid4().hex[:8]}"
        
        # Store order
        self.open_orders[order_id] = {
            "symbol": symbol,
            "direction": direction,
            "size": size,
            "executed_price": executed_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "order_time": datetime.utcnow()
        }
        
        return {
            "success": True,
            "order_id": order_id,
            "executed_price": executed_price,
            "executed_size": size
        }
    
    async def close_order(self, symbol: str, order_id: str, size: float) -> Dict:
        """
        Close a simulated order
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to close
            size: Size to close
            
        Returns:
            Dict: Order closure result
        """
        if not self.connected:
            return {"success": False, "error": "Gateway not connected"}
        
        if order_id not in self.open_orders:
            return {"success": False, "error": f"Order {order_id} not found"}
        
        # Get current price
        current_price = self.market_prices.get(symbol)
        
        # Add small random slippage
        import random
        slippage_pips = random.uniform(-2, 2)
        pip_value = 0.0001 if not symbol.endswith("JPY") else 0.01
        executed_price = current_price + (slippage_pips * pip_value)
        
        # Remove order
        self.open_orders.pop(order_id)
        
        return {
            "success": True,
            "order_id": order_id,
            "executed_price": executed_price,
            "executed_size": size
        }
