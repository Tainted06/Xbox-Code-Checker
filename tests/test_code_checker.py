import unittest
from unittest.mock import patch, MagicMock
from src.core.code_checker import CodeChecker
from src.data.models import WLIDToken, CodeResult, CodeStatus, AppConfig, SessionStatus
from datetime import datetime
import time
import queue

class TestCodeChecker(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig()
        self.wlid_tokens = [WLIDToken(token="test_token")]
        self.code_checker = CodeChecker(self.wlid_tokens, self.config)

    def test_initialization(self):
        self.assertEqual(self.code_checker.wlid_tokens, self.wlid_tokens)
        self.assertEqual(self.code_checker.config, self.config)
        self.assertEqual(self.code_checker.max_threads, self.config.max_threads)
        self.assertEqual(self.code_checker.request_delay, self.config.request_delay)

    @patch('src.core.code_checker.APIClient')
    def test_start_and_stop_checking(self, mock_api_client):
        mock_api_client.return_value.check_code.return_value = CodeResult("code", CodeStatus.VALID, datetime.now())

        codes = ["code1", "code2"]
        self.code_checker.check_codes_batch(codes)

        time.sleep(1) # Allow threads to start

        self.assertEqual(self.code_checker.session.status, SessionStatus.RUNNING)
        self.assertTrue(self.code_checker.is_checking())

        self.code_checker.stop_checking()

        self.assertEqual(self.code_checker.session.status, SessionStatus.STOPPED)
        self.assertFalse(self.code_checker.is_checking())

    @patch('src.core.code_checker.APIClient')
    def test_pause_and_resume_checking(self, mock_api_client):
        mock_api_client.return_value.check_code.return_value = CodeResult("code", CodeStatus.VALID, datetime.now())

        codes = ["code1", "code2"]
        self.code_checker.check_codes_batch(codes)

        time.sleep(1)

        self.code_checker.pause_checking()
        self.assertEqual(self.code_checker.session.status, SessionStatus.PAUSED)

        self.code_checker.resume_checking()
        self.assertEqual(self.code_checker.session.status, SessionStatus.RUNNING)

        self.code_checker.stop_checking()

    @patch('time.sleep', return_value=None)
    @patch('src.core.code_checker.APIClient')
    def test_rate_limited_codes(self, mock_api_client, mock_sleep):
        mock_api_client.return_value.check_code.side_effect = [
            CodeResult("code1", CodeStatus.RATE_LIMITED, datetime.now()),
            CodeResult("code1", CodeStatus.VALID, datetime.now())
        ]

        codes = ["code1"]
        self.code_checker.check_codes_batch(codes)

        # Wait for the result queue to have a result
        try:
            self.code_checker.result_queue.get(timeout=1)
        except queue.Empty:
            # This is expected since the code is requeued
            pass

        # Stop checking after a short delay to allow the retry to be processed
        time.sleep(0.1)
        self.code_checker.stop_checking()

        # This is tricky to test without more complex mocking,
        # but we can check if the code was requeued.
        self.assertGreater(mock_api_client.return_value.check_code.call_count, 1)

    @patch('src.core.code_checker.APIClient')
    def test_invalid_wlid_token(self, mock_api_client):
        mock_api_client.return_value.check_code.side_effect = [
            CodeResult("code1", CodeStatus.WLID_TOKEN_ERROR, datetime.now()),
            CodeResult("code1", CodeStatus.VALID, datetime.now())
        ]

        codes = ["code1"]
        self.code_checker.check_codes_batch(codes)

        time.sleep(1)

        self.code_checker.stop_checking()

        self.assertGreater(mock_api_client.return_value.check_code.call_count, 1)

if __name__ == '__main__':
    unittest.main()
