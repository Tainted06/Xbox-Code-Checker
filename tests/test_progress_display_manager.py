"""
Unit tests for ProgressDisplayManager component
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import customtkinter as ctk
import threading
import time

from src.gui.components.progress_display_manager import ProgressDisplayManager
from src.data.models import CodeResult, CodeStatus
from datetime import datetime


class TestProgressDisplayManager(unittest.TestCase):
    """Test cases for ProgressDisplayManager component"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock parent frame
        self.mock_parent = Mock(spec=ctk.CTkFrame)
        
        # Create ProgressDisplayManager instance with comprehensive mocking
        with patch('src.gui.components.progress_display_manager.ctk.CTkFrame') as mock_frame, \
             patch('src.gui.components.progress_display_manager.ctk.CTkLabel') as mock_label, \
             patch('src.gui.components.progress_display_manager.ctk.CTkProgressBar') as mock_progressbar, \
             patch('src.gui.components.progress_display_manager.ctk.CTkFont') as mock_font:
            
            # Setup mock returns
            mock_frame.return_value = Mock()
            mock_label.return_value = Mock()
            mock_progressbar.return_value = Mock()
            mock_font.return_value = Mock()
            
            self.manager = ProgressDisplayManager(self.mock_parent, update_interval=0.01)  # Fast updates for testing
    
    def tearDown(self):
        """Clean up after tests"""
        self.manager.cleanup()
    
    def test_initialization(self):
        """Test ProgressDisplayManager initialization"""
        self.assertEqual(self.manager.parent_frame, self.mock_parent)
        self.assertEqual(self.manager.update_interval, 0.01)
        self.assertEqual(self.manager._total_codes, 0)
        self.assertEqual(self.manager._checked_codes, 0)
        self.assertEqual(len(self.manager.progress_callbacks), 0)
        self.assertEqual(len(self.manager.status_callbacks), 0)
    
    def test_start_session(self):
        """Test starting a new session"""
        total_codes = 100
        
        # Mock UI elements
        self.manager.progress_bar = Mock()
        self.manager.progress_label = Mock()
        self.manager.stats_labels = {'valid': Mock(), 'used': Mock(), 'invalid': Mock(), 
                                   'expired': Mock(), 'error': Mock(), 'skipped': Mock(), 'wlid_token_error': Mock()}
        
        # Start session
        self.manager.start_session(total_codes)
        
        # Verify internal state
        self.assertEqual(self.manager._total_codes, total_codes)
        self.assertEqual(self.manager._checked_codes, 0)
        
        # Verify UI was updated
        self.manager.progress_label.configure.assert_called()
    
    def test_update_progress_with_valid_result(self):
        """Test updating progress with a valid result"""
        # Setup
        self.manager.start_session(10)
        self.manager.progress_bar = Mock()
        self.manager.progress_label = Mock()
        self.manager.stats_labels = {'valid': Mock(), 'used': Mock(), 'invalid': Mock(), 
                                   'expired': Mock(), 'error': Mock(), 'skipped': Mock()}
        
        # Create test result
        result = CodeResult(
            code="TEST-CODE-1",
            status=CodeStatus.VALID,
            timestamp=datetime.now(),
            details="Test result"
        )
        
        # Update progress
        self.manager.update_progress(result)
        
        # Force immediate update instead of waiting for timer
        self.manager.force_update()
        
        # Verify statistics
        stats = self.manager.get_statistics_summary()
        self.assertEqual(stats['valid'], 1)
        self.assertEqual(stats['checked'], 1)
    
    def test_update_progress_with_rate_limited_result(self):
        """Test that rate limited results don't count towards progress"""
        # Setup
        self.manager.start_session(10)
        
        # Create rate limited result
        result = CodeResult(
            code="TEST-CODE-1",
            status=CodeStatus.RATE_LIMITED,
            timestamp=datetime.now(),
            details="Rate limited"
        )
        
        # Update progress
        self.manager.update_progress(result)
        
        # Force immediate update instead of waiting for timer
        self.manager.force_update()
        
        # Verify statistics - should not count towards checked codes
        stats = self.manager.get_statistics_summary()
        self.assertEqual(stats['checked'], 0)  # Rate limited doesn't count
    
    def test_batched_updates(self):
        """Test that updates are properly batched"""
        # Setup
        self.manager.start_session(10)
        self.manager.progress_bar = Mock()
        self.manager.progress_label = Mock()
        self.manager.stats_labels = {'valid': Mock(), 'used': Mock(), 'invalid': Mock(), 
                                   'expired': Mock(), 'error': Mock(), 'skipped': Mock()}
        
        # Add multiple results quickly
        for i in range(5):
            result = CodeResult(
                code=f"TEST-CODE-{i}",
                status=CodeStatus.VALID,
                timestamp=datetime.now(),
                details=f"Test result {i}"
            )
            self.manager.update_progress(result)
        
        # Force immediate update to avoid waiting for timers
        self.manager.force_update()
        
        # Verify all results were processed
        stats = self.manager.get_statistics_summary()
        self.assertEqual(stats['valid'], 5)
        self.assertEqual(stats['checked'], 5)
    
    def test_progress_callbacks(self):
        """Test progress callback functionality"""
        # Setup callback
        callback_mock = Mock()
        self.manager.add_progress_callback(callback_mock)
        
        # Setup UI mocks
        self.manager.progress_bar = Mock()
        self.manager.progress_label = Mock()
        self.manager.stats_labels = {'valid': Mock(), 'used': Mock(), 'invalid': Mock(), 
                                   'expired': Mock(), 'error': Mock(), 'skipped': Mock()}
        
        # Start session and update
        self.manager.start_session(10)
        result = CodeResult(
            code="TEST-CODE-1",
            status=CodeStatus.VALID,
            timestamp=datetime.now(),
            details="Test result"
        )
        self.manager.update_progress(result)
        
        # Force immediate update instead of waiting for timer
        self.manager.force_update()
        
        # Verify callback was called
        callback_mock.assert_called()
    
    def test_status_callbacks(self):
        """Test status callback functionality"""
        # Setup callback
        callback_mock = Mock()
        self.manager.add_status_callback(callback_mock)
        
        # Update status
        test_status = "Test status"
        self.manager.update_status(test_status)
        
        # Verify callback was called
        callback_mock.assert_called_with(test_status)
    
    def test_callback_management(self):
        """Test adding and removing callbacks"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        self.manager.add_progress_callback(callback1)
        self.manager.add_progress_callback(callback2)
        self.manager.add_status_callback(callback1)
        
        self.assertEqual(len(self.manager.progress_callbacks), 2)
        self.assertEqual(len(self.manager.status_callbacks), 1)
        
        # Remove callbacks
        self.manager.remove_progress_callback(callback1)
        self.manager.remove_status_callback(callback1)
        
        self.assertEqual(len(self.manager.progress_callbacks), 1)
        self.assertEqual(len(self.manager.status_callbacks), 0)
        
        # Test removing non-existent callback (should not error)
        self.manager.remove_progress_callback(callback1)
        self.assertEqual(len(self.manager.progress_callbacks), 1)
    
    def test_session_control(self):
        """Test session control methods"""
        # Mock status label
        self.manager.status_label = Mock()
        
        # Test pause
        self.manager.pause_session()
        self.manager.status_label.configure.assert_called_with(text="Приостановлено")
        
        # Test resume
        self.manager.resume_session()
        self.manager.status_label.configure.assert_called_with(text="Продолжаем проверку...")
        
        # Test stop
        self.manager.stop_session()
        self.manager.status_label.configure.assert_called_with(text="Остановлено")
        
        # Test complete
        self.manager.complete_session()
        self.manager.status_label.configure.assert_called_with(text="Завершено")
    
    def test_statistics_summary(self):
        """Test getting statistics summary"""
        # Setup
        self.manager.start_session(20)
        
        # Add various results
        results = [
            CodeResult("CODE1", CodeStatus.VALID, datetime.now(), ""),
            CodeResult("CODE2", CodeStatus.USED, datetime.now(), ""),
            CodeResult("CODE3", CodeStatus.INVALID, datetime.now(), ""),
            CodeResult("CODE4", CodeStatus.ERROR, datetime.now(), ""),
            CodeResult("CODE5", CodeStatus.VALID, datetime.now(), "")
        ]
        
        for result in results:
            self.manager.update_progress(result)

        self.manager.force_update()
        
        # Get summary
        stats = self.manager.get_statistics_summary()
        
        # Verify counts
        self.assertEqual(stats['total'], 20)
        self.assertEqual(stats['checked'], 5)
        self.assertEqual(stats['valid'], 2)
        self.assertEqual(stats['used'], 1)
        self.assertEqual(stats['invalid'], 1)
        self.assertEqual(stats['error'], 1)
    
    def test_update_interval_setting(self):
        """Test setting update interval"""
        # Test valid interval
        self.manager.set_update_interval(0.5)
        self.assertEqual(self.manager.update_interval, 0.5)
        
        # Test invalid interval (should not change)
        original_interval = self.manager.update_interval
        self.manager.set_update_interval(-1)
        self.assertEqual(self.manager.update_interval, original_interval)
        
        self.manager.set_update_interval(0)
        self.assertEqual(self.manager.update_interval, original_interval)
    
    def test_cleanup(self):
        """Test cleanup functionality"""
        # Add some callbacks
        callback = Mock()
        self.manager.add_progress_callback(callback)
        self.manager.add_status_callback(callback)
        
        # Cleanup
        self.manager.cleanup()
        
        # Verify callbacks were cleared
        self.assertEqual(len(self.manager.progress_callbacks), 0)
        self.assertEqual(len(self.manager.status_callbacks), 0)
    
    def test_error_handling_in_callbacks(self):
        """Test error handling in callback notifications"""
        # Create callback that raises exception
        def failing_callback(data):
            raise Exception("Test exception")
        
        # Add failing callback
        self.manager.add_progress_callback(failing_callback)
        
        # Setup UI mocks
        self.manager.progress_bar = Mock()
        self.manager.progress_label = Mock()
        self.manager.stats_labels = {'valid': Mock(), 'used': Mock(), 'invalid': Mock(), 
                                   'expired': Mock(), 'error': Mock(), 'skipped': Mock()}
        
        # This should not crash despite the failing callback
        self.manager.start_session(10)
        result = CodeResult("CODE1", CodeStatus.VALID, datetime.now(), "")
        self.manager.update_progress(result)
        
        # Force immediate update instead of waiting for timer
        self.manager.force_update()
        
        # Manager should still function normally
        stats = self.manager.get_statistics_summary()
        self.assertEqual(stats['valid'], 1)
    
    def test_ui_update_error_handling(self):
        """Test error handling in UI updates"""
        # Setup with mock that raises exception
        self.manager.progress_bar = Mock()
        self.manager.progress_bar.set.side_effect = Exception("UI Error")
        self.manager.progress_label = Mock()
        self.manager.stats_labels = {}
        
        # This should not crash despite UI error
        progress_data = {
            'progress_percentage': 50,
            'checked_codes': 5,
            'total_codes': 10,
            'valid_count': 3,
            'used_count': 1,
            'invalid_count': 1,
            'expired_count': 0,
            'error_count': 0,
            'skipped_count': 0
        }
        
        # Should handle the exception gracefully
        self.manager._update_ui_immediate(progress_data)
        
        # Manager should still be functional
        self.assertIsNotNone(self.manager.progress_bar)


if __name__ == '__main__':
    unittest.main()