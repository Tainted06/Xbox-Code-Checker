import unittest
from unittest.mock import patch, MagicMock
from src.data.api_client import APIClient
from src.data.models import WLIDToken, CodeResult, CodeStatus, AppConfig
from datetime import datetime
import requests

class TestAPIClient(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig()
        self.wlid_tokens = [WLIDToken(token="test_token")]
        self.api_client = APIClient(self.wlid_tokens, self.config)

    def test_initialization(self):
        self.assertEqual(self.api_client.wlid_tokens, self.wlid_tokens)
        self.assertEqual(self.api_client.config, self.config)
        self.assertIsNotNone(self.api_client.session)

    @patch('requests.Session.get')
    def test_check_code_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tokenState": "Active"}
        mock_get.return_value = mock_response

        result = self.api_client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.assertEqual(result.status, CodeStatus.VALID)

    @patch('requests.Session.get')
    def test_check_code_rate_limited(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = self.api_client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.assertEqual(result.status, CodeStatus.RATE_LIMITED)

    @patch('requests.Session.get')
    def test_check_code_invalid_wlid(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.api_client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.assertEqual(result.status, CodeStatus.WLID_TOKEN_ERROR)

    @patch('requests.Session.get')
    def test_check_code_server_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = self.api_client.check_code("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.assertEqual(result.status, CodeStatus.ERROR)

    def test_parse_api_response_valid(self):
        response_data = {"tokenState": "Active"}
        result = self.api_client._parse_api_response("code", response_data, datetime.now())
        self.assertEqual(result.status, CodeStatus.VALID)

    def test_parse_api_response_used(self):
        response_data = {"tokenState": "Redeemed"}
        result = self.api_client._parse_api_response("code", response_data, datetime.now())
        self.assertEqual(result.status, CodeStatus.USED)

    def test_parse_api_response_invalid(self):
        response_data = {"tokenState": "Invalid"}
        result = self.api_client._parse_api_response("code", response_data, datetime.now())
        self.assertEqual(result.status, CodeStatus.INVALID)

    def test_parse_api_response_expired(self):
        response_data = {"tokenState": "Expired"}
        result = self.api_client._parse_api_response("code", response_data, datetime.now())
        self.assertEqual(result.status, CodeStatus.EXPIRED)

if __name__ == '__main__':
    unittest.main()
