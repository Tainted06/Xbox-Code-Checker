"""
Unit tests for thread safety in Xbox Code Checker
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.code_checker import CodeChecker
from src.data.models import WLIDToken, CodeResult, CodeStatus, SessionStatus


class TestCodeCheckerThreadSafety(unittest.TestCase):
    """Test thread safety of CodeChecker pending_codes operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.wlid_tokens = [WLIDToken("test_token_1"), WLIDToken("test_token_2")]
        self.checker = CodeChecker(self.wlid_tokens, max_threads=3, request_delay=0.1)
    
    def test_concurrent_pending_codes_access(self):
        """Test concurrent access to pending_codes doesn't cause race conditions"""
        test_codes = [f"TEST-CODE-{i:04d}" for i in range(100)]
        
        # Initialize pending codes
        with self.checker.pending_codes_lock:
            self.checker.pending_codes = set(test_codes)
        
        results = []
        errors = []
        
        def worker_add_codes():
            """Worker that adds codes to pending_codes"""
            try:
                for i in range(50):
                    code = f"NEW-CODE-{i:04d}"
                    with self.checker.pending_codes_lock:
                        self.checker.pending_codes.add(code)
                    time.sleep(0.001)  # Small delay to increase chance of race condition
                results.append("add_completed")
            except Exception as e:
                errors.append(f"add_worker_error: {e}")
        
        def worker_remove_codes():
            """Worker that removes codes from pending_codes"""
            try:
                for code in test_codes[:50]:
                    with self.checker.pending_codes_lock:
                        self.checker.pending_codes.discard(code)  # Using discard to prevent KeyError
                    time.sleep(0.001)  # Small delay to increase chance of race condition
                results.append("remove_completed")
            except Exception as e:
                errors.append(f"remove_worker_error: {e}")
        
        def worker_read_codes():
            """Worker that reads from pending_codes"""
            try:
                for _ in range(100):
                    with self.checker.pending_codes_lock:
                        count = len(self.checker.pending_codes)
                        # Make a copy to avoid issues during iteration
                        codes_copy = self.checker.pending_codes.copy()
                    time.sleep(0.001)  # Small delay to increase chance of race condition
                results.append(f"read_completed_count_{count}")
            except Exception as e:
                errors.append(f"read_worker_error: {e}")
        
        # Start multiple threads
        threads = []
        threads.append(threading.Thread(target=worker_add_codes))
        threads.append(threading.Thread(target=worker_remove_codes))
        threads.append(threading.Thread(target=worker_read_codes))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent access: {errors}")
        self.assertEqual(len(results), 3, f"Not all workers completed: {results}")
        
        # Verify final state is consistent
        with self.checker.pending_codes_lock:
            final_count = len(self.checker.pending_codes)
        
        # Should have original codes (100) minus removed (50) plus added (50) = 100
        self.assertEqual(final_count, 100, f"Final pending codes count is incorrect: {final_count}")
    
    def test_concurrent_retry_counts_access(self):
        """Test concurrent access to retry_counts doesn't cause race conditions"""
        test_codes = [f"TEST-CODE-{i:04d}" for i in range(50)]
        
        # Initialize retry counts
        with self.checker.retry_counts_lock:
            self.checker.retry_counts = {code: 0 for code in test_codes}
        
        results = []
        errors = []
        
        def worker_increment_retries():
            """Worker that increments retry counts"""
            try:
                for code in test_codes[:25]:
                    for _ in range(3):  # Increment 3 times
                        with self.checker.retry_counts_lock:
                            current_count = self.checker.retry_counts.get(code, 0)
                            self.checker.retry_counts[code] = current_count + 1
                        time.sleep(0.001)
                results.append("increment_completed")
            except Exception as e:
                errors.append(f"increment_worker_error: {e}")
        
        def worker_read_retries():
            """Worker that reads retry counts"""
            try:
                for _ in range(100):
                    with self.checker.retry_counts_lock:
                        total_retries = sum(self.checker.retry_counts.values())
                        codes_with_retries = sum(1 for count in self.checker.retry_counts.values() if count > 0)
                    time.sleep(0.001)
                results.append(f"read_completed_total_{total_retries}_with_retries_{codes_with_retries}")
            except Exception as e:
                errors.append(f"read_worker_error: {e}")
        
        def worker_reset_some_retries():
            """Worker that resets some retry counts"""
            try:
                for code in test_codes[25:]:
                    with self.checker.retry_counts_lock:
                        self.checker.retry_counts[code] = 0
                    time.sleep(0.001)
                results.append("reset_completed")
            except Exception as e:
                errors.append(f"reset_worker_error: {e}")
        
        # Start multiple threads
        threads = []
        threads.append(threading.Thread(target=worker_increment_retries))
        threads.append(threading.Thread(target=worker_read_retries))
        threads.append(threading.Thread(target=worker_reset_some_retries))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent access: {errors}")
        self.assertEqual(len(results), 3, f"Not all workers completed: {results}")
        
        # Verify final state is consistent
        with self.checker.retry_counts_lock:
            final_retry_counts = self.checker.retry_counts.copy()
        
        # First 25 codes should have retry count of 3, last 25 should have 0
        for i, code in enumerate(test_codes):
            expected_count = 3 if i < 25 else 0
            actual_count = final_retry_counts.get(code, 0)
            self.assertEqual(actual_count, expected_count, 
                           f"Code {code} has incorrect retry count: {actual_count}, expected: {expected_count}")
    
    def test_discard_prevents_keyerror(self):
        """Test that using discard() instead of remove() prevents KeyError exceptions"""
        test_codes = [f"TEST-CODE-{i:04d}" for i in range(10)]
        
        # Initialize with some codes
        with self.checker.pending_codes_lock:
            self.checker.pending_codes = set(test_codes[:5])
        
        errors = []
        
        def worker_remove_codes():
            """Worker that tries to remove codes (some may not exist)"""
            try:
                for code in test_codes:  # Try to remove all codes, including non-existent ones
                    with self.checker.pending_codes_lock:
                        self.checker.pending_codes.discard(code)  # Should not raise KeyError
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"remove_worker_error: {e}")
        
        # Start multiple threads trying to remove codes
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=worker_remove_codes)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Check that no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred when using discard(): {errors}")
        
        # Verify all codes were removed
        with self.checker.pending_codes_lock:
            final_count = len(self.checker.pending_codes)
        
        self.assertEqual(final_count, 0, f"Not all codes were removed: {final_count} remaining")
    
    def test_thread_safe_session_info(self):
        """Test that get_session_info() works correctly with concurrent access"""
        test_codes = [f"TEST-CODE-{i:04d}" for i in range(20)]
        
        # Initialize data
        with self.checker.pending_codes_lock:
            self.checker.pending_codes = set(test_codes)
        with self.checker.retry_counts_lock:
            self.checker.retry_counts = {code: i % 3 for i, code in enumerate(test_codes)}
        
        self.checker.session.total_codes = len(test_codes)
        
        results = []
        errors = []
        
        def worker_get_session_info():
            """Worker that calls get_session_info()"""
            try:
                for _ in range(50):
                    info = self.checker.get_session_info()
                    # Verify the info is consistent
                    self.assertIn('pending_codes', info)
                    self.assertIn('retry_info', info)
                    self.assertIn('progress_percentage', info)
                    time.sleep(0.001)
                results.append("session_info_completed")
            except Exception as e:
                errors.append(f"session_info_error: {e}")
        
        def worker_modify_data():
            """Worker that modifies pending codes and retry counts"""
            try:
                for i in range(10):
                    code_to_remove = test_codes[i]
                    with self.checker.pending_codes_lock:
                        self.checker.pending_codes.discard(code_to_remove)
                    with self.checker.retry_counts_lock:
                        if code_to_remove in self.checker.retry_counts:
                            del self.checker.retry_counts[code_to_remove]
                    time.sleep(0.001)
                results.append("modify_completed")
            except Exception as e:
                errors.append(f"modify_error: {e}")
        
        # Start threads
        threads = []
        threads.append(threading.Thread(target=worker_get_session_info))
        threads.append(threading.Thread(target=worker_modify_data))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 2, f"Not all workers completed: {results}")


