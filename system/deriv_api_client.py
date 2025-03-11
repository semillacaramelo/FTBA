
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional

class DerivAPI:
    """Mock DerivAPI class for development without actual dependency"""
    async def disconnect(self):
        pass
    
    async def ping(self):
        return {"ping": 1}
    
    async def active_symbols(self, **kwargs):
        # Return some sample forex symbols for testing
        return {
            "active_symbols": [
                {
                    "symbol": "frxEURUSD",
                    "display_name": "EUR/USD",
                    "market": "forex",
                    "market_display_name": "Forex"
                },
                {
                    "symbol": "frxGBPUSD",
                    "display_name": "GBP/USD",
                    "market": "forex",
                    "market_display_name": "Forex"
                },
                {
                    "symbol": "frxUSDJPY",
                    "display_name": "USD/JPY",
                    "market": "forex",
                    "market_display_name": "Forex"
                }
            ]
        }
    
    async def proposal(self, **kwargs):
        # Mock proposal response with contract ID
        return {
            "proposal": {
                "id": "mock_proposal_123",
                "ask_price": 10.50,
                "date_start": 0,
                "date_expiry": 0,
                "spot": 1.10532,
                "spot_time": 0,
                "payout": 19.05
            }
        }
    
    async def buy(self, **kwargs):
        # Mock buy response
        return {
            "buy": {
                "contract_id": "mock_contract_456",
                "longcode": "Win payout if EUR/USD is strictly higher than entry spot after 5 minutes.",
                "start_time": 0,
                "transaction_id": "mock_transaction_789"
            }
        }
    
    async def proposal_open_contract(self, **kwargs):
        # Mock proposal open contract
        return {
            "proposal_open_contract": {
                "contract_id": kwargs.get("contract_id", "unknown"),
                "status": "open",
                "entry_spot": 1.10532,
                "current_spot": 1.10982,
                "profit": 5.25,
                "profit_percentage": 50.0
            }
        }
    
    async def cancel(self, **kwargs):
        # Mock cancel response
        return {
            "cancel": {
                "contract_id": kwargs.get("cancel", "unknown"),
                "refund_amount": 9.25
            }
        }
    
    async def balance(self, **kwargs):
        # Mock balance response
        return {
            "balance": {
                "balance": 1000.00,
                "currency": "USD",
                "loginid": "MOCK123456",
                "total": 1000.00
            }
        }
    
    async def ticks(self, **kwargs):
        # Mock ticks response
        symbol = kwargs.get("ticks", "unknown")
        return {
            "tick": {
                "symbol": symbol,
                "id": "mock_tick_1",
                "quote": 1.10532,
                "epoch": 0
            },
            "subscription": {
                "id": "mock_sub_1"
            }
        }

