"""
Progress Display Manager Component

Handles progress display and batched GUI updates for the Xbox Code Checker GUI.
Extracted from MainWindow to follow single responsibility principle.
Optimized with debouncing, smooth animations, and efficient statistics calculation.
"""

import customtkinter as ctk
import threading
from typing import Dict, Any, Optional, Callable
from collections import defaultdict
import time
import math

from ...data.models import CodeResult


class ProgressDisplayManager:
    """Manages progress display with optimized batched GUI updates to prevent UI blocking"""
    
    def __init__(self, parent_frame: ctk.CTkFrame, update_interval: float = 0.1):
        """
        Initialize ProgressDisplayManager
        
        Args:
            parent_frame: Parent frame to contain the progress UI
            update_interval: Interval in seconds for batched updates (default: 0.1s)
        """
        self.parent_frame = parent_frame
        self.update_interval = update_interval
        
        # Enhanced update batching with debouncing
        self._update_lock = threading.Lock()
        self._last_update_time = 0
        self._update_count = 0
        self._pending_update = False
        self._update_timer_id = None
        
        # Debouncing settings
        self.min_update_interval = 0.05  # Minimum 50ms between updates
        self.max_update_interval = 0.5   # Maximum 500ms without update
        self.batch_size = 20             # Update every N results
        
        # Progress data with thread safety
        self._total_codes = 0
        self._checked_codes = 0
        self._statistics = defaultdict(int)
        self._pending_statistics = defaultdict(int)
        self._wlid_token_error_count = 0
        
        # Animation state
        self._current_progress = 0.0
        self._target_progress = 0.0
        self._animation_step = 0.02  # 2% per animation frame
        self._animation_timer_id = None
        
        # Performance tracking
        self._update_frequency_tracker = []
        self._last_performance_check = time.time()
        
        # Callbacks
        self.progress_callbacks: list[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: list[Callable[[str], None]] = []
        
        # UI elements
        self.progress_frame: Optional[ctk.CTkFrame] = None
        self.progress_bar: Optional[ctk.CTkProgressBar] = None
        self.progress_label: Optional[ctk.CTkLabel] = None
        self.status_label: Optional[ctk.CTkLabel] = None
        self.stats_frame: Optional[ctk.CTkFrame] = None
        self.stats_labels: Dict[str, ctk.CTkLabel] = {}
        
        # Create UI
        self.create_ui()
    
    def create_ui(self) -> None:
        """Create the progress display user interface"""
        # Main progress frame
        self.progress_frame = ctk.CTkFrame(self.parent_frame)
        self.progress_frame.pack(fill="x", padx=10, pady=5)
        
        # Title
        title_label = ctk.CTkLabel(
            self.progress_frame,
            text="Прогресс",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=5)
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="0 / 0 кодов проверено (0.0%)",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(pady=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Готов",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=5)
        
        # Statistics frame
        self.stats_frame = ctk.CTkFrame(self.progress_frame)
        self.stats_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        # Create statistics labels
        self._create_stats_labels()
    
    def _create_stats_labels(self) -> None:
        """Create statistics labels with proper layout"""
        # First row - main statuses
        stats_row1 = [
            ('valid', 'Рабочие', '#00ff00'),
            ('used', 'Использованные', '#ffff00'),
            ('invalid', 'Неверные', '#ff8000'),
            ('expired', 'Истекшие', '#cccccc')
        ]
        
        for i, (key, label, color) in enumerate(stats_row1):
            stat_label = ctk.CTkLabel(
                self.stats_frame,
                text=f"{label}: 0",
                font=ctk.CTkFont(size=12),
                text_color=color
            )
            stat_label.grid(row=0, column=i, padx=10, pady=5, sticky="ew")
            self.stats_labels[key] = stat_label
        
        # Second row - problem statuses
        stats_row2 = [
            ('error', 'Ошибки', '#ff0000'),
            ('skipped', 'Пропущены', '#888888'),
            ('wlid_token_error', 'Проблемы с токенами', '#ff4444')
        ]
        
        for i, (key, label, color) in enumerate(stats_row2):
            stat_label = ctk.CTkLabel(
                self.stats_frame,
                text=f"{label}: 0",
                font=ctk.CTkFont(size=12),
                text_color=color
            )
            stat_label.grid(row=1, column=i, padx=10, pady=5, sticky="ew")
            self.stats_labels[key] = stat_label
        
        # Configure grid weights
        for i in range(4):  # 4 columns in first row
            self.stats_frame.grid_columnconfigure(i, weight=1)
        
        # Configure second row columns (3 columns now)
        for i in range(3):  # 3 columns in second row
            self.stats_frame.grid_columnconfigure(i, weight=1)
    
    def start_session(self, total_codes: int) -> None:
        """Start a new progress session"""
        with self._update_lock:
            self._total_codes = total_codes
            self._checked_codes = 0
            self._statistics.clear()
            self._pending_statistics.clear()
            self._wlid_token_error_count = 0
            
            # Reset animation state
            self._current_progress = 0.0
            self._target_progress = 0.0
            
            # Cancel any pending timers
            self._cancel_pending_timers()
            
            # Reset performance tracking
            self._update_frequency_tracker.clear()
            self._last_performance_check = time.time()
            
            # Reset UI immediately
            self._update_ui_immediate({
                'total_codes': total_codes,
                'checked_codes': 0,
                'progress_percentage': 0.0,
                'valid_count': 0,
                'used_count': 0,
                'invalid_count': 0,
                'expired_count': 0,
                'error_count': 0,
                'skipped_count': 0
            })
            
            # Notify callbacks
            self._notify_status_callbacks("Начинаем проверку...")
    
    def update_progress(self, result: CodeResult) -> None:
        """Update progress with a new result using optimized debounced batching"""
        with self._update_lock:
            # Update pending statistics (more efficient than immediate updates)
            status_key = result.status.value.lower()
            self._pending_statistics[status_key] += 1
            
            # Count WLID token errors separately (they don't count as final results)
            if result.status.value.upper() == 'WLID_TOKEN_ERROR':
                self._wlid_token_error_count += 1
            
            # Only count final results towards progress (not intermediate states)
            is_final_result = result.status.value.upper() not in ['RATE_LIMITED', 'PENDING', 'WLID_TOKEN_ERROR']
            if is_final_result:
                self._checked_codes += 1
            
            # Enhanced debounced batching
            self._update_count += 1
            current_time = time.time()
            time_since_last_update = current_time - self._last_update_time
            
            # Determine if we should update based on multiple criteria
            should_update_immediately = (
                self._update_count >= self.batch_size or  # Batch size reached
                time_since_last_update >= self.max_update_interval or  # Max interval exceeded
                self._checked_codes >= self._total_codes  # Session complete
            )
            
            should_schedule_update = (
                not self._pending_update and  # No update already scheduled
                time_since_last_update >= self.min_update_interval  # Minimum interval passed
            )
            
            if should_update_immediately:
                self._perform_debounced_update()
            elif should_schedule_update:
                self._schedule_debounced_update()
    
    def _prepare_progress_data(self) -> Dict[str, Any]:
        """Prepare progress data for UI update"""
        progress_percentage = (self._checked_codes / self._total_codes * 100) if self._total_codes > 0 else 0
        
        return {
            'total_codes': self._total_codes,
            'checked_codes': self._checked_codes,
            'progress_percentage': progress_percentage,
            'valid_count': self._statistics.get('valid', 0),
            'used_count': self._statistics.get('used', 0),
            'invalid_count': self._statistics.get('invalid', 0),
            'expired_count': self._statistics.get('expired', 0),
            'error_count': self._statistics.get('error', 0),
            'skipped_count': self._statistics.get('skipped', 0)
        }
    
    def _perform_debounced_update(self) -> None:
        """Perform debounced UI update - must be called with lock held"""
        # Cancel any pending update
        self._cancel_pending_timers()
        
        # Merge pending statistics into main statistics
        for key, count in self._pending_statistics.items():
            self._statistics[key] += count
        self._pending_statistics.clear()
        
        # Track update frequency for performance monitoring
        current_time = time.time()
        self._update_frequency_tracker.append(current_time)
        
        # Keep only recent updates for frequency calculation
        cutoff_time = current_time - 1.0  # Last 1 second
        self._update_frequency_tracker = [
            t for t in self._update_frequency_tracker if t > cutoff_time
        ]
        
        # Prepare update data
        progress_data = self._prepare_progress_data()
        
        # Update target progress for smooth animation
        self._target_progress = progress_data.get('progress_percentage', 0) / 100.0
        
        # Start smooth animation if needed
        if abs(self._target_progress - self._current_progress) > 0.001:
            self._start_progress_animation()
        
        # Update UI with current data
        self._update_ui_immediate(progress_data)
        
        # Notify progress callbacks
        self._notify_progress_callbacks(progress_data)
        
        # Reset counters
        self._update_count = 0
        self._last_update_time = current_time
        self._pending_update = False
    
    def _schedule_debounced_update(self) -> None:
        """Schedule a debounced update - must be called with lock held"""
        if not self._pending_update:
            self._pending_update = True
            # Schedule update after minimum interval
            delay_ms = int(self.update_interval * 1000)
            self._update_timer_id = self.parent_frame.after(delay_ms, self._execute_scheduled_update)
    
    def _execute_scheduled_update(self) -> None:
        """Execute a scheduled update (called by tkinter timer)"""
        with self._update_lock:
            if self._pending_update:  # Check if still needed
                self._perform_debounced_update()
    
    def _cancel_pending_timers(self) -> None:
        """Cancel any pending update or animation timers"""
        if self._update_timer_id:
            try:
                self.parent_frame.after_cancel(self._update_timer_id)
            except:
                pass  # Timer may have already executed
            self._update_timer_id = None
            self._pending_update = False
        
        if self._animation_timer_id:
            try:
                self.parent_frame.after_cancel(self._animation_timer_id)
            except:
                pass
            self._animation_timer_id = None
    
    def _start_progress_animation(self) -> None:
        """Start smooth progress bar animation"""
        if self._animation_timer_id is None:
            self._animate_progress_step()
    
    def _animate_progress_step(self) -> None:
        """Perform one step of progress bar animation"""
        if abs(self._target_progress - self._current_progress) < 0.001:
            # Animation complete
            self._current_progress = self._target_progress
            self._animation_timer_id = None
            return
        
        # Calculate smooth animation step
        progress_diff = self._target_progress - self._current_progress
        step_size = min(abs(progress_diff), self._animation_step)
        
        if progress_diff > 0:
            self._current_progress += step_size
        else:
            self._current_progress -= step_size
        
        # Update progress bar with animated value
        if self.progress_bar:
            self.progress_bar.set(self._current_progress)
        
        # Schedule next animation frame
        self._animation_timer_id = self.parent_frame.after(16, self._animate_progress_step)  # ~60 FPS
    
    def _update_ui_immediate(self, progress_data: Dict[str, Any]) -> None:
        """Update UI immediately with given progress data (optimized)"""
        try:
            # Update progress label (progress bar is handled by animation)
            if self.progress_label:
                progress_pct = progress_data.get('progress_percentage', 0)
                checked = progress_data.get('checked_codes', 0)
                total = progress_data.get('total_codes', 0)
                
                # Add rate information for better user feedback
                rate_info = self._calculate_processing_rate()
                rate_text = f" ({rate_info})" if rate_info else ""
                
                self.progress_label.configure(
                    text=f"{checked} / {total} кодов проверено ({progress_pct:.1f}%){rate_text}"
                )
            
            # Batch update statistics labels for better performance
            stat_updates = [
                ('valid', 'Рабочие', progress_data.get('valid_count', 0)),
                ('used', 'Использованные', progress_data.get('used_count', 0)),
                ('invalid', 'Неверные', progress_data.get('invalid_count', 0)),
                ('expired', 'Истекшие', progress_data.get('expired_count', 0)),
                ('error', 'Ошибки', progress_data.get('error_count', 0)),
                ('skipped', 'Пропущены', progress_data.get('skipped_count', 0)),
                ('wlid_token_error', 'Проблемы с токенами', self._wlid_token_error_count)
            ]
            
            # Only update labels that have changed to reduce UI overhead
            for key, label, count in stat_updates:
                if key in self.stats_labels:
                    new_text = f"{label}: {count}"
                    current_text = self.stats_labels[key].cget("text")
                    if current_text != new_text:
                        self.stats_labels[key].configure(text=new_text)
        
        except Exception as e:
            # Log error but don't crash the application
            print(f"Error updating progress UI: {e}")
    
    def _calculate_processing_rate(self) -> str:
        """Calculate and format current processing rate"""
        if len(self._update_frequency_tracker) < 2:
            return ""
        
        # Calculate rate based on recent updates
        current_time = time.time()
        recent_updates = [t for t in self._update_frequency_tracker if current_time - t <= 5.0]
        
        if len(recent_updates) < 2:
            return ""
        
        # Estimate codes per second based on update frequency and batch size
        time_span = recent_updates[-1] - recent_updates[0]
        if time_span > 0:
            updates_per_second = (len(recent_updates) - 1) / time_span
            estimated_codes_per_second = updates_per_second * (self.batch_size / 2)  # Rough estimate
            
            if estimated_codes_per_second >= 1:
                return f"{estimated_codes_per_second:.1f} кодов/сек"
            else:
                return f"{60 / estimated_codes_per_second:.0f} сек/код"
        
        return ""
    
    def update_status(self, status: str) -> None:
        """Update status display"""
        if self.status_label:
            self.status_label.configure(text=status)
        
        # Notify status callbacks
        self._notify_status_callbacks(status)
    
    def pause_session(self) -> None:
        """Pause the current session"""
        self.update_status("Приостановлено")
    
    def resume_session(self) -> None:
        """Resume the current session"""
        self.update_status("Продолжаем проверку...")
    
    def stop_session(self) -> None:
        """Stop the current session"""
        # Force final update and cleanup
        with self._update_lock:
            self._cancel_pending_timers()
            self._perform_debounced_update()
        
        self.update_status("Остановлено")
    
    def complete_session(self) -> None:
        """Mark session as completed"""
        # Perform final update and cleanup
        with self._update_lock:
            self._cancel_pending_timers()
            self._perform_debounced_update()
            
            # Ensure progress bar reaches 100%
            self._target_progress = 1.0
            self._current_progress = 1.0
            if self.progress_bar:
                self.progress_bar.set(1.0)
        
        self.update_status("Завершено")
    
    def get_statistics_summary(self) -> Dict[str, int]:
        """Get current statistics summary"""
        with self._update_lock:
            return {
                'total': self._total_codes,
                'checked': self._checked_codes,
                'valid': self._statistics.get('valid', 0),
                'used': self._statistics.get('used', 0),
                'invalid': self._statistics.get('invalid', 0),
                'expired': self._statistics.get('expired', 0),
                'error': self._statistics.get('error', 0),
                'skipped': self._statistics.get('skipped', 0)
            }
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a progress update callback"""
        if callback not in self.progress_callbacks:
            self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a progress update callback"""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def add_status_callback(self, callback: Callable[[str], None]) -> None:
        """Add a status update callback"""
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[str], None]) -> None:
        """Remove a status update callback"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_progress_callbacks(self, progress_data: Dict[str, Any]) -> None:
        """Notify all progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def _notify_status_callbacks(self, status: str) -> None:
        """Notify all status callbacks"""
        for callback in self.status_callbacks:
            try:
                callback(status)
            except Exception as e:
                print(f"Error in status callback: {e}")
    
    def set_update_interval(self, interval: float) -> None:
        """Set the update interval for batched updates"""
        if interval > 0:
            self.update_interval = interval
    
    def force_update(self) -> None:
        """Force an immediate update of all pending changes"""
        with self._update_lock:
            self._perform_debounced_update()
    
    def set_batch_size(self, batch_size: int) -> None:
        """Set the batch size for updates"""
        if batch_size > 0:
            self.batch_size = batch_size
    
    def set_animation_speed(self, step_size: float) -> None:
        """Set the animation step size (0.01 to 0.1)"""
        if 0.01 <= step_size <= 0.1:
            self._animation_step = step_size
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._update_lock:
            current_time = time.time()
            recent_updates = [t for t in self._update_frequency_tracker if current_time - t <= 5.0]
            
            update_frequency = 0.0
            if len(recent_updates) >= 2:
                time_span = recent_updates[-1] - recent_updates[0]
                if time_span > 0:
                    update_frequency = (len(recent_updates) - 1) / time_span
            
            return {
                'update_frequency': update_frequency,
                'pending_updates': len(self._pending_statistics),
                'batch_size': self.batch_size,
                'update_interval': self.update_interval,
                'animation_active': self._animation_timer_id is not None,
                'pending_timer': self._update_timer_id is not None,
                'current_progress': self._current_progress,
                'target_progress': self._target_progress
            }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        with self._update_lock:
            # Cancel all timers
            self._cancel_pending_timers()
            
            # Clear callbacks
            self.progress_callbacks.clear()
            self.status_callbacks.clear()
            
            # Clear tracking data
            self._update_frequency_tracker.clear()
            self._pending_statistics.clear()