#!/usr/bin/env python3
"""
API client for external service communication.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
import asyncio
import aiohttp

class APIClient:
    """Client for making API requests with retry logic and error handling"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize the API client
        
        Args:
            base_url: Base URL for the API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.api_key = api_key or os.getenv("API_KEY")
        self.timeout = timeout
        self.logger = logging.getLogger("api_client")
        self.session = None
    
    async def __aenter__(self):
        """Create session when used as async context manager"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session when leaving async context manager"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Create request headers with authentication if available"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def ensure_session(self):
        """Ensure an active session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def close(self):
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def request(self, method: str, endpoint: str, data: Any = None, 
                    params: Dict[str, Any] = None, headers: Dict[str, str] = None, 
                    retry_count: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
        """
        Send a request to the API with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            data: Optional request data (will be JSON encoded)
            params: Optional query parameters
            headers: Optional additional headers
            retry_count: Number of retries on failure
            retry_delay: Delay between retries (in seconds)
            
        Returns:
            API response parsed as JSON
            
        Raises:
            aiohttp.ClientError: On request failure after all retries
        """
        await self.ensure_session()
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        merged_headers = {**self._get_headers(), **(headers or {})}
        
        for attempt in range(retry_count + 1):
            try:
                if method.upper() == "GET":
                    async with self.session.get(url, params=params, headers=merged_headers) as response:
                        response.raise_for_status()
                        return await response.json()
                        
                elif method.upper() == "POST":
                    async with self.session.post(url, json=data, params=params, headers=merged_headers) as response:
                        response.raise_for_status()
                        return await response.json()
                        
                elif method.upper() == "PUT":
                    async with self.session.put(url, json=data, params=params, headers=merged_headers) as response:
                        response.raise_for_status()
                        return await response.json()
                        
                elif method.upper() == "DELETE":
                    async with self.session.delete(url, params=params, headers=merged_headers) as response:
                        response.raise_for_status()
                        return await response.json()
                        
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                    
            except aiohttp.ClientResponseError as e:
                # Don't retry on client errors (4xx)
                if 400 <= e.status < 500:
                    self.logger.error(f"Client error: {e}, URL: {url}")
                    raise
                    
                # Server errors (5xx) can be retried
                if attempt < retry_count:
                    self.logger.warning(f"Server error: {e}, retrying ({attempt+1}/{retry_count})")
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"Server error after {retry_count} retries: {e}")
                    raise
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < retry_count:
                    self.logger.warning(f"Request failed: {e}, retrying ({attempt+1}/{retry_count})")
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"Request failed after {retry_count} retries: {e}")
                    raise
                    
    async def get(self, endpoint: str, params: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a GET request"""
        return await self.request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Any = None, params: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a POST request"""
        return await self.request("POST", endpoint, data=data, params=params, **kwargs)
    
    async def put(self, endpoint: str, data: Any = None, params: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a PUT request"""
        return await self.request("PUT", endpoint, data=data, params=params, **kwargs)
    
    async def delete(self, endpoint: str, params: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a DELETE request"""
        return await self.request("DELETE", endpoint, params=params, **kwargs)