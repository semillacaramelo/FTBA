
import asyncio
import logging
import time
import os
import json
import websockets
import uuid
from typing import Dict, List, Any, Optional

# We're using our own implementation of DerivAPI since the package is not readily available
class DerivAPI:
    """Basic DerivAPI implementation using websockets directly"""
    def __init__(self, app_id, endpoint, token=None):
        self.app_id = app_id
        self.endpoint = endpoint
        self.token = token
        self.connection = None
        self.request_id = 0
        self.logger = logging.getLogger("deriv_api")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self):
        """Connect to the API endpoint"""
        if self.connection is None or self.connection.closed:
            endpoint_with_app_id = f"{self.endpoint}?app_id={self.app_id}"
            self.connection = await websockets.connect(endpoint_with_app_id)
            # Authenticate if token is provided
            if self.token:
                await self.authorize(self.token)
        return self.connection
    
    async def disconnect(self):
        """Disconnect from the API endpoint"""
        if self.connection and not self.connection.closed:
            await self.connection.close()
        self.connection = None
    
    async def send_request(self, request):
        """Send a request to the API"""
        if self.connection is None or self.connection.closed:
            await self.connect()
            
        self.request_id += 1
        request['req_id'] = self.request_id
        
        await self.connection.send(json.dumps(request))
        response = await self.connection.recv()
        return json.loads(response)
    
    async def authorize(self, token):
        """Authorize with API token"""
        request = {
            "authorize": token
        }
        return await self.send_request(request)
    
    async def ping(self):
        """Ping the API to check connection"""
        request = {
            "ping": 1
        }
        return await self.send_request(request)
    
    async def active_symbols(self, **kwargs):
        """Get active symbols"""
        request = {
            "active_symbols": kwargs.get("active_symbols", "brief"),
            "product_type": kwargs.get("product_type", "basic")
        }
        return await self.send_request(request)
    
    async def proposal(self, **kwargs):
        """Get price proposal"""
        request = {
            "proposal": 1,
            "contract_type": kwargs.get("contract_type"),
            "currency": kwargs.get("currency"),
            "symbol": kwargs.get("symbol"),
            "amount": kwargs.get("amount"),
            "basis": kwargs.get("basis", "stake"),
            "duration": kwargs.get("duration"),
            "duration_unit": kwargs.get("duration_unit")
        }
        return await self.send_request(request)
    
    async def buy(self, proposal_id: str, price: float = None) -> Dict:
        """Buy a contract"""
        request = {
            "buy": proposal_id,
            "price": price
        }
        return await self.send_request(request)
    
    async def proposal_open_contract(self, **kwargs):
        """Get open contract details"""
        request = {
            "proposal_open_contract": 1,
            "contract_id": kwargs.get("contract_id")
        }
        return await self.send_request(request)
    
    async def cancel(self, **kwargs):
        """Cancel a contract"""
        request = {
            "cancel": kwargs.get("cancel")
        }
        return await self.send_request(request)
    
    async def balance(self, **kwargs):
        """Get account balance"""
        request = {
            "balance": 1,
            "account": kwargs.get("account", "current")
        }
        return await self.send_request(request)
    
    async def ticks(self, **kwargs):
        """Get tick data for a symbol"""
        request = {
            "ticks": kwargs.get("ticks"),
            "subscribe": kwargs.get("subscribe", 1)
        }
        return await self.send_request(request)

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
            
            # Get API credentials from environment variables
            app_id = os.environ.get('DERIV_APP_ID', self.app_id)
            if not app_id:
                self.logger.warning("DERIV_APP_ID environment variable is not set, using default app_id")
                app_id = self.app_id
                
            # Determine which API token to use based on ENVIRONMENT variable
            environment = os.environ.get('ENVIRONMENT', 'demo').lower()
            
            if environment == 'demo':
                token = os.environ.get('DERIV_DEMO_API_TOKEN')
                self.logger.info("Using DEMO account for API connection")
            else:
                token = os.environ.get('DERIV_API_TOKEN')
                self.logger.info("Using REAL account for API connection")
                
            if not token:
                token_var = 'DERIV_DEMO_API_TOKEN' if environment == 'demo' else 'DERIV_API_TOKEN'
                self.logger.warning(f"{token_var} environment variable is not set, using demo mode without authentication")
            
            # Create a real DerivAPI instance with appropriate parameters
            self.api = DerivAPI(app_id=app_id, endpoint=self.endpoint, token=token)
            
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
        self.logger.info(f"Fetching active symbols for market type: {market_type}")
        
        try:
            response = await self._execute_with_retry(
                "get_active_symbols",
                lambda: self.api.active_symbols(active_symbols="brief", product_type="basic")
            )
            
            if "error" in response:
                self.logger.error(f"Error fetching active symbols: {response.get('error')}")
                return []
            
            symbols = response.get('active_symbols', [])
            self.logger.info(f"Received {len(symbols)} symbols from Deriv API")
            
            # Log a few symbols to debug
            if symbols:
                sample_symbols = symbols[:3]
                for symbol in sample_symbols:
                    self.logger.info(f"Symbol example - Display name: {symbol.get('display_name')}, Symbol: {symbol.get('symbol')}")
            
            # Filter by market type (e.g., forex)
            if market_type:
                filtered_symbols = [s for s in symbols 
                       if s.get('market', '').lower() == market_type.lower()]
                self.logger.info(f"Filtered to {len(filtered_symbols)} {market_type} symbols")
                return filtered_symbols
                
            return symbols
        except Exception as e:
            self.logger.error(f"Exception in get_active_symbols: {e}")
            return []
    
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
        self.logger.info(f"Requesting price proposal for {symbol} - {contract_type}, amount: {amount}, duration: {duration}{duration_unit}")
        
        try:
            # Make sure symbol is in the correct format for Deriv API
            deriv_symbol = self._map_to_deriv_symbol(symbol)
            self.logger.info(f"Using Deriv symbol: {deriv_symbol}")
            
            # Set up the request parameters
            proposal_params = {
                "contract_type": contract_type,
                "currency": "USD",
                "symbol": deriv_symbol,
                "amount": amount,
                "basis": basis,
                "duration": duration,
                "duration_unit": duration_unit
            }
            
            # Execute API request with retry logic
            response = await self._execute_with_retry(
                "get_price_proposal",
                lambda: self.api.proposal(**proposal_params)
            )
            
            # Check for errors
            if "error" in response:
                error_code = response.get("error", {}).get("code", "unknown")
                error_message = response.get("error", {}).get("message", "Unknown error")
                self.logger.error(f"Price proposal error: {error_code} - {error_message}")
                return {}
                
            # Extract proposal data
            proposal = response.get('proposal', {})
            
            if proposal:
                self.logger.info(f"Received proposal - ID: {proposal.get('id')}, Price: {proposal.get('ask_price')}")
            else:
                self.logger.error("No proposal data in response")
                
            return proposal
            
        except Exception as e:
            self.logger.error(f"Exception in get_price_proposal for {symbol}: {e}")
            return {}
    
    async def buy_contract(self, proposal_id: str, price: float) -> Dict:
        """
        Buy a contract based on proposal ID
        
        Args:
            proposal_id: ID of the proposal to execute
            price: Price to execute at
            
        Returns:
            Dict: Contract purchase details
        """
        self.logger.info(f"Buying contract with proposal ID: {proposal_id}, price: {price}")
        
        try:
            # Validate inputs to prevent None values
            if not proposal_id:
                self.logger.error("Cannot buy contract: proposal_id is empty")
                return {}
            
            # Execute the buy request
            # According to Deriv API docs, we need to send the contract parameters
            response = await self._execute_with_retry(
                "buy_contract",
                lambda: self.api.buy(proposal_id=proposal_id, price=price)  # Send price from proposal
            )
            
            # Check for errors
            if "error" in response:
                error_code = response.get("error", {}).get("code", "unknown")
                error_message = response.get("error", {}).get("message", "Unknown error")
                self.logger.error(f"Buy contract error: {error_code} - {error_message}")
                return {}
                
            # Extract contract details
            buy_data = response.get('buy', {})
            
            if buy_data:
                contract_id = buy_data.get("contract_id")
                self.logger.info(f"Successfully purchased contract: {contract_id}")
                self.logger.info(f"Contract details: Balance change: {buy_data.get('balance_after')} - {buy_data.get('balance_before')}")
            else:
                self.logger.error("No contract purchase data in response")
                
            return buy_data
            
        except Exception as e:
            self.logger.error(f"Exception in buy_contract: {e}")
            return {}
    
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
            
            # Default duration (we'll use 1 day since some shorter durations are not supported)
            duration = 1
            duration_unit = "d"
            
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