class ResponseError(Exception):
    """Mock response error class"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class DerivApiClient:
    """Client for interacting with the Deriv API with improved connection handling"""
    
    def __init__(self, app_id: str, endpoint: str = "wss://ws.binaryws.com/websockets/v3"):
        """
        Initialize the Deriv API client
        
        Args:
            app_id: The application ID for API authentication
            endpoint: The WebSocket endpoint URL
        """
        self.app_id = app_id
        self.endpoint = endpoint
        self.api = None
        self.logger = logging.getLogger("deriv_api_client")
        self.connected = False
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
    
    async def connect(self, retry_count: int = 0) -> bool:
        """
        Connect to the Deriv API with retry logic
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to Deriv API at {self.endpoint}")
            
            # In a real implementation, this would use the actual Deriv API
            # from deriv_api import DerivAPI
            # Create a mock DerivAPI instance - our mock class doesn't take parameters
            self.api = DerivAPI()
            
            # Validate connection with a ping
            ping_result = await self.ping()
            if not ping_result:
                raise ConnectionError("Failed to ping Deriv API after connection")
                
            self.connected = True
            self.logger.info("Successfully connected to Deriv API")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Deriv API: {e}")
            self.connected = False
            
            # Implement retry logic
            if retry_count < self.max_reconnect_attempts:
                retry_delay = self.reconnect_delay * (2 ** retry_count)  # Exponential backoff
                self.logger.info(f"Retrying connection in {retry_delay} seconds (attempt {retry_count + 1}/{self.max_reconnect_attempts})")
                await asyncio.sleep(retry_delay)
                return await self.connect(retry_count + 1)
            
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the Deriv API"""
        if self.api:
            try:
                await self.api.disconnect()
                self.logger.info("Disconnected from Deriv API")
            except Exception as e:
                self.logger.error(f"Error disconnecting from Deriv API: {e}")
            finally:
                self.api = None
                self.connected = False
    
    async def ping(self) -> bool:
        """
        Ping the API to check connection status
        
        Returns:
            bool: True if ping was successful, False otherwise
        """
        if not self.api:
            return False
        
        try:
            response = await self.api.ping()
            return 'ping' in response
        except Exception as e:
            self.logger.error(f"Ping failed: {e}")
            self.connected = False
            return False
            
    async def ensure_connected(self) -> bool:
        """
        Ensure the API client is connected, reconnect if necessary
        
        Returns:
            bool: True if connected or reconnected successfully, False otherwise
        """
        if self.connected and await self.ping():
            return True
        
        # Try to reconnect
        self.logger.info("Connection lost, attempting to reconnect")
        return await self.connect()
    
    async def _execute_with_retry(self, operation_name: str, operation_func, *args, **kwargs) -> Dict:
        """
        Execute an API operation with automatic reconnection on failure
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to execute
            *args, **kwargs: Arguments to pass to the operation function
            
        Returns:
            Dict: API response or error dictionary
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            if not await self.ensure_connected():
                return {"error": f"Failed to connect to Deriv API for {operation_name}"}
            
            try:
                return await operation_func(*args, **kwargs)
            except ResponseError as e:
                self.logger.error(f"{operation_name} error: {e.message}")
                return {"error": e.message}
            except Exception as e:
                self.logger.error(f"Failed to execute {operation_name}: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 1 * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"Retrying {operation_name} in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    return {"error": f"Failed to execute {operation_name} after {max_retries} attempts"}
        
        return {"error": "Unexpected execution flow"}
    
    async def get_active_symbols(self, market_type: str = "forex") -> List[Dict]:
        """
        Get available symbols for trading
        
        Args:
            market_type: Type of market to filter symbols by (e.g., "forex")
            
        Returns:
            List[Dict]: List of available symbols
        """
        response = await self._execute_with_retry(
            "get_active_symbols",
            lambda: self.api.active_symbols(active_symbols="brief", product_type="basic")
        )
        
        if "error" in response:
            return []
        
        # Filter by market type (e.g., forex)
        if market_type:
            return [s for s in response.get('active_symbols', []) 
                   if s.get('market', '').lower() == market_type.lower()]
        return response.get('active_symbols', [])
    
    async def get_price_proposal(self, symbol: str, contract_type: str, 
                               amount: float, duration: int, duration_unit: str,
                               basis: str = "stake") -> Dict:
        """
        Get price proposal for a contract
        
        Args:
            symbol: Trading symbol
            contract_type: Type of contract
            amount: Trade amount
            duration: Contract duration
            duration_unit: Unit of duration (e.g., "m" for minutes)
            basis: Basis for pricing (e.g., "stake")
            
        Returns:
            Dict: Price proposal details
        """
        response = await self._execute_with_retry(
            "get_price_proposal",
            lambda: self.api.proposal(
                contract_type=contract_type,
                currency="USD",
                symbol=symbol,
                amount=amount,
                basis=basis,
                duration=duration,
                duration_unit=duration_unit
            )
        )
        
        return response.get('proposal', {})
    
    async def buy_contract(self, proposal_id: str, price: float) -> Dict:
        """
        Buy a contract based on proposal ID
        
        Args:
            proposal_id: ID of the proposal to execute
            price: Price to execute at
            
        Returns:
            Dict: Contract purchase details
        """
        response = await self._execute_with_retry(
            "buy_contract",
            lambda: self.api.buy(
                buy=1,
                price=price,
                proposal_id=proposal_id
            )
        )
        
        return response.get('buy', {})
    
    async def get_contract_update(self, contract_id: str) -> Dict:
        """
        Get updates for an open contract
        
        Args:
            contract_id: ID of the contract
            
        Returns:
            Dict: Contract status details
        """
        response = await self._execute_with_retry(
            "get_contract_update",
            lambda: self.api.proposal_open_contract(contract_id=contract_id)
        )
        
        return response.get('proposal_open_contract', {})
    
    async def cancel_contract(self, contract_id: str) -> Dict:
        """
        Cancel a contract
        
        Args:
            contract_id: ID of the contract to cancel
            
        Returns:
            Dict: Cancellation details
        """
        response = await self._execute_with_retry(
            "cancel_contract",
            lambda: self.api.cancel(cancel=contract_id)
        )
        
        return response.get('cancel', {})
    
    async def get_account_balance(self) -> Dict:
        """
        Get account balance
        
        Returns:
            Dict: Account balance details
        """
        response = await self._execute_with_retry(
            "get_account_balance",
            lambda: self.api.balance()
        )
        
        return response.get('balance', {})
    
    async def get_ticks(self, symbol: str) -> Dict:
        """
        Subscribe to tick data for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict: Tick data
        """
        response = await self._execute_with_retry(
            "get_ticks",
            lambda: self.api.ticks(ticks=symbol)
        )
        
        return response
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol
        
        Args:
            symbol: Trading symbol (e.g., "frxEURUSD")
            
        Returns:
            float: Current market price or None if not available
        """
        # Map standard symbol format to Deriv format if needed
        deriv_symbol = self._map_to_deriv_symbol(symbol)
        
        # Get tick data for the symbol
        response = await self.get_ticks(deriv_symbol)
        
        # Check if response contains valid price data
        if "error" in response:
            self.logger.error(f"Error getting current price for {symbol}: {response.get('error')}")
            return None
            
        # Extract price from tick data
        tick = response.get("tick", {})
        if not tick:
            self.logger.warning(f"No tick data available for {symbol}")
            return None
            
        # Return the current quote
        return tick.get("quote")
    
    async def place_order(self, symbol: str, direction: str, size: float,
                         order_type: str, price: Optional[float] = None,
                         stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None) -> Dict:
        """
        Place a trading order
        
        Args:
            symbol: Trading symbol
            direction: Trade direction (LONG/SHORT)
            size: Trade size (stake amount)
            order_type: Order type (MARKET, LIMIT, etc.)
            price: Limit price (for LIMIT orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Dict: Order execution result
        """
        try:
            # Map standard symbol format to Deriv format
            deriv_symbol = self._map_to_deriv_symbol(symbol)
            
            # Determine contract type based on direction
            contract_type = "CALL" if direction == "LONG" else "PUT"
            
            # Default duration (we'll use 5 minutes for now, but this should come from config)
            duration = 5
            duration_unit = "m"
            
            # Get price proposal first
            proposal_response = await self.get_price_proposal(
                symbol=deriv_symbol,
                contract_type=contract_type,
                amount=size,
                duration=duration,
                duration_unit=duration_unit
            )
            
            if not proposal_response or "id" not in proposal_response:
                return {
                    "success": False,
                    "error": f"Failed to get price proposal for {symbol}"
                }
                
            # Extract proposal ID and price
            proposal_id = proposal_response.get("id")
            proposal_price = proposal_response.get("ask_price")
            
            # Execute the contract purchase
            purchase_response = await self.buy_contract(
                proposal_id=proposal_id,
                price=proposal_price
            )
            
            if not purchase_response or "contract_id" not in purchase_response:
                return {
                    "success": False,
                    "error": f"Failed to execute contract purchase for {symbol}"
                }
                
            # Extract contract details
            contract_id = purchase_response.get("contract_id")
            
            # Return success response with contract details
            return {
                "success": True,
                "order_id": contract_id,
                "executed_price": proposal_response.get("spot"),
                "executed_size": size
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_order(self, symbol: str, order_id: str, size: float) -> Dict:
        """
        Close an open order/contract
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to close
            size: Size to close (not used in Deriv API, full contract is closed)
            
        Returns:
            Dict: Order closure result
        """
        try:
            # In Deriv API, we use contract_id to cancel/sell back the contract
            cancel_response = await self.cancel_contract(contract_id=order_id)
            
            if not cancel_response or "contract_id" not in cancel_response:
                # Try to get the current contract state
                contract_update = await self.get_contract_update(contract_id=order_id)
                
                if "error" in contract_update:
                    return {
                        "success": False,
                        "error": f"Failed to close contract {order_id}: {contract_update.get('error')}"
                    }
                
                # Check if contract is already closed or expired
                status = contract_update.get("status", "")
                if status in ["sold", "expired"]:
                    return {
                        "success": True,
                        "executed_price": contract_update.get("sell_price", 0),
                        "message": f"Contract was already {status}"
                    }
                
                return {
                    "success": False,
                    "error": f"Failed to close contract {order_id}"
                }
            
            # Return success response with contract details
            return {
                "success": True,
                "order_id": order_id,
                "executed_price": cancel_response.get("sell_price", 0),
                "refund_amount": cancel_response.get("refund_amount", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error closing order {order_id} for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _map_to_deriv_symbol(self, symbol: str) -> str:
        """
        Map standard symbol format (e.g., EUR/USD) to Deriv format (e.g., frxEURUSD)
        
        Args:
            symbol: Standard symbol name
            
        Returns:
            str: Deriv symbol name
        """
        # Simple mapping for common forex pairs
        symbol_map = {
            "EUR/USD": "frxEURUSD",
            "GBP/USD": "frxGBPUSD",
            "USD/JPY": "frxUSDJPY",
            "USD/CHF": "frxUSDCHF",
            "AUD/USD": "frxAUDUSD",
            "NZD/USD": "frxNZDUSD",
            "EUR/GBP": "frxEURGBP",
            "EUR/JPY": "frxEURJPY",
            "GBP/JPY": "frxGBPJPY"
        }
        
        # Check if symbol already in Deriv format
        if symbol.startswith("frx"):
            return symbol
        
        # Remove any spaces
        clean_symbol = symbol.replace(" ", "")
        
        # Check if in mapping
        if clean_symbol in symbol_map:
            return symbol_map[clean_symbol]
        
        # Default case - prepend "frx" and remove "/"
        return f"frx{clean_symbol.replace('/', '')}"