class TestProgressManagerThreadSafety(unittest.TestCase):
    """Test thread safety of ProgressManager operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        from src.core.progress_manager import ProgressManager
        self.progress_manager = ProgressManager()
    
    def test_concurrent_statistics_updates(self):
        """Test concurrent updates to statistics don't cause race conditions"""
        from src.data.models import CodeResult, CodeStatus
        
        # Start a session
        self.progress_manager.start_session(100)
        
        results = []
        errors = []
        
        def worker_update_progress():
            """Worker that updates progress with results"""
            try:
                for i in range(25):
                    # Create different types of results
                    status = [CodeStatus.VALID, CodeStatus.USED, CodeStatus.INVALID, CodeStatus.ERROR][i % 4]
                    result = CodeResult(
                        code=f"TEST-{i:04d}",
                        status=status,
                        timestamp=datetime.now(),
                        details=f"Test result {i}"
                    )
                    self.progress_manager.update_progress(result)
                    time.sleep(0.001)  # Small delay to increase chance of race condition
                results.append("update_completed")
            except Exception as e:
                errors.append(f"update_worker_error: {e}")
        
        def worker_get_progress_info():
            """Worker that reads progress information"""
            try:
                for _ in range(50):
                    info = self.progress_manager.get_progress_info()
                    # Verify the info is consistent
                    self.assertIn('total_codes', info)
                    self.assertIn('checked_codes', info)
                    self.assertIn('progress_percentage', info)
                    time.sleep(0.001)
                results.append("read_completed")
            except Exception as e:
                errors.append(f"read_worker_error: {e}")
        
        def worker_get_statistics():
            """Worker that reads statistics summary"""
            try:
                for _ in range(50):
                    stats = self.progress_manager.get_statistics_summary()
                    # Verify the stats are consistent
                    self.assertIn('total', stats)
                    self.assertIn('checked', stats)
                    self.assertIn('valid', stats)
                    time.sleep(0.001)
                results.append("stats_completed")
            except Exception as e:
                errors.append(f"stats_worker_error: {e}")
        
        # Start multiple threads
        threads = []
        for _ in range(2):  # 2 update workers
            thread = threading.Thread(target=worker_update_progress)
            threads.append(thread)
        
        threads.append(threading.Thread(target=worker_get_progress_info))
        threads.append(threading.Thread(target=worker_get_statistics))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent access: {errors}")
        self.assertEqual(len(results), 4, f"Not all workers completed: {results}")
        
        # Verify final statistics are consistent
        final_info = self.progress_manager.get_progress_info()
        self.assertEqual(final_info['checked_codes'], 50)  # 2 workers * 25 updates each
        
        # Verify counts add up correctly
        total_status_counts = (final_info['valid_count'] + final_info['used_count'] + 
                              final_info['invalid_count'] + final_info['error_count'])
        self.assertEqual(total_status_counts, 50)
    
    def test_concurrent_callback_management(self):
        """Test concurrent callback addition/removal doesn't cause race conditions"""
        results = []
        errors = []
        
        def dummy_progress_callback(info):
            pass
        
        def dummy_status_callback(message):
            pass
        
        def worker_add_remove_callbacks():
            """Worker that adds and removes callbacks"""
            try:
                for i in range(20):
                    # Add callbacks
                    self.progress_manager.add_progress_callback(dummy_progress_callback)
                    self.progress_manager.add_status_callback(dummy_status_callback)
                    time.sleep(0.001)
                    
                    # Remove callbacks
                    self.progress_manager.remove_progress_callback(dummy_progress_callback)
                    self.progress_manager.remove_status_callback(dummy_status_callback)
                    time.sleep(0.001)
                results.append("callback_management_completed")
            except Exception as e:
                errors.append(f"callback_worker_error: {e}")
        
        def worker_trigger_callbacks():
            """Worker that triggers callback notifications"""
            try:
                self.progress_manager.start_session(10)
                for i in range(10):
                    from src.data.models import CodeResult, CodeStatus
                    result = CodeResult(
                        code=f"CALLBACK-{i:04d}",
                        status=CodeStatus.VALID,
                        timestamp=datetime.now(),
                        details=f"Callback test {i}"
                    )
                    self.progress_manager.update_progress(result)
                    time.sleep(0.001)
                results.append("trigger_completed")
            except Exception as e:
                errors.append(f"trigger_worker_error: {e}")
        
        # Start multiple threads
        threads = []
        for _ in range(3):  # 3 callback management workers
            thread = threading.Thread(target=worker_add_remove_callbacks)
            threads.append(thread)
        
        threads.append(threading.Thread(target=worker_trigger_callbacks))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent callback management: {errors}")
        self.assertEqual(len(results), 4, f"Not all workers completed: {results}")
    
    def test_concurrent_session_state_changes(self):
        """Test concurrent session state changes are handled correctly"""
        results = []
        errors = []
        
        def worker_session_control():
            """Worker that controls session state"""
            try:
                for i in range(10):
                    self.progress_manager.start_session(50)
                    time.sleep(0.001)
                    self.progress_manager.pause_session()
                    time.sleep(0.001)
                    self.progress_manager.resume_session()
                    time.sleep(0.001)
                    self.progress_manager.stop_session()
                    time.sleep(0.001)
                    self.progress_manager.reset_session()
                    time.sleep(0.001)
                results.append("session_control_completed")
            except Exception as e:
                errors.append(f"session_control_error: {e}")
        
        def worker_read_status():
            """Worker that reads session status"""
            try:
                for _ in range(100):
                    info = self.progress_manager.get_progress_info()
                    # Just verify we can read the status without errors
                    self.assertIn('status', info)
                    time.sleep(0.001)
                results.append("status_read_completed")
            except Exception as e:
                errors.append(f"status_read_error: {e}")
        
        # Start multiple threads
        threads = []
        threads.append(threading.Thread(target=worker_session_control))
        threads.append(threading.Thread(target=worker_read_status))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent session state changes: {errors}")
        self.assertEqual(len(results), 2, f"Not all workers completed: {results}")


