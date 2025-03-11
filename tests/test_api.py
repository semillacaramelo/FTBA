#!/usr/bin/env python3
"""
Tests for the API client.
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock, Mock

# Add the root directory to the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.config import Config
from system.api_client import APIClient


class TestAPIClient(unittest.TestCase):
    """Tests for the APIClient class"""
    
    def setUp(self):
        # Create a test config
        self.config = Config()
        self.config.config_data = {
            "api": {
                "base_url": "https://api.example.com/v1",
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 0.1  # Short delay for tests
            }
        }
        
        # Initialize API client with mock session
        with patch('requests.Session') as mock_session:
            self.mock_session = MagicMock()
            mock_session.return_value = self.mock_session
            self.api_client = APIClient(self.config)
    
    def mock_response(self, status_code, json_data=None, raise_for_status=None):
        """Helper method to create a mock response"""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        
        mock_resp.status_code = status_code
        
        if json_data:
            mock_resp.json = Mock(return_value=json_data)
        
        return mock_resp
    
    def test_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.api_client.base_url, "https://api.example.com/v1")
        self.assertEqual(self.api_client.timeout, 30)
        self.assertEqual(self.api_client.retry_attempts, 3)
        self.assertEqual(self.api_client.retry_delay, 0.1)
    
    def test_get_request(self):
        """Test GET request"""
        # Mock the session's request method
        test_data = {"status": "success", "data": {"test": 123}}
        mock_resp = self.mock_response(200, test_data)
        self.mock_session.request.return_value = mock_resp
        
        # Make the request
        response = self.api_client.get("/test", params={"param": "value"})
        
        # Check the request was made correctly
        self.mock_session.request.assert_called_once_with(
            method="GET",
            url="https://api.example.com/v1/test",
            params={"param": "value"},
            data=None,
            timeout=30
        )
        
        # Check the response was parsed correctly
        self.assertEqual(response, test_data)
    
    def test_post_request(self):
        """Test POST request with data"""
        # Mock the session's request method
        test_data = {"status": "success", "data": {"id": 456}}
        mock_resp = self.mock_response(200, test_data)
        self.mock_session.request.return_value = mock_resp
        
        # Prepare request data
        post_data = {"name": "test", "value": 123}
        
        # Make the request
        response = self.api_client.post("/create", data=post_data)
        
        # Check the request was made correctly
        self.mock_session.request.assert_called_once_with(
            method="POST",
            url="https://api.example.com/v1/create",
            params=None,
            data=json.dumps(post_data),
            timeout=30
        )
        
        # Check the response was parsed correctly
        self.assertEqual(response, test_data)
    
    def test_put_request(self):
        """Test PUT request with data"""
        # Mock the session's request method
        test_data = {"status": "success", "data": {"updated": True}}
        mock_resp = self.mock_response(200, test_data)
        self.mock_session.request.return_value = mock_resp
        
        # Make the request
        response = self.api_client.put("/update", data={"id": 123, "value": "new"})
        
        # Check the request was made correctly
        self.mock_session.request.assert_called_once_with(
            method="PUT",
            url="https://api.example.com/v1/update",
            params=None,
            data='{"id": 123, "value": "new"}',
            timeout=30
        )
        
        # Check the response was parsed correctly
        self.assertEqual(response, test_data)
    
    def test_delete_request(self):
        """Test DELETE request"""
        # Mock the session's request method
        test_data = {"status": "success", "data": {"deleted": True}}
        mock_resp = self.mock_response(200, test_data)
        self.mock_session.request.return_value = mock_resp
        
        # Make the request
        response = self.api_client.delete("/delete", params={"id": 123})
        
        # Check the request was made correctly
        self.mock_session.request.assert_called_once_with(
            method="DELETE",
            url="https://api.example.com/v1/delete",
            params={"id": 123},
            data=None,
            timeout=30
        )
        
        # Check the response was parsed correctly
        self.assertEqual(response, test_data)
    
    def test_request_failure(self):
        """Test handling of request failure"""
        # Import the exceptions
        from requests.exceptions import RequestException
        
        # Mock a failing response
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = RequestException("Test error")
        mock_resp.status_code = 500
        self.mock_session.request.return_value = mock_resp
        
        # Make the request (should fail but not raise an exception)
        response = self.api_client.get("/test")
        
        # Check the response is None
        self.assertIsNone(response)
        
        # Should have attempted to retry
        self.assertEqual(self.mock_session.request.call_count, 3)
    
    def test_client_error_no_retry(self):
        """Test client errors (4xx) don't trigger retries"""
        # Import the exceptions
        from requests.exceptions import RequestException
        
        # Create a response that fails with a 404
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = RequestException("Not found")
        mock_resp.status_code = 404
        self.mock_session.request.return_value = mock_resp
        
        # Make the request
        response = self.api_client.get("/test")
        
        # Check the response is None
        self.assertIsNone(response)
        
        # Should not have attempted to retry
        self.assertEqual(self.mock_session.request.call_count, 1)
    
    def test_invalid_json_response(self):
        """Test handling of invalid JSON in response"""
        # Mock a response with invalid JSON
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()  # No exception
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        self.mock_session.request.return_value = mock_resp
        
        # Make the request
        response = self.api_client.get("/test")
        
        # Check the response is None
        self.assertIsNone(response)
    
    def test_api_key_from_env(self):
        """Test loading API key from environment variable"""
        with patch('os.getenv') as mock_getenv:
            # Mock the environment variable
            mock_getenv.return_value = "test_api_key_from_env"
            
            # Create a new API client
            with patch('requests.Session') as mock_session:
                mock_session_instance = MagicMock()
                mock_session.return_value = mock_session_instance
                client = APIClient(self.config)
            
            # Check that the API key was set in the headers
            headers = mock_session_instance.headers.update.call_args[0][0]
            self.assertEqual(headers["Authorization"], "Bearer test_api_key_from_env")


if __name__ == '__main__':
    unittest.main()
