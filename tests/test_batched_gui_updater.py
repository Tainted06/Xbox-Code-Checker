"""
Tests for BatchedGUIUpdater component
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch

from src.gui.components.batched_gui_updater import BatchedGUIUpdater, UpdatePriority


class TestBatchedGUIUpdater(unittest.TestCase):
    """Test cases for BatchedGUIUpdater"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.updater = BatchedGUIUpdater(
            update_interval=0.05,  # Fast updates for testing
            max_batch_size=10,
            coalesce_window=0.02
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.updater.is_running():
            self.updater.stop()
    
    def test_start_stop(self):
        """Test starting and stopping the updater"""
        self.assertFalse(self.updater.is_running())
        
        self.updater.start()
        self.assertTrue(self.updater.is_running())
        
        self.updater.stop()
        self.assertFalse(self.updater.is_running())
    
    def test_queue_update(self):
        """Test queuing updates"""
        mock_func = Mock()
        
        self.updater.queue_update(
            update_id="test_update",
            update_func=mock_func,
            priority=UpdatePriority.NORMAL
        )
        
        # Should execute immediately when not running
        mock_func.assert_called_once()
    
    def test_batched_updates(self):
        """Test that updates are processed in batches"""
        self.updater.start()
        
        mock_funcs = [Mock() for _ in range(5)]
        
        # Queue multiple updates
        for i, mock_func in enumerate(mock_funcs):
            self.updater.queue_update(
                update_id=f"test_update_{i}",
                update_func=mock_func,
                priority=UpdatePriority.NORMAL
            )
        
        # Wait for processing
        time.sleep(0.2)
        
        # All updates should be processed
        for mock_func in mock_funcs:
            mock_func.assert_called_once()
    
    def test_priority_ordering(self):
        """Test that higher priority updates are processed first"""
        # Use a slower update interval to ensure all updates are queued before processing
        updater = BatchedGUIUpdater(
            update_interval=0.2,  # Slower interval
            max_batch_size=10
        )
        updater.start()
        
        try:
            execution_order = []
            
            def create_update_func(name):
                def update_func():
                    execution_order.append(name)
                return update_func
            
            # Queue all updates quickly before any processing happens
            updater.queue_update("low", create_update_func("low"), UpdatePriority.LOW)
            updater.queue_update("urgent", create_update_func("urgent"), UpdatePriority.URGENT)
            updater.queue_update("normal", create_update_func("normal"), UpdatePriority.NORMAL)
            updater.queue_update("high", create_update_func("high"), UpdatePriority.HIGH)
            
            # Wait for processing
            time.sleep(0.5)
            
            # Should be processed in priority order
            expected_order = ["urgent", "high", "normal", "low"]
            self.assertEqual(execution_order, expected_order)
        
        finally:
            updater.stop()
    
    def test_update_coalescing(self):
        """Test that updates with same coalesce key are coalesced"""
        self.updater.start()
        
        mock_func1 = Mock()
        mock_func2 = Mock()
        mock_func3 = Mock()
        
        # Queue updates with same coalesce key
        self.updater.queue_update("update1", mock_func1, coalesce_key="test_key")
        self.updater.queue_update("update2", mock_func2, coalesce_key="test_key")
        self.updater.queue_update("update3", mock_func3, coalesce_key="test_key")
        
        # Wait for processing
        time.sleep(0.2)
        
        # Only the last update should be executed
        mock_func1.assert_not_called()
        mock_func2.assert_not_called()
        mock_func3.assert_called_once()
    
    def test_convenience_methods(self):
        """Test convenience methods for common update types"""
        self.updater.start()
        
        # Test progress update
        progress_data = {'progress': 50}
        self.updater.queue_progress_update(progress_data)
        
        # Test status update
        self.updater.queue_status_update("Testing")
        
        # Test statistics update
        stats_data = {'count': 100}
        self.updater.queue_statistics_update(stats_data)
        
        # Test urgent update
        mock_func = Mock()
        self.updater.queue_urgent_update("urgent_test", mock_func)
        
        # Wait for processing
        time.sleep(0.2)
        
        # Urgent update should be processed
        mock_func.assert_called_once()
    
    def test_statistics(self):
        """Test statistics collection"""
        self.updater.start()
        
        # Queue some updates
        for i in range(5):
            mock_func = Mock()
            self.updater.queue_update(f"test_{i}", mock_func)
        
        # Wait for processing
        time.sleep(0.2)
        
        stats = self.updater.get_statistics()
        
        # Check that statistics are collected
        self.assertGreater(stats['total_updates_requested'], 0)
        self.assertGreater(stats['total_updates_processed'], 0)
        self.assertGreaterEqual(stats['batches_processed'], 1)
    
    def test_max_batch_size(self):
        """Test that batch size is respected"""
        updater = BatchedGUIUpdater(
            update_interval=0.1,
            max_batch_size=3
        )
        updater.start()
        
        try:
            mock_funcs = [Mock() for _ in range(10)]
            
            # Queue more updates than max batch size
            for i, mock_func in enumerate(mock_funcs):
                updater.queue_update(f"test_{i}", mock_func)
            
            # Wait for multiple batch cycles
            time.sleep(0.5)
            
            # All updates should eventually be processed
            for mock_func in mock_funcs:
                mock_func.assert_called_once()
        
        finally:
            updater.stop()
    
    def test_context_manager(self):
        """Test using updater as context manager"""
        mock_func = Mock()
        
        with BatchedGUIUpdater(update_interval=0.05) as updater:
            self.assertTrue(updater.is_running())
            updater.queue_update("test", mock_func)
            time.sleep(0.1)
        
        # Should be stopped after context exit
        self.assertFalse(updater.is_running())
        mock_func.assert_called_once()
    
    def test_clear_queues(self):
        """Test clearing all queues"""
        mock_func = Mock()
        
        # Start first, then queue update
        self.updater.start()
        self.updater.queue_update("test", mock_func, priority=UpdatePriority.HIGH)
        
        # Immediately clear queues before processing
        self.updater.clear_queues()
        
        # Wait to ensure no processing happens
        time.sleep(0.1)
        
        # Update should not have been processed
        mock_func.assert_not_called()
    
    def test_queue_sizes(self):
        """Test getting queue sizes"""
        # Queue updates in different priorities without starting
        for i in range(3):
            self.updater.queue_update(f"low_{i}", Mock(), UpdatePriority.LOW)
        for i in range(2):
            self.updater.queue_update(f"high_{i}", Mock(), UpdatePriority.HIGH)
        
        self.updater.start()
        
        # Check initial queue sizes (might be processed quickly)
        queue_sizes = self.updater.get_queue_sizes()
        self.assertIsInstance(queue_sizes, dict)
        
        # All priority levels should be present
        for priority in UpdatePriority:
            self.assertIn(priority.name, queue_sizes)
    
    def test_error_handling(self):
        """Test error handling in update functions"""
        self.updater.start()
        
        def failing_update():
            raise Exception("Test error")
        
        def working_update():
            working_update.called = True
        working_update.called = False
        
        # Queue failing and working updates
        self.updater.queue_update("failing", failing_update)
        self.updater.queue_update("working", working_update)
        
        # Wait for processing
        time.sleep(0.2)
        
        # Working update should still be processed despite error
        self.assertTrue(working_update.called)


if __name__ == '__main__':
    unittest.main()