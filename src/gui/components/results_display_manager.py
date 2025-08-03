"""
ResultsDisplayManager component for efficient results display with virtualization
"""

import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Optional, Callable, Any
import threading
from datetime import datetime

from ...data.models import CodeResult, CodeStatus
from .virtualized_list import VirtualizedList, CodeResultDataSource


class ResultsDisplayManager:
    """Manages the display of code checking results with virtualization and filtering"""
    
    def __init__(self, parent_frame: ctk.CTkFrame):
        self.parent_frame = parent_frame
        
        # Data
        self.all_results: List[CodeResult] = []
        self.filtered_results: Dict[str, List[CodeResult]] = {
            'all': [],
            'valid': [],
            'used': [],
            'invalid': [],
            'expired': [],
            'error': [],
            'skipped': []
        }
        
        # Thread safety
        self.results_lock = threading.Lock()
        
        # UI components
        self.results_tabview: Optional[ctk.CTkTabview] = None
        self.virtualized_lists: Dict[str, VirtualizedList] = {}
        self.data_sources: Dict[str, CodeResultDataSource] = {}
        self.search_entries: Dict[str, ctk.CTkEntry] = {}
        
        # Batch update settings
        self.batch_size = 100
        self.update_interval = 0.1  # 100ms
        self.pending_updates: List[CodeResult] = []
        self.update_timer: Optional[str] = None
        
        # Statistics
        self.stats = {
            'total': 0,
            'valid': 0,
            'used': 0,
            'invalid': 0,
            'expired': 0,
            'error': 0,
            'skipped': 0
        }
        
        # Callbacks
        self.result_selected_callback: Optional[Callable[[CodeResult], None]] = None
        self.result_double_clicked_callback: Optional[Callable[[CodeResult], None]] = None
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup the user interface"""
        # Create title
        title_label = ctk.CTkLabel(
            self.parent_frame,
            text="Результаты",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Create tabview for different result categories
        self.results_tabview = ctk.CTkTabview(self.parent_frame)
        self.results_tabview.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Tab configuration
        tab_configs = [
            ("Все", "all"),
            ("Рабочие", "valid"),
            ("Использованные", "used"),
            ("Неверные", "invalid"),
            ("Истекшие", "expired"),
            ("Ошибки", "error"),
            ("Пропущены", "skipped")
        ]
        
        # Create tabs with virtualized lists
        for tab_name, tab_key in tab_configs:
            # Add tab
            self.results_tabview.add(tab_name)
            tab = self.results_tabview.tab(tab_name)
            
            # Create search frame
            search_frame = ctk.CTkFrame(tab)
            search_frame.pack(fill="x", padx=5, pady=5)
            
            search_label = ctk.CTkLabel(search_frame, text="Поиск:")
            search_label.pack(side="left", padx=(10, 5))
            
            search_entry = ctk.CTkEntry(
                search_frame,
                placeholder_text="Введите код или детали..."
            )
            search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            search_entry.bind("<KeyRelease>", lambda e, key=tab_key: self.on_search_changed(key, e))
            self.search_entries[tab_key] = search_entry
            
            # Clear search button
            clear_button = ctk.CTkButton(
                search_frame,
                text="Очистить",
                width=80,
                command=lambda key=tab_key: self.clear_search(key)
            )
            clear_button.pack(side="right", padx=5)
            
            # Create data source and virtualized list
            data_source = CodeResultDataSource([])
            self.data_sources[tab_key] = data_source
            
            virtualized_list = VirtualizedList(
                parent=tab,
                data_source=data_source,
                item_height=25,
                visible_items=15,
                buffer_size=5
            )
            virtualized_list.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Set callbacks
            virtualized_list.set_item_selected_callback(
                lambda idx, data, key=tab_key: self.on_result_selected(data)
            )
            virtualized_list.set_item_double_clicked_callback(
                lambda idx, data, key=tab_key: self.on_result_double_clicked(data)
            )
            
            self.virtualized_lists[tab_key] = virtualized_list
    
    def add_result(self, result: CodeResult) -> None:
        """Add a single result with batched updates"""
        with self.results_lock:
            self.pending_updates.append(result)
            
            # Process batch if it's full or start timer for smaller batches
            if len(self.pending_updates) >= self.batch_size:
                self.process_pending_updates()
            elif self.update_timer is None:
                self.update_timer = self.parent_frame.after(
                    int(self.update_interval * 1000),
                    self.process_pending_updates
                )
    
    def add_results_batch(self, results: List[CodeResult]) -> None:
        """Add multiple results efficiently"""
        with self.results_lock:
            self.pending_updates.extend(results)
            self.process_pending_updates()
    
    def process_pending_updates(self) -> None:
        """Process all pending result updates"""
        with self.results_lock:
            if not self.pending_updates:
                return
            
            # Cancel existing timer
            if self.update_timer:
                self.parent_frame.after_cancel(self.update_timer)
                self.update_timer = None
            
            # Process all pending updates
            for result in self.pending_updates:
                self._add_result_internal(result)
            
            # Clear pending updates
            self.pending_updates.clear()
            
            # Update all displays
            self._update_all_displays()
    
    def _add_result_internal(self, result: CodeResult) -> None:
        """Internal method to add result to data structures"""
        # Skip intermediate statuses for display
        if result.status in [CodeStatus.RATE_LIMITED, CodeStatus.PENDING]:
            return
        
        # Add to all results
        self.all_results.append(result)
        self.filtered_results['all'].append(result)
        
        # Add to specific category
        status_key = result.status.value.lower()
        if status_key in self.filtered_results:
            self.filtered_results[status_key].append(result)
        
        # Update statistics
        self.stats['total'] += 1
        if status_key in self.stats:
            self.stats[status_key] += 1
    
    def _update_all_displays(self) -> None:
        """Update all virtualized list displays"""
        for tab_key, data_source in self.data_sources.items():
            # Update data source
            data_source.update_results(self.filtered_results[tab_key])
            
            # Refresh virtualized list
            if tab_key in self.virtualized_lists:
                self.virtualized_lists[tab_key].refresh()
    
    def clear_results(self) -> None:
        """Clear all results"""
        with self.results_lock:
            # Clear data
            self.all_results.clear()
            for key in self.filtered_results:
                self.filtered_results[key].clear()
            
            # Reset statistics
            for key in self.stats:
                self.stats[key] = 0
            
            # Clear pending updates
            self.pending_updates.clear()
            
            # Cancel timer
            if self.update_timer:
                self.parent_frame.after_cancel(self.update_timer)
                self.update_timer = None
            
            # Update displays
            self._update_all_displays()
    
    def on_search_changed(self, tab_key: str, event) -> None:
        """Handle search term changes"""
        search_term = self.search_entries[tab_key].get().strip()
        
        if tab_key in self.virtualized_lists:
            self.virtualized_lists[tab_key].set_search_term(search_term)
    
    def clear_search(self, tab_key: str) -> None:
        """Clear search for specific tab"""
        if tab_key in self.search_entries:
            self.search_entries[tab_key].delete(0, "end")
            
        if tab_key in self.virtualized_lists:
            self.virtualized_lists[tab_key].set_search_term("")
    
    def on_result_selected(self, result: CodeResult) -> None:
        """Handle result selection"""
        if self.result_selected_callback:
            self.result_selected_callback(result)
    
    def on_result_double_clicked(self, result: CodeResult) -> None:
        """Handle result double click"""
        if self.result_double_clicked_callback:
            self.result_double_clicked_callback(result)
    
    def set_result_selected_callback(self, callback: Callable[[CodeResult], None]) -> None:
        """Set callback for result selection"""
        self.result_selected_callback = callback
    
    def set_result_double_clicked_callback(self, callback: Callable[[CodeResult], None]) -> None:
        """Set callback for result double click"""
        self.result_double_clicked_callback = callback
    
    def get_statistics(self) -> Dict[str, int]:
        """Get current statistics"""
        with self.results_lock:
            return self.stats.copy()
    
    def get_results_by_status(self, status: CodeStatus) -> List[CodeResult]:
        """Get results filtered by status"""
        with self.results_lock:
            status_key = status.value.lower()
            return self.filtered_results.get(status_key, []).copy()
    
    def get_all_results(self) -> List[CodeResult]:
        """Get all results"""
        with self.results_lock:
            return self.all_results.copy()
    
    def export_visible_results(self, tab_key: str = "all") -> List[CodeResult]:
        """Export currently visible results from specific tab"""
        with self.results_lock:
            if tab_key in self.filtered_results:
                return self.filtered_results[tab_key].copy()
            return []
    
    def set_filter_for_tab(self, tab_key: str, filter_func: Callable[[CodeResult], bool]) -> None:
        """Set custom filter function for specific tab"""
        if tab_key in self.virtualized_lists:
            self.virtualized_lists[tab_key].set_filter_function(filter_func)
    
    def scroll_to_latest(self, tab_key: str = "all") -> None:
        """Scroll to the latest result in specified tab"""
        if tab_key in self.virtualized_lists:
            vlist = self.virtualized_lists[tab_key]
            item_count = vlist.data_source.get_item_count()
            if item_count > 0:
                vlist.scroll_to(max(0, item_count - vlist.visible_items))
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all virtualized lists"""
        stats = {}
        for tab_key, vlist in self.virtualized_lists.items():
            stats[tab_key] = vlist.get_performance_stats()
        
        # Add overall stats
        stats['overall'] = {
            'total_results': len(self.all_results),
            'pending_updates': len(self.pending_updates),
            'batch_size': self.batch_size,
            'update_interval': self.update_interval
        }
        
        return stats
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        with self.results_lock:
            # Cancel any pending timer
            if self.update_timer:
                self.parent_frame.after_cancel(self.update_timer)
                self.update_timer = None
            
            # Clear all data
            self.all_results.clear()
            for key in self.filtered_results:
                self.filtered_results[key].clear()
            self.pending_updates.clear()