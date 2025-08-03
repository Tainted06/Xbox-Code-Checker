"""
Optimized Progress Updater Component

Provides optimized progress updates with debouncing, smooth animations,
and efficient statistics calculation to prevent UI blocking.
"""

import threading
import time
from typing import Dict, Any, Optional, Callable, List
from collections import deque
from dataclasses import dataclass
import customtkinter as ctk

from ...data.models import CodeResult, CodeStatus


@dataclass
class ProgressSnapshot:
    """Represents a snapshot of progress at a point in time"""
    timestamp: float
    total_codes: int
    checked_codes: int
    statistics: Dict[str, int]
    progress_percentage: float
    codes_per_second: float


class OptimizedProgressUpdater:
    """
    Optimized progress updater with debouncing, smooth animations,
    and efficient statistics calculation.
    """
    
    def __init__(self, 
                 update_interval: float = 0.1,
                 debounce_window: float = 0.05,
                 animation_duration: float = 0.3,
                 max_update_frequency: float = 60.0):
        """
        Initialize OptimizedProgressUpdater
        
        Args:
            update_interval: Base interval between updates (seconds)
            debounce_window: Time window for debouncing rapid changes (seconds)
            animation_duration: Duration for smooth animations (seconds)
            max_update_frequency: Maximum updates per second
        """
        self.update_interval = update_interval
        self.debounce_window = debounce_window
        self.animation_duration = animation_duration
        self.min_update_interval = 1.0 / max_update_frequency
        
        # Threading
        self._lock = threading.RLock()
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Progress state
        self._current_snapshot = ProgressSnapshot(
            timestamp=time.time(),
            total_codes=0,
            checked_codes=0,
            statistics={},
            progress_percentage=0.0,
            codes_per_second=0.0
        )
        self._target_snapshot = self._current_snapshot
        
        # Debouncing
        self._pending_updates: deque = deque(maxlen=1000)
        self._last_update_time = 0.0
        self._last_render_time = 0.0
        
        # Animation state
        self._animation_start_time = 0.0
        self._animation_start_snapshot: Optional[ProgressSnapshot] = None
        self._is_animating = False
        
        # Statistics calculation
        self._statistics_cache = {}
        self._statistics_dirty = False
        self._speed_history: deque = deque(maxlen=20)  # Keep last 20 measurements
        
        # Performance tracking
        self._update_count = 0
        self._debounced_count = 0
        self._animation_count = 0
        
        # Callbacks
        self.progress_callbacks: List[Callable[[ProgressSnapshot], None]] = []
        self.animation_callbacks: List[Callable[[float], None]] = []  # Progress 0.0-1.0
    
    def start(self) -> None:
        """Start the progress updater"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._stop_event.clear()
            
            self._update_thread = threading.Thread(
                target=self._update_loop,
                name="OptimizedProgressUpdater",
                daemon=True
            )
            self._update_thread.start()
    
    def stop(self) -> None:
        """Stop the progress updater"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            self._stop_event.set()
            
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
            
            # Process any remaining updates
            self._process_pending_updates()
    
    def queue_progress_update(self, 
                            total_codes: int,
                            checked_codes: int,
                            statistics: Dict[str, int],
                            codes_per_second: float = 0.0) -> None:
        """
        Queue a progress update with debouncing
        
        Args:
            total_codes: Total number of codes
            checked_codes: Number of codes checked
            statistics: Statistics dictionary
            codes_per_second: Current processing speed
        """
        current_time = time.time()
        
        # Create new snapshot
        progress_percentage = (checked_codes / total_codes * 100) if total_codes > 0 else 0.0
        
        new_snapshot = ProgressSnapshot(
            timestamp=current_time,
            total_codes=total_codes,
            checked_codes=checked_codes,
            statistics=statistics.copy(),
            progress_percentage=progress_percentage,
            codes_per_second=codes_per_second
        )
        
        with self._lock:
            # Add to pending updates (deque automatically limits size)
            self._pending_updates.append(new_snapshot)
            self._statistics_dirty = True
            self._update_count += 1
    
    def queue_result_update(self, result: CodeResult) -> None:
        """
        Queue an update based on a single result
        
        Args:
            result: Code result to process
        """
        # This would typically be called by the main progress system
        # For now, we'll just track that an update occurred
        current_time = time.time()
        
        with self._lock:
            # Update speed calculation
            self._update_speed_calculation()
    
    def _update_loop(self) -> None:
        """Main update processing loop"""
        while self._running and not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check if we should process updates
                time_since_last_update = current_time - self._last_update_time
                
                if (time_since_last_update >= self.update_interval and 
                    current_time - self._last_render_time >= self.min_update_interval):
                    
                    # Process pending updates
                    if self._process_pending_updates():
                        self._last_update_time = current_time
                        self._last_render_time = current_time
                
                # Update animations
                self._update_animations(current_time)
                
                # Wait for next cycle
                sleep_time = min(self.update_interval, self.min_update_interval)
                self._stop_event.wait(sleep_time)
                
            except Exception as e:
                print(f"Error in OptimizedProgressUpdater loop: {e}")
                time.sleep(0.1)
    
    def _process_pending_updates(self) -> bool:
        """Process pending updates with debouncing"""
        with self._lock:
            if not self._pending_updates:
                return False
            
            current_time = time.time()
            
            # Get the most recent update (debouncing)
            latest_snapshot = self._pending_updates[-1]
            
            # Check debounce window
            time_since_snapshot = current_time - latest_snapshot.timestamp
            if time_since_snapshot < self.debounce_window and len(self._pending_updates) < 10:
                return False  # Wait for more updates or debounce window to pass
            
            # Clear pending updates
            debounced_count = len(self._pending_updates) - 1
            self._debounced_count += debounced_count
            self._pending_updates.clear()
            
            # Update target snapshot
            old_target = self._target_snapshot
            self._target_snapshot = latest_snapshot
            
            # Start animation if values changed significantly
            if self._should_animate(old_target, latest_snapshot):
                self._start_animation(old_target, latest_snapshot)
            else:
                # Direct update without animation
                self._current_snapshot = latest_snapshot
                self._notify_progress_callbacks()
            
            return True
    
    def _should_animate(self, old_snapshot: ProgressSnapshot, new_snapshot: ProgressSnapshot) -> bool:
        """Determine if animation should be used for the update"""
        # Animate if progress changed significantly
        progress_diff = abs(new_snapshot.progress_percentage - old_snapshot.progress_percentage)
        
        # Animate if more than 1% change or if it's a significant milestone
        return (progress_diff > 1.0 or 
                new_snapshot.progress_percentage in [25, 50, 75, 100] or
                new_snapshot.checked_codes - old_snapshot.checked_codes > 10)
    
    def _start_animation(self, start_snapshot: ProgressSnapshot, end_snapshot: ProgressSnapshot) -> None:
        """Start smooth animation between snapshots"""
        current_time = time.time()
        
        self._animation_start_time = current_time
        self._animation_start_snapshot = start_snapshot
        self._current_snapshot = start_snapshot
        self._is_animating = True
        self._animation_count += 1
    
    def _update_animations(self, current_time: float) -> None:
        """Update smooth animations"""
        if not self._is_animating or not self._animation_start_snapshot:
            return
        
        elapsed = current_time - self._animation_start_time
        progress = min(1.0, elapsed / self.animation_duration)
        
        if progress >= 1.0:
            # Animation complete
            self._current_snapshot = self._target_snapshot
            self._is_animating = False
            self._animation_start_snapshot = None
            self._notify_progress_callbacks()
            return
        
        # Smooth easing function (ease-out)
        eased_progress = 1 - (1 - progress) ** 3
        
        # Interpolate between start and target snapshots
        start = self._animation_start_snapshot
        target = self._target_snapshot
        
        interpolated_snapshot = ProgressSnapshot(
            timestamp=current_time,
            total_codes=target.total_codes,  # Don't interpolate counts
            checked_codes=int(start.checked_codes + (target.checked_codes - start.checked_codes) * eased_progress),
            statistics=self._interpolate_statistics(start.statistics, target.statistics, eased_progress),
            progress_percentage=start.progress_percentage + (target.progress_percentage - start.progress_percentage) * eased_progress,
            codes_per_second=start.codes_per_second + (target.codes_per_second - start.codes_per_second) * eased_progress
        )
        
        self._current_snapshot = interpolated_snapshot
        
        # Notify callbacks
        self._notify_progress_callbacks()
        self._notify_animation_callbacks(eased_progress)
    
    def _interpolate_statistics(self, start_stats: Dict[str, int], end_stats: Dict[str, int], progress: float) -> Dict[str, int]:
        """Interpolate between two statistics dictionaries"""
        result = {}
        
        # Get all keys from both dictionaries
        all_keys = set(start_stats.keys()) | set(end_stats.keys())
        
        for key in all_keys:
            start_val = start_stats.get(key, 0)
            end_val = end_stats.get(key, 0)
            interpolated = int(start_val + (end_val - start_val) * progress)
            result[key] = interpolated
        
        return result
    
    def _update_speed_calculation(self) -> None:
        """Update speed calculation with smoothing"""
        current_time = time.time()
        
        # Add current time to speed history
        self._speed_history.append(current_time)
        
        # Calculate speed based on recent history
        if len(self._speed_history) >= 2:
            time_window = self._speed_history[-1] - self._speed_history[0]
            if time_window > 0:
                codes_in_window = len(self._speed_history) - 1
                speed = codes_in_window / time_window
                
                # Update current snapshot if not animating
                if not self._is_animating:
                    self._current_snapshot.codes_per_second = speed
    
    def get_current_snapshot(self) -> ProgressSnapshot:
        """Get the current progress snapshot"""
        with self._lock:
            return self._current_snapshot
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            return {
                'total_updates': self._update_count,
                'debounced_updates': self._debounced_count,
                'animations_started': self._animation_count,
                'is_animating': self._is_animating,
                'pending_updates': len(self._pending_updates),
                'update_interval': self.update_interval,
                'debounce_window': self.debounce_window,
                'animation_duration': self.animation_duration,
                'speed_history_size': len(self._speed_history)
            }
    
    def set_update_interval(self, interval: float) -> None:
        """Set the update interval"""
        if interval > 0:
            self.update_interval = interval
    
    def set_debounce_window(self, window: float) -> None:
        """Set the debounce window"""
        if window > 0:
            self.debounce_window = window
    
    def set_animation_duration(self, duration: float) -> None:
        """Set the animation duration"""
        if duration > 0:
            self.animation_duration = duration
    
    def add_progress_callback(self, callback: Callable[[ProgressSnapshot], None]) -> None:
        """Add a progress update callback"""
        if callback not in self.progress_callbacks:
            self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[ProgressSnapshot], None]) -> None:
        """Remove a progress update callback"""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def add_animation_callback(self, callback: Callable[[float], None]) -> None:
        """Add an animation progress callback"""
        if callback not in self.animation_callbacks:
            self.animation_callbacks.append(callback)
    
    def remove_animation_callback(self, callback: Callable[[float], None]) -> None:
        """Remove an animation progress callback"""
        if callback in self.animation_callbacks:
            self.animation_callbacks.remove(callback)
    
    def _notify_progress_callbacks(self) -> None:
        """Notify all progress callbacks"""
        snapshot = self._current_snapshot
        
        for callback in self.progress_callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def _notify_animation_callbacks(self, progress: float) -> None:
        """Notify all animation callbacks"""
        for callback in self.animation_callbacks:
            try:
                callback(progress)
            except Exception as e:
                print(f"Error in animation callback: {e}")
    
    def force_update(self) -> None:
        """Force an immediate update of all pending changes"""
        with self._lock:
            self._process_pending_updates()
    
    def reset(self) -> None:
        """Reset the progress updater to initial state"""
        with self._lock:
            self._pending_updates.clear()
            self._speed_history.clear()
            self._is_animating = False
            self._animation_start_snapshot = None
            
            # Reset to initial snapshot
            self._current_snapshot = ProgressSnapshot(
                timestamp=time.time(),
                total_codes=0,
                checked_codes=0,
                statistics={},
                progress_percentage=0.0,
                codes_per_second=0.0
            )
            self._target_snapshot = self._current_snapshot
            
            # Reset counters
            self._update_count = 0
            self._debounced_count = 0
            self._animation_count = 0
    
    def is_running(self) -> bool:
        """Check if the updater is currently running"""
        return self._running
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()