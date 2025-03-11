
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
        return {"active_symbols": []}
    
    async def proposal(self, **kwargs):
        return {"proposal": {}}
    
    async def buy(self, **kwargs):
        return {"buy": {}}
    
    async def proposal_open_contract(self, **kwargs):
        return {"proposal_open_contract": {}}
    
    async def cancel(self, **kwargs):
        return {"cancel": {}}
    
    async def balance(self, **kwargs):
        return {"balance": {}}
    
    async def ticks(self, **kwargs):
        return {}

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
            self.api = DerivAPI(app_id=self.app_id, endpoint=self.endpoint)
            
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
