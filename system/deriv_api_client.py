
import asyncio
import logging
from typing import Dict, List, Any, Optional
from deriv_api import DerivAPI
from deriv_api.errors import ResponseError, ConstructionError

class DerivApiClient:
    """Client for interacting with the Deriv API"""
    
    def __init__(self, app_id: str, endpoint: str = "wss://ws.binaryws.com/websockets/v3"):
        self.app_id = app_id
        self.endpoint = endpoint
        self.api = None
        self.logger = logging.getLogger("deriv_api_client")
        self.connected = False
    
    async def connect(self):
        """Connect to the Deriv API"""
        try:
            self.logger.info(f"Connecting to Deriv API at {self.endpoint}")
            self.api = DerivAPI(app_id=self.app_id, endpoint=self.endpoint)
            self.connected = True
            self.logger.info("Connected to Deriv API")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Deriv API: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
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
        """Ping the API to check connection status"""
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
        """Ensure the API client is connected, reconnect if necessary"""
        if self.connected and await self.ping():
            return True
        
        # Try to reconnect
        return await self.connect()
    
    async def get_active_symbols(self, market_type: str = "forex") -> List[Dict]:
        """Get available symbols for trading"""
        if not self.api:
            self.logger.error("Not connected to API")
            return []
        
        try:
            response = await self.api.active_symbols(
                active_symbols="brief", 
                product_type="basic"
            )
            
            # Filter by market type (e.g., forex)
            if market_type:
                return [s for s in response.get('active_symbols', []) 
                       if s.get('market', '').lower() == market_type.lower()]
            return response.get('active_symbols', [])
        except Exception as e:
            self.logger.error(f"Failed to get active symbols: {e}")
            return []
    
    async def get_price_proposal(self, symbol: str, contract_type: str, 
                                amount: float, duration: int, duration_unit: str,
                                basis: str = "stake") -> Dict:
        """Get price proposal for a contract"""
        if not self.api:
            self.logger.error("Not connected to API")
            return {}
        
        try:
            response = await self.api.proposal(
                contract_type=contract_type,
                currency="USD",
                symbol=symbol,
                amount=amount,
                basis=basis,
                duration=duration,
                duration_unit=duration_unit
            )
            return response.get('proposal', {})
        except ResponseError as e:
            self.logger.error(f"Proposal error: {e.message}")
            return {"error": e.message}
        except Exception as e:
            self.logger.error(f"Failed to get price proposal: {e}")
            return {}
    
    async def buy_contract(self, proposal_id: str, price: float) -> Dict:
        """Buy a contract based on proposal ID"""
        if not self.api:
            self.logger.error("Not connected to API")
            return {}
        
        try:
            response = await self.api.buy(
                buy=1,
                price=price,
                proposal_id=proposal_id
            )
            return response.get('buy', {})
        except ResponseError as e:
            self.logger.error(f"Buy error: {e.message}")
            return {"error": e.message}
        except Exception as e:
            self.logger.error(f"Failed to buy contract: {e}")
            return {}
    
    async def get_contract_update(self, contract_id: str) -> Dict:
        """Subscribe to contract updates"""
        if not self.api:
            self.logger.error("Not connected to API")
            return {}
        
        try:
            response = await self.api.proposal_open_contract(
                contract_id=contract_id
            )
            return response.get('proposal_open_contract', {})
        except Exception as e:
            self.logger.error(f"Failed to get contract update: {e}")
            return {}
    
    async def cancel_contract(self, contract_id: str) -> Dict:
        """Cancel a contract"""
        if not self.api:
            self.logger.error("Not connected to API")
            return {}
        
        try:
            response = await self.api.cancel(
                cancel=contract_id
            )
            return response.get('cancel', {})
        except Exception as e:
            self.logger.error(f"Failed to cancel contract: {e}")
            return {}
    
    async def get_account_balance(self) -> Dict:
        """Get account balance"""
        if not self.api:
            self.logger.error("Not connected to API")
            return {}
        
        try:
            response = await self.api.balance()
            return response.get('balance', {})
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return {}
    
    async def get_ticks(self, symbol: str) -> Dict:
        """Subscribe to tick data for a symbol"""
        if not self.api:
            self.logger.error("Not connected to API")
            return {}
        
        try:
            response = await self.api.ticks(
                ticks=symbol
            )
            return response
        except Exception as e:
            self.logger.error(f"Failed to get ticks: {e}")
            return {}
