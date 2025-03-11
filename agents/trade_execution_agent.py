
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

from system.agent import Agent, Message, MessageType
from system.core import Direction, TradeExecution, TradeResult
from system.deriv_api_client import DerivApiClient


class TradeExecutionAgent(Agent):
    """Agent responsible for trade execution and position management"""
    
    def __init__(self, agent_id: str, message_broker, config: Dict):
        super().__init__(agent_id, message_broker)
        self.config = config
        self.gateway_type = config.get("gateway_type", "simulation")
        self.check_interval = config.get("check_interval_seconds", 1)
        self.active_trades = {}
        self.deriv_client = None
        self.contract_id_to_trade_id = {}  # Mapping between Deriv contract IDs and our trade IDs
        self.symbol_mapping = {}  # Mapping between our symbol format and Deriv format
        self.position_updates_task = None
    
    async def setup(self):
        """Initialize the trade execution agent"""
        self.logger.info("Setting up Trade Execution Agent")
        
        # Subscribe to relevant message types
        await self.subscribe_to([
            MessageType.TRADE_APPROVAL,
            MessageType.TRADE_REJECTION,
            MessageType.SYSTEM_STATUS
        ])
        
        # Set up the appropriate gateway based on configuration
        if self.gateway_type == "deriv":
            await self.setup_deriv_gateway()
        else:
            self.logger.info(f"Using simulation gateway for trade execution")
    
    async def setup_deriv_gateway(self):
        """Set up the Deriv API gateway"""
        # Get Deriv API configuration from global config
        global_config = {}
        try:
            # Import to access global configuration
            import json
            import os
            config_path = "config/settings.json"
            if os.path.exists(config_path):
                with open(config_path) as f:
                    global_config = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load global config: {e}")
            return
        
        deriv_config = global_config.get("deriv_api", {})
        
        # Get API credentials from config
        app_id = deriv_config.get("app_id")
        endpoint = deriv_config.get("endpoint", "wss://ws.binaryws.com/websockets/v3")
        
        if not app_id:
            self.logger.error("Deriv API app_id not configured")
            return
        
        # Store the symbol mapping
        self.symbol_mapping = deriv_config.get("symbols_mapping", {})
        
        # Initialize and connect to Deriv API
        self.deriv_client = DerivApiClient(app_id=app_id, endpoint=endpoint)
        connection_result = await self.deriv_client.connect()
        
        if connection_result:
            self.logger.info("Successfully connected to Deriv API")
            
            # Start monitoring open positions
            self.position_updates_task = asyncio.create_task(self.monitor_open_positions())
        else:
            self.logger.error("Failed to connect to Deriv API")
    
    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up Trade Execution Agent")
        
        # Cancel position monitoring task
        if self.position_updates_task:
            self.position_updates_task.cancel()
            try:
                await self.position_updates_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect from Deriv API if applicable
        if self.deriv_client:
            await self.deriv_client.disconnect()
    
    async def process_cycle(self):
        """Main processing cycle for the agent"""
        # Check if we're connected to the API
        if self.deriv_client and not self.deriv_client.connected:
            self.logger.warning("Deriv API connection lost, attempting to reconnect...")
            await self.deriv_client.connect()
        
        # Wait for the next check interval
        await asyncio.sleep(self.check_interval)
    
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.type == MessageType.TRADE_APPROVAL:
            await self.handle_trade_approval(message.content)
        elif message.type == MessageType.TRADE_REJECTION:
            await self.handle_trade_rejection(message.content)
    
    async def handle_trade_approval(self, content: Dict):
        """Handle an approved trade request"""
        trade_proposal = content.get("trade_proposal")
        if not trade_proposal:
            self.logger.error("Received trade approval without trade proposal")
            return
        
        trade_id = trade_proposal.get("id")
        symbol = trade_proposal.get("symbol")
        direction = trade_proposal.get("direction")
        entry_price = trade_proposal.get("entry_price")
        stop_loss = trade_proposal.get("stop_loss")
        take_profit = trade_proposal.get("take_profit")
        position_size = trade_proposal.get("position_size")
        
        self.logger.info(f"Executing approved trade: {trade_id} on {symbol}")
        
        # Execute the trade based on the gateway type
        if self.gateway_type == "deriv":
            await self.execute_deriv_trade(trade_id, symbol, direction, entry_price, 
                                         stop_loss, take_profit, position_size)
        else:
            # Simulation mode
            await self.execute_simulated_trade(trade_id, symbol, direction, entry_price, 
                                             stop_loss, take_profit, position_size)
    
    async def handle_trade_rejection(self, content: Dict):
        """Handle a rejected trade request"""
        trade_proposal = content.get("trade_proposal")
        reason = content.get("reason", "Unknown reason")
        
        if not trade_proposal:
            self.logger.error("Received trade rejection without trade proposal")
            return
        
        trade_id = trade_proposal.get("id")
        symbol = trade_proposal.get("symbol")
        
        self.logger.info(f"Trade rejected: {trade_id} on {symbol}. Reason: {reason}")
        
        # Notify other agents about the rejection
        await self.send_message(
            msg_type=MessageType.TRADE_EXECUTION,
            content={
                "trade_id": trade_id,
                "symbol": symbol,
                "status": "rejected",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def execute_deriv_trade(self, trade_id: str, symbol: str, direction: Direction, 
                               entry_price: float, stop_loss: float, take_profit: float, 
                               position_size: float):
        """Execute a trade using the Deriv API"""
        if not self.deriv_client or not self.deriv_client.connected:
            self.logger.error("Cannot execute trade: Not connected to Deriv API")
            return
        
        # Map our symbol format to Deriv's format
        deriv_symbol = self.symbol_mapping.get(symbol)
        if not deriv_symbol:
            self.logger.error(f"Symbol mapping not found for {symbol}")
            return
        
        # Get contract type based on direction
        contract_type = "CALL" if direction == Direction.LONG else "PUT"
        
        # Get global config for default values
        import json
        import os
        global_config = {}
        try:
            config_path = "config/settings.json"
            if os.path.exists(config_path):
                with open(config_path) as f:
                    global_config = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load global config: {e}")
        
        deriv_config = global_config.get("deriv_api", {})
        duration = deriv_config.get("default_duration", 5)
        duration_unit = deriv_config.get("default_duration_unit", "m")
        
        try:
            # Get price proposal
            self.logger.info(f"Requesting price proposal for {deriv_symbol}, {contract_type}")
            proposal = await self.deriv_client.get_price_proposal(
                symbol=deriv_symbol,
                contract_type=contract_type,
                amount=position_size,
                duration=duration,
                duration_unit=duration_unit
            )
            
            if not proposal or "error" in proposal:
                self.logger.error(f"Failed to get price proposal: {proposal.get('error', 'Unknown error')}")
                return
            
            proposal_id = proposal.get("id")
            price = proposal.get("ask_price")
            
            if not proposal_id or not price:
                self.logger.error(f"Invalid proposal response: {proposal}")
                return
            
            # Buy the contract
            self.logger.info(f"Buying contract with proposal ID: {proposal_id}")
            buy_response = await self.deriv_client.buy_contract(
                proposal_id=proposal_id,
                price=price
            )
            
            if not buy_response or "error" in buy_response:
                self.logger.error(f"Failed to buy contract: {buy_response.get('error', 'Unknown error')}")
                return
            
            contract_id = buy_response.get("contract_id")
            buy_price = buy_response.get("buy_price")
            
            if not contract_id:
                self.logger.error(f"Invalid buy response: {buy_response}")
                return
            
            # Store the mapping between our trade ID and Deriv's contract ID
            self.contract_id_to_trade_id[contract_id] = trade_id
            
            # Create trade execution record
            trade_execution = TradeExecution(
                trade_id=trade_id,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                execution_time=datetime.utcnow(),
                execution_price=buy_price,
                status="executed",
                metadata={"contract_id": contract_id, "provider": "deriv"}
            )
            
            # Store the active trade
            self.active_trades[trade_id] = trade_execution
            
            # Notify other agents about successful execution
            await self.send_message(
                msg_type=MessageType.TRADE_EXECUTION,
                content={
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "direction": direction.value,
                    "entry_price": buy_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "position_size": position_size,
                    "status": "executed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {"contract_id": contract_id, "provider": "deriv"}
                }
            )
            
            self.logger.info(f"Successfully executed trade {trade_id} with contract ID {contract_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing Deriv trade: {e}")
            
            # Notify other agents about execution failure
            await self.send_message(
                msg_type=MessageType.TRADE_EXECUTION,
                content={
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "status": "failed",
                    "reason": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def execute_simulated_trade(self, trade_id: str, symbol: str, direction: Direction, 
                                    entry_price: float, stop_loss: float, take_profit: float, 
                                    position_size: float):
        """Execute a simulated trade for testing"""
        self.logger.info(f"Simulating trade execution for {trade_id} on {symbol}")
        
        # Create simulated trade execution
        trade_execution = TradeExecution(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            execution_time=datetime.utcnow(),
            execution_price=entry_price,  # In simulation, assume perfect execution
            status="executed",
            metadata={"provider": "simulation"}
        )
        
        # Store the active trade
        self.active_trades[trade_id] = trade_execution
        
        # Notify other agents about successful execution
        await self.send_message(
            msg_type=MessageType.TRADE_EXECUTION,
            content={
                "trade_id": trade_id,
                "symbol": symbol,
                "direction": direction.value,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": position_size,
                "status": "executed",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"provider": "simulation"}
            }
        )
    
    async def monitor_open_positions(self):
        """Monitor open positions and handle updates for Deriv API"""
        try:
            while True:
                if not self.deriv_client or not self.deriv_client.connected:
                    await asyncio.sleep(5)
                    continue
                
                # Check each active trade that has a contract ID
                for trade_id, trade in list(self.active_trades.items()):
                    contract_id = trade.metadata.get("contract_id")
                    if contract_id and trade.metadata.get("provider") == "deriv":
                        # Get contract update
                        contract_update = await self.deriv_client.get_contract_update(contract_id)
                        
                        if not contract_update:
                            continue
                        
                        status = contract_update.get("status")
                        
                        # Check if contract is finished
                        if status in ["sold", "expired"]:
                            # Contract is closed, process the result
                            await self.process_completed_deriv_trade(trade_id, contract_update)
                
                # Sleep between updates
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            self.logger.info("Position monitoring task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in position monitoring task: {e}")
    
    async def process_completed_deriv_trade(self, trade_id: str, contract_data: Dict):
        """Process a completed Deriv trade"""
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        
        # Extract result data
        contract_id = contract_data.get("contract_id")
        exit_price = contract_data.get("sell_price", 0)
        profit_loss = contract_data.get("profit", 0)
        exit_time = datetime.utcnow()  # Use current time or try to parse from contract data
        
        # Determine exit reason
        exit_reason = "expired"
        if contract_data.get("status") == "sold":
            exit_reason = "manually_closed"
        if profit_loss > 0:
            exit_reason = "take_profit"
        elif profit_loss < 0:
            exit_reason = "stop_loss"
        
        # Calculate pip difference for forex
        pip_multiplier = 10000 if not trade.symbol.endswith("JPY") else 100
        price_diff = abs(exit_price - trade.entry_price)
        profit_loss_pips = price_diff * pip_multiplier
        
        # Create trade result
        trade_result = TradeResult(
            trade_id=trade_id,
            symbol=trade.symbol,
            direction=trade.direction,
            entry_price=trade.entry_price,
            exit_price=exit_price,
            position_size=trade.position_size,
            entry_time=trade.execution_time,
            exit_time=exit_time,
            profit_loss=profit_loss,
            profit_loss_pips=profit_loss_pips,
            exit_reason=exit_reason,
            strategy_name=trade.metadata.get("strategy_name", "unknown"),
            metadata={
                "provider": "deriv",
                "contract_id": contract_id,
                "contract_details": contract_data
            }
        )
        
        # Remove from active trades
        del self.active_trades[trade_id]
        if contract_id in self.contract_id_to_trade_id:
            del self.contract_id_to_trade_id[contract_id]
        
        # Notify other agents about the trade result
        await self.send_message(
            msg_type=MessageType.TRADE_RESULT,
            content={
                "trade_id": trade_id,
                "symbol": trade.symbol,
                "direction": trade.direction.value,
                "entry_price": trade.entry_price,
                "exit_price": exit_price,
                "position_size": trade.position_size,
                "entry_time": trade.execution_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "profit_loss": profit_loss,
                "profit_loss_pips": profit_loss_pips,
                "exit_reason": exit_reason,
                "status": "closed",
                "metadata": {
                    "provider": "deriv",
                    "contract_id": contract_id
                }
            }
        )
        
        self.logger.info(f"Trade {trade_id} completed with P/L: {profit_loss}")
