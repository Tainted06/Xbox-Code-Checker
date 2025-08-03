"""
Unit tests for HTTP connection management in APIClient
"""

import unittest
import time
from unittest.mock import patch, MagicMock, Mock
import requests

from src.data.api_client import APIClient
from src.data.models import WLIDToken


class TestHTTPConnectionManagement(unittest.TestCase):
    """Test cases for HTTP connection management"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test WLID tokens
        self.test_tokens = [
            WLIDToken(token="test_token_1"),
            WLIDToken(token="test_token_2")
        ]
    
    def test_api_client_initialization(self):
        """Test APIClient initialization with connection pooling"""
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Check that session is initialized
        self.assertIsNotNone(client.session)
        self.assertFalse(client._session_closed)
        
        # Check default timeouts
        self.assertEqual(client.connection_timeout, 10.0)
        self.assertEqual(client.read_timeout, 30.0)
        
        # Check session headers
        self.assertIn('connection', client.session.headers)
        self.assertEqual(client.session.headers['connection'], 'keep-alive')
        
        client.close()
    
    def test_api_client_custom_timeouts(self):
        """Test APIClient initialization with custom timeouts"""
        client = APIClient(
            self.test_tokens, 
            request_delay=0.1,
            connection_timeout=5.0,
            read_timeout=15.0
        )
        
        self.assertEqual(client.connection_timeout, 5.0)
        self.assertEqual(client.read_timeout, 15.0)
        
        client.close()
    
    def test_context_manager_support(self):
        """Test APIClient as context manager"""
        with APIClient(self.test_tokens, request_delay=0.1) as client:
            self.assertIsNotNone(client.session)
            self.assertFalse(client._session_closed)
        
        # After context exit, session should be closed
        self.assertTrue(client._session_closed)
        self.assertIsNone(client.session)
    
    def test_manual_close(self):
        """Test manual session closing"""
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        self.assertIsNotNone(client.session)
        self.assertFalse(client._session_closed)
        
        client.close()
        
        self.assertTrue(client._session_closed)
        self.assertIsNone(client.session)
    
    def test_double_close(self):
        """Test that double close doesn't cause errors"""
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # First close
        client.close()
        self.assertTrue(client._session_closed)
        
        # Second close should not raise exception
        try:
            client.close()
        except Exception as e:
            self.fail(f"Double close raised exception: {e}")
    
    @patch('requests.Session')
    def test_session_reinitialization(self, mock_session_class):
        """Test session reinitialization after close"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Close the session
        client.close()
        self.assertTrue(client._session_closed)
        
        # Ensure session active should reinitialize
        client._ensure_session_active()
        
        self.assertFalse(client._session_closed)
        self.assertIsNotNone(client.session)
        
        client.close()
    
    def test_update_timeouts(self):
        """Test updating connection and read timeouts"""
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Update timeouts
        client.update_timeouts(connection_timeout=7.0, read_timeout=20.0)
        
        self.assertEqual(client.connection_timeout, 7.0)
        self.assertEqual(client.read_timeout, 20.0)
        
        # Test minimum limits
        client.update_timeouts(connection_timeout=0.5, read_timeout=2.0)
        
        self.assertEqual(client.connection_timeout, 1.0)  # Should be minimum
        self.assertEqual(client.read_timeout, 5.0)       # Should be minimum
        
        client.close()
    
    @patch('requests.Session.get')
    def test_timeout_usage_in_requests(self, mock_get):
        """Test that proper timeouts are used in HTTP requests"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'tokenState': 'Active'}
        mock_get.return_value = mock_response
        
        client = APIClient(
            self.test_tokens, 
            request_delay=0.1,
            connection_timeout=5.0,
            read_timeout=15.0
        )
        
        # Make a request
        result = client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        
        # Verify timeout was passed correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        
        # Check that timeout parameter was passed
        self.assertIn('timeout', call_args.kwargs)
        timeout = call_args.kwargs['timeout']
        
        # Should be tuple of (connection_timeout, read_timeout)
        self.assertEqual(timeout, (5.0, 15.0))
        
        client.close()
    
    @patch('requests.Session.get')
    def test_connection_error_handling(self, mock_get):
        """Test handling of connection errors"""
        # Mock connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        result = client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        
        # Should return error result
        self.assertEqual(result.status.value, 'error')
        self.assertIn("соединения", result.details)
        
        client.close()
    
    @patch('requests.Session.get')
    def test_timeout_error_handling(self, mock_get):
        """Test handling of timeout errors"""
        # Mock timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        result = client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        
        # Should return error result
        self.assertEqual(result.status.value, 'error')
        self.assertIn("Таймаут", result.details)
        
        client.close()
    
    @patch('requests.Session')
    def test_session_adapter_configuration(self, mock_session_class):
        """Test that session is configured with proper adapters"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Verify that mount was called for both HTTP and HTTPS
        mount_calls = mock_session.mount.call_args_list
        
        # Should have at least 2 calls (http:// and https://)
        self.assertGreaterEqual(len(mount_calls), 2)
        
        # Check that adapters were mounted
        mounted_schemes = [call[0][0] for call in mount_calls]
        self.assertIn('http://', mounted_schemes)
        self.assertIn('https://', mounted_schemes)
        
        client.close()
    
    @patch('requests.Session.get')
    def test_session_reinitialization_on_closed_session(self, mock_get):
        """Test that session is reinitialized when used after being closed"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'tokenState': 'Active'}
        mock_get.return_value = mock_response
        
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Close the session
        client.close()
        self.assertTrue(client._session_closed)
        
        # Make a request - should reinitialize session
        result = client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        
        # Session should be active again
        self.assertFalse(client._session_closed)
        self.assertIsNotNone(client.session)
        
        # Request should have been made
        mock_get.assert_called_once()
        
        client.close()
    
    def test_destructor_cleanup(self):
        """Test that destructor properly cleans up resources"""
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Store reference to check state
        session_closed_ref = client._session_closed
        
        # Delete client - should trigger __del__
        del client
        
        # Note: We can't directly test __del__ behavior as it's called by GC
        # This test mainly ensures __del__ doesn't raise exceptions
    
    @patch('requests.Session.close')
    def test_close_with_session_error(self, mock_close):
        """Test close method when session.close() raises an error"""
        # Mock session.close() to raise an exception
        mock_close.side_effect = Exception("Close failed")
        
        client = APIClient(self.test_tokens, request_delay=0.1)
        
        # Close should not raise exception even if session.close() fails
        try:
            client.close()
        except Exception as e:
            self.fail(f"close() raised exception when session.close() failed: {e}")
        
        # Session should still be marked as closed
        self.assertTrue(client._session_closed)
        self.assertIsNone(client.session)
    
    @patch('requests.Session.get')
    def test_test_wlid_tokens_with_timeouts(self, mock_get):
        """Test that test_wlid_tokens uses proper timeouts"""
        # Mock response for token testing
        mock_response = MagicMock()
        mock_response.status_code = 404  # Expected for dummy code
        mock_get.return_value = mock_response
        
        client = APIClient(
            self.test_tokens, 
            request_delay=0.1,
            connection_timeout=8.0,
            read_timeout=25.0
        )
        
        # Test tokens
        results = client.test_wlid_tokens()
        
        # Verify timeout was used (should be min of 5.0 and 8.0, min of 10.0 and 25.0)
        expected_timeout = (5.0, 10.0)
        
        # Check that get was called with proper timeout
        for call in mock_get.call_args_list:
            self.assertIn('timeout', call.kwargs)
            self.assertEqual(call.kwargs['timeout'], expected_timeout)
        
        client.close()


if __name__ == '__main__':
    unittest.main()