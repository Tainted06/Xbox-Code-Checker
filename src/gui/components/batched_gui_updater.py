"""
Batched GUI Updater Component

Provides sophisticated batched GUI updates with priority levels and update coalescing
to optimize GUI performance and prevent UI blocking.
"""

import threading
import time
from typing import Dict, Any, Callable, Optional, List, Tuple
from enum import Enum
from collections import defaultdict, deque
from dataclasses import dataclass, field
import customtkinter as ctk


class UpdatePriority(Enum):
    """Priority levels for GUI updates"""
    LOW = 1      # Statistics, non-critical info
    NORMAL = 2   # Progress updates, status changes
    HIGH = 3     # User interactions, critical updates
    URGENT = 4   # Error messages, completion notifications


@dataclass
class UpdateRequest:
    """Represents a GUI update request"""
    update_id: str
    priority: UpdatePriority
    update_func: Callable[[], None]
    timestamp: float = field(default_factory=time.time)
    coalesce_key: Optional[str] = None  # Key for update coalescing
    data: Dict[str, Any] = field(default_factory=dict)


class BatchedGUIUpdater:
    """
    Manages batched GUI updates with configurable intervals, priority levels,
    and update coalescing to reduce redundant operations.
    """
    
    def __init__(self, 
                 update_interval: float = 0.1,
                 max_batch_size: int = 50,
                 coalesce_window: float = 0.05):
        """
        Initialize BatchedGUIUpdater
        
        Args:
            update_interval: Base interval between batch updates (seconds)
            max_batch_size: Maximum number of updates per batch
            coalesce_window: Time window for update coalescing (seconds)
        """
        self.update_interval = update_interval
        self.max_batch_size = max_batch_size
        self.coalesce_window = coalesce_window
        
        # Thread synchronization
        self._lock = threading.RLock()
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Update queues by priority
        self._update_queues: Dict[UpdatePriority, deque] = {
            priority: deque() for priority in UpdatePriority
        }
        
        # Coalescing support
        self._coalesce_map: Dict[str, UpdateRequest] = {}
        self._last_coalesce_cleanup = time.time()
        
        # Statistics
        self._stats = {
            'total_updates_requested': 0,
            'total_updates_processed': 0,
            'total_updates_coalesced': 0,
            'batches_processed': 0,
            'average_batch_size': 0.0,
            'last_batch_time': 0.0
        }
        
        # Performance tracking
        self._batch_times: deque = deque(maxlen=100)  # Keep last 100 batch times
        self._update_counts: deque = deque(maxlen=100)  # Keep last 100 batch sizes
        
        # Dynamic interval adjustment
        self._adaptive_interval = update_interval
        self._last_adjustment_time = time.time()
        self._high_load_threshold = 30  # Updates per batch
        self._low_load_threshold = 5   # Updates per batch
    
    def start(self) -> None:
        """Start the batched update processing"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._stop_event.clear()
            
            self._update_thread = threading.Thread(
                target=self._update_loop,
                name="BatchedGUIUpdater",
                daemon=True
            )
            self._update_thread.start()
    
    def stop(self) -> None:
        """Stop the batched update processing"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            self._stop_event.set()
            
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
            
            # Process any remaining updates
            self._process_remaining_updates()
    
    def queue_update(self, 
                    update_id: str,
                    update_func: Callable[[], None],
                    priority: UpdatePriority = UpdatePriority.NORMAL,
                    coalesce_key: Optional[str] = None,
                    data: Optional[Dict[str, Any]] = None) -> None:
        """
        Queue a GUI update for batched processing
        
        Args:
            update_id: Unique identifier for this update
            update_func: Function to call for the update
            priority: Priority level for the update
            coalesce_key: Optional key for update coalescing
            data: Optional data associated with the update
        """
        
        with self._lock:
            if not self._running:
                # If not running, execute immediately
                try:
                    update_func()
                except Exception as e:
                    print(f"Error executing immediate update {update_id}: {e}")
                return
            
            self._stats['total_updates_requested'] += 1
            
            update_request = UpdateRequest(
                update_id=update_id,
                priority=priority,
                update_func=update_func,
                coalesce_key=coalesce_key,
                data=data or {}
            )
            
            # Handle coalescing
            if coalesce_key:
                if coalesce_key in self._coalesce_map:
                    # Replace existing update with same coalesce key
                    old_request = self._coalesce_map[coalesce_key]
                    self._remove_from_queue(old_request)
                    self._stats['total_updates_coalesced'] += 1
                
                self._coalesce_map[coalesce_key] = update_request
            
            # Add to appropriate priority queue
            self._update_queues[priority].append(update_request)
    
    def queue_progress_update(self, progress_data: Dict[str, Any]) -> None:
        """Convenience method for progress updates with coalescing"""
        def update_func():
            # This will be implemented by the caller
            pass
        
        self.queue_update(
            update_id=f"progress_{time.time()}",
            update_func=update_func,
            priority=UpdatePriority.NORMAL,
            coalesce_key="progress_update",
            data=progress_data
        )
    
    def queue_status_update(self, status: str) -> None:
        """Convenience method for status updates with coalescing"""
        def update_func():
            # This will be implemented by the caller
            pass
        
        self.queue_update(
            update_id=f"status_{time.time()}",
            update_func=update_func,
            priority=UpdatePriority.NORMAL,
            coalesce_key="status_update",
            data={'status': status}
        )
    
    def queue_statistics_update(self, stats: Dict[str, Any]) -> None:
        """Convenience method for statistics updates with coalescing"""
        def update_func():
            # This will be implemented by the caller
            pass
        
        self.queue_update(
            update_id=f"stats_{time.time()}",
            update_func=update_func,
            priority=UpdatePriority.LOW,
            coalesce_key="statistics_update",
            data=stats
        )
    
    def queue_urgent_update(self, update_id: str, update_func: Callable[[], None]) -> None:
        """Convenience method for urgent updates (no coalescing)"""
        self.queue_update(
            update_id=update_id,
            update_func=update_func,
            priority=UpdatePriority.URGENT
        )
    
    def _update_loop(self) -> None:
        """Main update processing loop"""
        while self._running and not self._stop_event.is_set():
            try:
                batch_start_time = time.time()
                
                # Collect updates for this batch
                batch_updates = self._collect_batch_updates()
                
                if batch_updates:
                    # Process the batch
                    self._process_batch(batch_updates)
                    
                    # Update statistics
                    batch_time = time.time() - batch_start_time
                    self._update_performance_stats(len(batch_updates), batch_time)
                    
                    # Adjust interval based on load
                    self._adjust_update_interval(len(batch_updates))
                
                # Clean up old coalesce entries periodically
                if time.time() - self._last_coalesce_cleanup > 1.0:
                    self._cleanup_coalesce_map()
                
                # Wait for next update cycle
                self._stop_event.wait(self._adaptive_interval)
                
            except Exception as e:
                print(f"Error in BatchedGUIUpdater loop: {e}")
                # Continue running even if there's an error
                time.sleep(0.1)
    
    def _collect_batch_updates(self) -> List[UpdateRequest]:
        """Collect updates for the current batch"""
        batch_updates = []
        
        with self._lock:
            # Process by priority (highest first) - ensure we get all high priority items first
            for priority in sorted(UpdatePriority, key=lambda p: p.value, reverse=True):
                queue = self._update_queues[priority]
                
                # Take all items from this priority level (up to remaining batch size)
                while queue and len(batch_updates) < self.max_batch_size:
                    update_request = queue.popleft()
                    batch_updates.append(update_request)
                    
                    # Remove from coalesce map if present
                    if update_request.coalesce_key and update_request.coalesce_key in self._coalesce_map:
                        if self._coalesce_map[update_request.coalesce_key] == update_request:
                            del self._coalesce_map[update_request.coalesce_key]
                
                # If we've filled the batch, stop processing lower priorities
                if len(batch_updates) >= self.max_batch_size:
                    break
        
        return batch_updates
    
    def _process_batch(self, batch_updates: List[UpdateRequest]) -> None:
        """Process a batch of updates"""
        if not batch_updates:
            return
        
        # Sort by priority to maintain order (highest priority first)
        batch_updates.sort(key=lambda u: u.priority.value, reverse=True)
        
        # Group updates by coalesce key for efficient processing
        coalesced_updates = {}
        non_coalesced_updates = []
        
        for update in batch_updates:
            if update.coalesce_key:
                # For coalesced updates, keep only the most recent one
                if (update.coalesce_key not in coalesced_updates or 
                    update.timestamp > coalesced_updates[update.coalesce_key].timestamp):
                    coalesced_updates[update.coalesce_key] = update
            else:
                non_coalesced_updates.append(update)
        
        # Process coalesced updates first (by priority)
        coalesced_list = list(coalesced_updates.values())
        coalesced_list.sort(key=lambda u: u.priority.value, reverse=True)
        
        for update in coalesced_list:
            try:
                update.update_func()
                self._stats['total_updates_processed'] += 1
            except Exception as e:
                print(f"Error processing coalesced update {update.update_id}: {e}")
        
        # Process non-coalesced updates (already sorted by priority)
        for update in non_coalesced_updates:
            try:
                update.update_func()
                self._stats['total_updates_processed'] += 1
            except Exception as e:
                print(f"Error processing update {update.update_id}: {e}")
        
        self._stats['batches_processed'] += 1
    
    def _remove_from_queue(self, update_request: UpdateRequest) -> None:
        """Remove an update request from its queue"""
        queue = self._update_queues[update_request.priority]
        try:
            queue.remove(update_request)
        except ValueError:
            # Update not in queue (already processed or removed)
            pass
    
    def _cleanup_coalesce_map(self) -> None:
        """Clean up old entries from coalesce map"""
        current_time = time.time()
        
        with self._lock:
            expired_keys = [
                key for key, update in self._coalesce_map.items()
                if current_time - update.timestamp > self.coalesce_window * 10
            ]
            
            for key in expired_keys:
                del self._coalesce_map[key]
        
        self._last_coalesce_cleanup = current_time
    
    def _update_performance_stats(self, batch_size: int, batch_time: float) -> None:
        """Update performance statistics"""
        self._batch_times.append(batch_time)
        self._update_counts.append(batch_size)
        
        # Update averages
        if self._update_counts:
            self._stats['average_batch_size'] = sum(self._update_counts) / len(self._update_counts)
        
        self._stats['last_batch_time'] = batch_time
    
    def _adjust_update_interval(self, batch_size: int) -> None:
        """Dynamically adjust update interval based on load"""
        current_time = time.time()
        
        # Only adjust every few seconds to avoid oscillation
        if current_time - self._last_adjustment_time < 2.0:
            return
        
        if batch_size > self._high_load_threshold:
            # High load: increase interval to reduce frequency
            self._adaptive_interval = min(self._adaptive_interval * 1.2, self.update_interval * 3)
        elif batch_size < self._low_load_threshold:
            # Low load: decrease interval for more responsive updates
            self._adaptive_interval = max(self._adaptive_interval * 0.8, self.update_interval * 0.5)
        
        self._last_adjustment_time = current_time
    
    def _process_remaining_updates(self) -> None:
        """Process any remaining updates when stopping"""
        remaining_updates = []
        
        with self._lock:
            for priority in UpdatePriority:
                queue = self._update_queues[priority]
                while queue:
                    remaining_updates.append(queue.popleft())
        
        if remaining_updates:
            self._process_batch(remaining_updates)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        with self._lock:
            stats = self._stats.copy()
            
            # Add queue sizes
            stats['queue_sizes'] = {
                priority.name: len(queue) 
                for priority, queue in self._update_queues.items()
            }
            
            # Add performance metrics
            if self._batch_times:
                stats['average_batch_time'] = sum(self._batch_times) / len(self._batch_times)
                stats['max_batch_time'] = max(self._batch_times)
                stats['min_batch_time'] = min(self._batch_times)
            
            stats['adaptive_interval'] = self._adaptive_interval
            stats['coalesce_map_size'] = len(self._coalesce_map)
            
            return stats
    
    def set_update_interval(self, interval: float) -> None:
        """Set the base update interval"""
        if interval > 0:
            self.update_interval = interval
            self._adaptive_interval = interval
    
    def set_max_batch_size(self, size: int) -> None:
        """Set the maximum batch size"""
        if size > 0:
            self.max_batch_size = size
    
    def set_coalesce_window(self, window: float) -> None:
        """Set the coalescing time window"""
        if window > 0:
            self.coalesce_window = window
    
    def clear_queues(self) -> None:
        """Clear all pending updates"""
        with self._lock:
            for queue in self._update_queues.values():
                queue.clear()
            self._coalesce_map.clear()
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes by priority"""
        with self._lock:
            return {
                priority.name: len(queue)
                for priority, queue in self._update_queues.items()
            }
    
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