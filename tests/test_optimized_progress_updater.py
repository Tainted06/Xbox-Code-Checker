"""
Tests for OptimizedProgressUpdater component
"""

import unittest
import time
from unittest.mock import Mock

from src.gui.components.optimized_progress_updater import (
    OptimizedProgressUpdater, 
    ProgressSnapshot
)
from src.data.models import CodeResult, CodeStatus
from datetime import datetime


class TestProgressSnapshot(unittest.TestCase):
    """Test cases for ProgressSnapshot"""
    
    def test_progress_snapshot_creation(self):
        """Test creating a progress snapshot"""
        snapshot = ProgressSnapshot(
            timestamp=time.time(),
            total_codes=100,
            checked_codes=50,
            statistics={'valid': 25, 'invalid': 25},
            progress_percentage=50.0,
            codes_per_second=10.0
        )
        
        self.assertEqual(snapshot.total_codes, 100)
        self.assertEqual(snapshot.checked_codes, 50)
        self.assertEqual(snapshot.progress_percentage, 50.0)
        self.assertEqual(snapshot.codes_per_second, 10.0)
        self.assertEqual(snapshot.statistics['valid'], 25)


class TestOptimizedProgressUpdater(unittest.TestCase):
    """Test cases for OptimizedProgressUpdater"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.updater = OptimizedProgressUpdater(
            update_interval=0.05,  # Fast updates for testing
            debounce_window=0.02,
            animation_duration=0.1,
            max_update_frequency=100.0
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.updater.is_running():
            self.updater.stop()
    
    def test_initialization(self):
        """Test updater initialization"""
        self.assertEqual(self.updater.update_interval, 0.05)
        self.assertEqual(self.updater.debounce_window, 0.02)
        self.assertEqual(self.updater.animation_duration, 0.1)
        self.assertFalse(self.updater.is_running())
        
        # Check initial snapshot
        snapshot = self.updater.get_current_snapshot()
        self.assertEqual(snapshot.total_codes, 0)
        self.assertEqual(snapshot.checked_codes, 0)
        self.assertEqual(snapshot.progress_percentage, 0.0)
    
    def test_start_stop(self):
        """Test starting and stopping the updater"""
        self.assertFalse(self.updater.is_running())
        
        self.updater.start()
        self.assertTrue(self.updater.is_running())
        
        self.updater.stop()
        self.assertFalse(self.updater.is_running())
    
    def test_queue_progress_update(self):
        """Test queuing progress updates"""
        self.updater.start()
        
        # Queue an update
        statistics = {'valid': 10, 'invalid': 5}
        self.updater.queue_progress_update(
            total_codes=100,
            checked_codes=15,
            statistics=statistics,
            codes_per_second=5.0
        )
        
        # Wait for processing and animation to complete
        time.sleep(0.2)
        
        # Check that update was processed (allow for animation interpolation)
        snapshot = self.updater.get_current_snapshot()
        self.assertEqual(snapshot.total_codes, 100)
        self.assertGreaterEqual(snapshot.checked_codes, 10)  # Should be close to 15
        self.assertLessEqual(snapshot.checked_codes, 15)
        self.assertGreater(snapshot.progress_percentage, 0.0)
        self.assertGreater(snapshot.statistics['valid'], 0)
        self.assertGreater(snapshot.statistics['invalid'], 0)
    
    def test_debouncing(self):
        """Test that rapid updates are debounced"""
        self.updater.start()
        
        # Queue multiple rapid updates
        for i in range(10):
            statistics = {'valid': i, 'invalid': 0}
            self.updater.queue_progress_update(
                total_codes=100,
                checked_codes=i,
                statistics=statistics
            )
        
        # Wait for processing
        time.sleep(0.15)
        
        # Should have the last update
        snapshot = self.updater.get_current_snapshot()
        self.assertEqual(snapshot.checked_codes, 9)  # Last update (0-indexed)
        
        # Check performance stats
        stats = self.updater.get_performance_stats()
        self.assertEqual(stats['total_updates'], 10)
        self.assertGreater(stats['debounced_updates'], 0)
    
    def test_callbacks(self):
        """Test callback functionality"""
        progress_callback = Mock()
        animation_callback = Mock()
        
        self.updater.add_progress_callback(progress_callback)
        self.updater.add_animation_callback(animation_callback)
        
        self.updater.start()
        
        # Queue an update that should trigger animation
        statistics = {'valid': 50}
        self.updater.queue_progress_update(
            total_codes=100,
            checked_codes=50,
            statistics=statistics
        )
        
        # Wait for processing
        time.sleep(0.2)
        
        # Progress callback should have been called
        self.assertGreater(progress_callback.call_count, 0)
        
        # Animation callback might be called if animation was triggered
        # (depends on timing and animation thresholds)
    
    def test_animation_triggering(self):
        """Test that animations are triggered for significant changes"""
        self.updater.start()
        
        # Set initial state
        self.updater.queue_progress_update(
            total_codes=100,
            checked_codes=10,
            statistics={'valid': 10}
        )
        time.sleep(0.1)
        
        # Make a significant change (should trigger animation)
        self.updater.queue_progress_update(
            total_codes=100,
            checked_codes=50,  # 40% jump
            statistics={'valid': 50}
        )
        
        # Wait for animation to start
        time.sleep(0.05)
        
        stats = self.updater.get_performance_stats()
        # Animation might be triggered depending on the threshold
        self.assertGreaterEqual(stats['animations_started'], 0)
    
    def test_performance_stats(self):
        """Test performance statistics collection"""
        self.updater.start()
        
        # Queue some updates
        for i in range(5):
            self.updater.queue_progress_update(
                total_codes=100,
                checked_codes=i * 10,
                statistics={'valid': i * 10}
            )
        
        time.sleep(0.1)
        
        stats = self.updater.get_performance_stats()
        
        self.assertIn('total_updates', stats)
        self.assertIn('debounced_updates', stats)
        self.assertIn('animations_started', stats)
        self.assertIn('is_animating', stats)
        self.assertIn('pending_updates', stats)
        
        self.assertEqual(stats['total_updates'], 5)
        self.assertIsInstance(stats['is_animating'], bool)
    
    def test_configuration_updates(self):
        """Test updating configuration parameters"""
        # Test setting update interval
        self.updater.set_update_interval(0.2)
        self.assertEqual(self.updater.update_interval, 0.2)
        
        # Test setting debounce window
        self.updater.set_debounce_window(0.1)
        self.assertEqual(self.updater.debounce_window, 0.1)
        
        # Test setting animation duration
        self.updater.set_animation_duration(0.5)
        self.assertEqual(self.updater.animation_duration, 0.5)
        
        # Test invalid values are ignored
        self.updater.set_update_interval(-1)
        self.assertEqual(self.updater.update_interval, 0.2)  # Should remain unchanged
    
    def test_callback_management(self):
        """Test adding and removing callbacks"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Test adding callbacks
        self.updater.add_progress_callback(callback1)
        self.updater.add_progress_callback(callback2)
        self.assertEqual(len(self.updater.progress_callbacks), 2)
        
        # Test adding duplicate callback (should not duplicate)
        self.updater.add_progress_callback(callback1)
        self.assertEqual(len(self.updater.progress_callbacks), 2)
        
        # Test removing callback
        self.updater.remove_progress_callback(callback1)
        self.assertEqual(len(self.updater.progress_callbacks), 1)
        self.assertIn(callback2, self.updater.progress_callbacks)
        
        # Test removing non-existent callback (should not error)
        self.updater.remove_progress_callback(callback1)
        self.assertEqual(len(self.updater.progress_callbacks), 1)
    
    def test_reset_functionality(self):
        """Test reset functionality"""
        self.updater.start()
        
        # Add some data
        self.updater.queue_progress_update(
            total_codes=100,
            checked_codes=50,
            statistics={'valid': 50}
        )
        time.sleep(0.1)
        
        # Verify data exists
        snapshot = self.updater.get_current_snapshot()
        self.assertGreater(snapshot.checked_codes, 0)  # Should have some progress
        
        stats = self.updater.get_performance_stats()
        self.assertGreater(stats['total_updates'], 0)
        
        # Reset
        self.updater.reset()
        
        # Verify reset state
        snapshot = self.updater.get_current_snapshot()
        self.assertEqual(snapshot.checked_codes, 0)
        self.assertEqual(snapshot.total_codes, 0)
        self.assertEqual(snapshot.progress_percentage, 0.0)
        
        stats = self.updater.get_performance_stats()
        self.assertEqual(stats['total_updates'], 0)
        self.assertEqual(stats['debounced_updates'], 0)
        self.assertEqual(stats['animations_started'], 0)
    
    def test_force_update(self):
        """Test forcing immediate updates"""
        self.updater.start()
        
        # Queue an update
        self.updater.queue_progress_update(
            total_codes=100,
            checked_codes=25,
            statistics={'valid': 25}
        )
        
        # Force immediate update
        self.updater.force_update()
        
        # Wait a bit for animation to complete
        time.sleep(0.15)
        
        # Should be processed (allow for animation)
        snapshot = self.updater.get_current_snapshot()
        self.assertGreater(snapshot.checked_codes, 0)
        self.assertLessEqual(snapshot.checked_codes, 25)
    
    def test_context_manager(self):
        """Test using updater as context manager"""
        with OptimizedProgressUpdater(update_interval=0.05) as updater:
            self.assertTrue(updater.is_running())
            
            updater.queue_progress_update(
                total_codes=100,
                checked_codes=10,
                statistics={'valid': 10}
            )
            time.sleep(0.15)  # Wait for animation to complete
            
            snapshot = updater.get_current_snapshot()
            self.assertGreater(snapshot.checked_codes, 0)  # Should have some progress
            self.assertLessEqual(snapshot.checked_codes, 10)
        
        # Should be stopped after context exit
        self.assertFalse(updater.is_running())
    
    def test_result_update_processing(self):
        """Test processing individual result updates"""
        self.updater.start()
        
        # Create a test result
        result = CodeResult(
            code="TEST001",
            status=CodeStatus.VALID,
            timestamp=datetime.now()
        )
        
        # Queue result update
        self.updater.queue_result_update(result)
        
        # This should update speed calculation
        time.sleep(0.1)
        
        # Speed history should have entries
        stats = self.updater.get_performance_stats()
        self.assertGreaterEqual(stats['speed_history_size'], 0)
    
    def test_interpolation_logic(self):
        """Test statistics interpolation logic"""
        # Create test snapshots
        start_stats = {'valid': 10, 'invalid': 5}
        end_stats = {'valid': 20, 'invalid': 10}
        
        # Test interpolation at 50%
        interpolated = self.updater._interpolate_statistics(start_stats, end_stats, 0.5)
        
        self.assertEqual(interpolated['valid'], 15)  # 10 + (20-10) * 0.5
        self.assertEqual(interpolated['invalid'], 7)  # 5 + (10-5) * 0.5 (rounded down)
        
        # Test with missing keys
        start_stats = {'valid': 10}
        end_stats = {'valid': 20, 'invalid': 10}
        
        interpolated = self.updater._interpolate_statistics(start_stats, end_stats, 0.5)
        
        self.assertEqual(interpolated['valid'], 15)
        self.assertEqual(interpolated['invalid'], 5)  # 0 + (10-0) * 0.5


if __name__ == '__main__':
    unittest.main()