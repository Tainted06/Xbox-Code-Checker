"""
Progress management for Xbox Code Checker GUI
"""

import threading
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, timedelta
import time

from ..data.models import CodeResult, CodeStatus, SessionStatus


class ProgressManager:
    """Manages progress tracking and notifications"""
    
    def __init__(self):
        # Separate locks for different data structures to reduce contention
        self.statistics_lock = threading.Lock()  # For all statistics counters
        self.callbacks_lock = threading.Lock()   # For callback lists
        self.status_lock = threading.Lock()      # For status and messages
        self.speed_lock = threading.Lock()       # For speed calculations
        
        # Progress tracking
        self.total_codes = 0
        self.checked_codes = 0
        self.start_time: Optional[datetime] = None
        self.last_update_time = time.time()
        
        # Statistics
        self.valid_count = 0
        self.used_count = 0
        self.invalid_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.expired_count = 0
        
        # Speed tracking
        self.codes_per_second = 0.0
        self.speed_history: List[float] = []
        self.last_speed_calculation = time.time()
        self.codes_since_last_speed = 0
        
        # Callbacks
        self.progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: List[Callable[[str], None]] = []
        
        # Status
        self.current_status = SessionStatus.IDLE
        self.status_message = "Ready"
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a progress update callback"""
        with self.callbacks_lock:
            self.progress_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[str], None]) -> None:
        """Add a status update callback"""
        with self.callbacks_lock:
            self.status_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a progress update callback"""
        with self.callbacks_lock:
            if callback in self.progress_callbacks:
                self.progress_callbacks.remove(callback)
    
    def remove_status_callback(self, callback: Callable[[str], None]) -> None:
        """Remove a status update callback"""
        with self.callbacks_lock:
            if callback in self.status_callbacks:
                self.status_callbacks.remove(callback)
    
    def start_session(self, total_codes: int) -> None:
        """Start a new progress tracking session"""
        # Update statistics atomically
        with self.statistics_lock:
            self.total_codes = total_codes
            self.checked_codes = 0
            self.start_time = datetime.now()
            self.last_update_time = time.time()
            
            # Reset statistics
            self.valid_count = 0
            self.used_count = 0
            self.invalid_count = 0
            self.error_count = 0
            self.skipped_count = 0
            self.expired_count = 0
        
        # Update speed tracking atomically
        with self.speed_lock:
            self.codes_per_second = 0.0
            self.speed_history.clear()
            self.last_speed_calculation = time.time()
            self.codes_since_last_speed = 0
        
        # Update status atomically
        with self.status_lock:
            self.current_status = SessionStatus.RUNNING
            self.status_message = f"Начинаем проверку {total_codes} кодов..."
        
        self._notify_status_callbacks()
        self._notify_progress_callbacks()
    
    def update_progress(self, result: CodeResult) -> None:
        """Update progress with a new result"""
        # Skip WLID_TOKEN_ERROR, RATE_LIMITED, and PENDING as they are not final results
        if result.status in [CodeStatus.WLID_TOKEN_ERROR, CodeStatus.RATE_LIMITED, CodeStatus.PENDING]:
            return
        
        # Update statistics atomically
        with self.statistics_lock:
            self.checked_codes += 1
            
            # Update statistics based on result status
            if result.status == CodeStatus.VALID:
                self.valid_count += 1
            elif result.status == CodeStatus.USED:
                self.used_count += 1
            elif result.status == CodeStatus.INVALID:
                self.invalid_count += 1
            elif result.status == CodeStatus.EXPIRED:
                self.expired_count += 1
            elif result.status == CodeStatus.ERROR:
                self.error_count += 1
            elif result.status == CodeStatus.SKIPPED:
                self.skipped_count += 1
            
            # Get current values for status update
            checked_codes = self.checked_codes
            total_codes = self.total_codes
            start_time = self.start_time
        
        # Update speed calculation atomically
        with self.speed_lock:
            self.codes_since_last_speed += 1
            self._update_speed()
        
        # Update status atomically
        with self.status_lock:
            progress_pct = (checked_codes / total_codes) * 100 if total_codes > 0 else 0
            self.status_message = f"Проверяем коды... {checked_codes}/{total_codes} ({progress_pct:.1f}%)"
            
            # Проверяем, завершена ли сессия
            if checked_codes >= total_codes:
                self.current_status = SessionStatus.COMPLETED
                elapsed = (datetime.now() - start_time).total_seconds() if start_time else 0
                self.status_message = f"Завершено! Проверено {checked_codes} кодов за {elapsed:.1f}с"
        
        self._notify_progress_callbacks()
        self._notify_status_callbacks()
    
    def _update_speed(self) -> None:
        """Update the codes per second calculation - must be called with speed_lock held"""
        current_time = time.time()
        time_since_last = current_time - self.last_speed_calculation
        
        # Update speed every 2 seconds or every 5 codes
        if time_since_last >= 2.0 or self.codes_since_last_speed >= 5:
            if time_since_last > 0:
                current_speed = self.codes_since_last_speed / time_since_last
                
                # Add to history (keep last 10 measurements)
                self.speed_history.append(current_speed)
                if len(self.speed_history) > 10:
                    self.speed_history.pop(0)
                
                # Calculate average speed
                self.codes_per_second = sum(self.speed_history) / len(self.speed_history)
            
            self.last_speed_calculation = current_time
            self.codes_since_last_speed = 0
    
    def pause_session(self) -> None:
        """Pause the current session"""
        with self.status_lock:
            if self.current_status == SessionStatus.RUNNING:
                self.current_status = SessionStatus.PAUSED
                self.status_message = "Приостановлено"
        
        self._notify_status_callbacks()
    
    def resume_session(self) -> None:
        """Resume the current session"""
        # Get current statistics
        with self.statistics_lock:
            checked_codes = self.checked_codes
            total_codes = self.total_codes
        
        # Update status
        with self.status_lock:
            if self.current_status == SessionStatus.PAUSED:
                self.current_status = SessionStatus.RUNNING
                progress_pct = (checked_codes / total_codes) * 100 if total_codes > 0 else 0
                self.status_message = f"Возобновлено... {checked_codes}/{total_codes} ({progress_pct:.1f}%)"
        
        self._notify_status_callbacks()
    
    def stop_session(self) -> None:
        """Stop the current session"""
        # Get current statistics
        with self.statistics_lock:
            checked_codes = self.checked_codes
            total_codes = self.total_codes
            start_time = self.start_time
        
        # Update status
        with self.status_lock:
            self.current_status = SessionStatus.STOPPED
            elapsed = (datetime.now() - start_time).total_seconds() if start_time else 0
            self.status_message = f"Остановлено. Проверено {checked_codes}/{total_codes} кодов за {elapsed:.1f}с"
        
        self._notify_status_callbacks()
        self._notify_progress_callbacks()
    
    def reset_session(self) -> None:
        """Reset the session to idle state"""
        # Reset statistics
        with self.statistics_lock:
            self.total_codes = 0
            self.checked_codes = 0
            self.start_time = None
            
            self.valid_count = 0
            self.used_count = 0
            self.invalid_count = 0
            self.error_count = 0
            self.skipped_count = 0
            self.expired_count = 0
        
        # Reset speed tracking
        with self.speed_lock:
            self.codes_per_second = 0.0
            self.speed_history.clear()
        
        # Reset status
        with self.status_lock:
            self.current_status = SessionStatus.IDLE
            self.status_message = "Готов"
        
        self._notify_status_callbacks()
        self._notify_progress_callbacks()
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information"""
        # Get statistics atomically
        with self.statistics_lock:
            total_codes = self.total_codes
            checked_codes = self.checked_codes
            valid_count = self.valid_count
            used_count = self.used_count
            invalid_count = self.invalid_count
            error_count = self.error_count
            skipped_count = self.skipped_count
            expired_count = self.expired_count
            start_time = self.start_time
        
        # Get speed information atomically
        with self.speed_lock:
            codes_per_second = self.codes_per_second
        
        # Get status information atomically
        with self.status_lock:
            current_status = self.current_status
            status_message = self.status_message
        
        progress_pct = (checked_codes / total_codes) * 100 if total_codes > 0 else 0
        
        info = {
            'total_codes': total_codes,
            'checked_codes': checked_codes,
            'remaining_codes': total_codes - checked_codes,
            'progress_percentage': progress_pct,
            'valid_count': valid_count,
            'used_count': used_count,
            'invalid_count': invalid_count,
            'error_count': error_count,
            'skipped_count': skipped_count,
            'expired_count': expired_count,
            'codes_per_second': codes_per_second,
            'status': current_status.value,
            'status_message': status_message
        }
        
        if start_time:
            elapsed = (datetime.now() - start_time).total_seconds()
            info['elapsed_time'] = elapsed
            
            # Estimate remaining time
            if codes_per_second > 0 and current_status == SessionStatus.RUNNING:
                remaining_codes = total_codes - checked_codes
                estimated_remaining = remaining_codes / codes_per_second
                info['estimated_remaining_time'] = estimated_remaining
                
                # Format time estimates
                info['elapsed_time_formatted'] = self._format_time(elapsed)
                info['estimated_remaining_formatted'] = self._format_time(estimated_remaining)
        
        return info
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def _notify_progress_callbacks(self) -> None:
        """Notify all progress callbacks"""
        progress_info = self.get_progress_info()
        
        # Create a copy of callbacks to avoid issues with concurrent modification
        with self.callbacks_lock:
            callbacks = self.progress_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                # Log error but don't stop other callbacks
                print(f"Error in progress callback: {e}")
    
    def _notify_status_callbacks(self) -> None:
        """Notify all status callbacks"""
        # Get current status message
        with self.status_lock:
            status_message = self.status_message
        
        # Create a copy of callbacks to avoid issues with concurrent modification
        with self.callbacks_lock:
            callbacks = self.status_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(status_message)
            except Exception as e:
                # Log error but don't stop other callbacks
                print(f"Error in status callback: {e}")
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """Get a summary of statistics"""
        # Get statistics atomically
        with self.statistics_lock:
            total_codes = self.total_codes
            checked_codes = self.checked_codes
            valid_count = self.valid_count
            used_count = self.used_count
            invalid_count = self.invalid_count
            error_count = self.error_count
            skipped_count = self.skipped_count
            expired_count = self.expired_count
        
        # Get speed atomically
        with self.speed_lock:
            codes_per_second = self.codes_per_second
        
        return {
            'total': total_codes,
            'checked': checked_codes,
            'valid': valid_count,
            'used': used_count,
            'invalid': invalid_count,
            'error': error_count,
            'skipped': skipped_count,
            'expired': expired_count,
            'success_rate': (valid_count / checked_codes * 100) if checked_codes > 0 else 0,
            'average_speed': codes_per_second
        }