class TestGracefulThreadTermination(unittest.TestCase):
    """Test graceful thread termination in CodeChecker"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.wlid_tokens = [WLIDToken("test_token_1")]
        self.checker = CodeChecker(self.wlid_tokens, max_threads=2, request_delay=0.1)
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'checker'):
            self.checker.cleanup()
    
    @patch('src.data.api_client.APIClient')
    def test_graceful_thread_termination_timeout(self, mock_api_client_class):
        """Test that thread termination respects timeouts"""
        # Mock API client to simulate slow operations
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client
        
        def slow_check_code(code):
            # Simulate a slow API call that should be interrupted
            time.sleep(2.0)  # Longer than individual thread timeout
            return CodeResult(
                code=code,
                status=CodeStatus.VALID,
                timestamp=datetime.now(),
                details="Slow result"
            )
        
        mock_api_client.check_code.side_effect = slow_check_code
        mock_api_client.close.return_value = None
        
        # Start checking with a few codes
        test_codes = ["TEST-001", "TEST-002"]
        
        # Start checking in a separate thread to avoid blocking the test
        check_thread = threading.Thread(
            target=self.checker.check_codes_batch,
            args=(test_codes,)
        )
        check_thread.start()
        
        # Wait a bit for threads to start and session to be running
        time.sleep(0.5)
        
        # Verify session is running or completed (both are valid states to stop from)
        self.assertIn(self.checker.session.status, [SessionStatus.RUNNING, SessionStatus.COMPLETED])
        thread_status = self.checker.get_thread_status()
        self.assertGreater(thread_status['active_threads'], 0)
        
        # Stop checking and measure time
        start_time = time.time()
        result = self.checker.stop_checking()
        stop_time = time.time()
        
        # Verify stop was successful
        self.assertTrue(result)
        
        # Verify it didn't take too long (should respect timeout)
        elapsed_time = stop_time - start_time
        self.assertLess(elapsed_time, 15.0, "Thread termination took too long")
        
        # Verify session is stopped
        self.assertEqual(self.checker.session.status, SessionStatus.STOPPED)
        
        # Clean up the check thread
        check_thread.join(timeout=1.0)
    
    @patch('src.data.api_client.APIClient')
    def test_thread_status_monitoring(self, mock_api_client_class):
        """Test thread status monitoring during operation"""
        # Mock API client
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.check_code.return_value = CodeResult(
            code="TEST",
            status=CodeStatus.VALID,
            timestamp=datetime.now(),
            details="Test result"
        )
        mock_api_client.close.return_value = None
        
        # Start checking
        test_codes = ["TEST-001", "TEST-002", "TEST-003"]
        
        check_thread = threading.Thread(
            target=self.checker.check_codes_batch,
            args=(test_codes,)
        )
        check_thread.start()
        
        # Wait for threads to start and session to be running
        time.sleep(0.3)
        
        # Verify session is running or completed
        self.assertIn(self.checker.session.status, [SessionStatus.RUNNING, SessionStatus.COMPLETED])
        
        # Check thread status
        thread_status = self.checker.get_thread_status()
        
        self.assertIn('total_threads', thread_status)
        self.assertIn('active_threads', thread_status)
        self.assertIn('stop_event_set', thread_status)
        self.assertIn('pause_event_set', thread_status)
        self.assertIn('thread_details', thread_status)
        
        # Should have active threads
        self.assertGreater(thread_status['active_threads'], 0)
        self.assertFalse(thread_status['stop_event_set'])
        self.assertTrue(thread_status['pause_event_set'])  # Should be unpaused
        
        # Stop and verify status changes
        result = self.checker.stop_checking()
        self.assertTrue(result)
        
        final_status = self.checker.get_thread_status()
        self.assertTrue(final_status['stop_event_set'])
        
        # Clean up
        check_thread.join(timeout=1.0)
    
    def test_cleanup_resources(self):
        """Test that cleanup properly clears all resources"""
        # Initialize some data
        test_codes = ["TEST-001", "TEST-002", "TEST-003"]
        
        with self.checker.pending_codes_lock:
            self.checker.pending_codes = set(test_codes)
        with self.checker.retry_counts_lock:
            self.checker.retry_counts = {code: 1 for code in test_codes}
        
        # Add some items to queues
        for code in test_codes:
            self.checker.code_queue.put(code)
            result = CodeResult(
                code=code,
                status=CodeStatus.VALID,
                timestamp=datetime.now(),
                details="Test"
            )
            self.checker.result_queue.put(result)
        
        # Verify data is present
        with self.checker.pending_codes_lock:
            self.assertEqual(len(self.checker.pending_codes), 3)
        with self.checker.retry_counts_lock:
            self.assertEqual(len(self.checker.retry_counts), 3)
        self.assertFalse(self.checker.code_queue.empty())
        self.assertFalse(self.checker.result_queue.empty())
        
        # Call cleanup
        self.checker._cleanup_resources()
        
        # Verify everything is cleared
        with self.checker.pending_codes_lock:
            self.assertEqual(len(self.checker.pending_codes), 0)
        with self.checker.retry_counts_lock:
            self.assertEqual(len(self.checker.retry_counts), 0)
        self.assertTrue(self.checker.code_queue.empty())
        self.assertTrue(self.checker.result_queue.empty())
    
    @patch('src.data.api_client.APIClient')
    def test_stop_checking_multiple_calls(self, mock_api_client_class):
        """Test that multiple calls to stop_checking are handled gracefully"""
        # Mock API client
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.check_code.return_value = CodeResult(
            code="TEST",
            status=CodeStatus.VALID,
            timestamp=datetime.now(),
            details="Test result"
        )
        mock_api_client.close.return_value = None
        
        # Start checking
        test_codes = ["TEST-001"]
        
        check_thread = threading.Thread(
            target=self.checker.check_codes_batch,
            args=(test_codes,)
        )
        check_thread.start()
        
        # Wait for thread to start and session to be running
        time.sleep(0.2)
        
        # Verify session is running or completed
        self.assertIn(self.checker.session.status, [SessionStatus.RUNNING, SessionStatus.COMPLETED])
        
        # Call stop_checking multiple times
        result1 = self.checker.stop_checking()
        result2 = self.checker.stop_checking()  # Should return False
        result3 = self.checker.stop_checking()  # Should return False
        
        self.assertTrue(result1)   # First call should succeed
        self.assertFalse(result2)  # Subsequent calls should return False
        self.assertFalse(result3)
        
        # Verify session is stopped
        self.assertEqual(self.checker.session.status, SessionStatus.STOPPED)
        
        # Clean up
        check_thread.join(timeout=1.0)
    
    def test_thread_termination_under_various_conditions(self):
        """Test thread termination under various session states"""
        # Test stopping when not running
        result = self.checker.stop_checking()
        self.assertFalse(result)  # Should return False when not running
        
        # Test stopping when paused
        self.checker.session.status = SessionStatus.PAUSED
        result = self.checker.stop_checking()
        self.assertTrue(result)  # Should work when paused
        
        # Reset for next test
        self.checker.session.status = SessionStatus.IDLE
        
        # Test stopping when already stopped
        self.checker.session.status = SessionStatus.STOPPED
        result = self.checker.stop_checking()
        self.assertFalse(result)  # Should return False when already stopped


if __name__ == '__main__':
    unittest.main()