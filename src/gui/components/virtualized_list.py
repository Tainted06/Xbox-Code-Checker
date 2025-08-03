"""
VirtualizedList component for efficient display of large datasets
"""

import customtkinter as ctk
import tkinter as tk
from typing import List, Optional, Callable, Any, Tuple, Dict
from abc import ABC, abstractmethod
import time
from datetime import datetime

from ...data.models import CodeResult, CodeStatus


class ListItem:
    """Represents a single item in the virtualized list"""
    
    def __init__(self, index: int, data: Any, widget: Optional[ctk.CTkLabel] = None):
        self.index = index
        self.data = data
        self.widget = widget
        self.is_visible = False


class VirtualizedListDataSource(ABC):
    """Abstract base class for virtualized list data sources"""
    
    @abstractmethod
    def get_item_count(self) -> int:
        """Get total number of items"""
        pass
    
    @abstractmethod
    def get_item_data(self, index: int) -> Any:
        """Get data for item at index"""
        pass
    
    @abstractmethod
    def get_item_height(self, index: int) -> int:
        """Get height for item at index"""
        pass
    
    @abstractmethod
    def format_item_text(self, index: int, data: Any) -> str:
        """Format item data as display text"""
        pass
    
    @abstractmethod
    def get_item_color(self, index: int, data: Any) -> str:
        """Get background color for item"""
        pass


class CodeResultDataSource(VirtualizedListDataSource):
    """Data source for CodeResult objects"""
    
    def __init__(self, results: List[CodeResult]):
        self.results = results
        self.status_colors = {
            CodeStatus.VALID: "#00ff00",
            CodeStatus.USED: "#ffaa00", 
            CodeStatus.INVALID: "#ff0000",
            CodeStatus.EXPIRED: "#ff6600",
            CodeStatus.ERROR: "#ff0000",
            CodeStatus.SKIPPED: "#888888",
            CodeStatus.RATE_LIMITED: "#ffff00",
            CodeStatus.WLID_TOKEN_ERROR: "#ff4444",  # Светло-красный для проблем с токеном
            CodeStatus.PENDING: "#cccccc"
        }
    
    def get_item_count(self) -> int:
        return len(self.results)
    
    def get_item_data(self, index: int) -> CodeResult:
        if 0 <= index < len(self.results):
            return self.results[index]
        raise IndexError(f"Index {index} out of range")
    
    def get_item_height(self, index: int) -> int:
        return 25
    
    def format_item_text(self, index: int, data: CodeResult) -> str:
        timestamp = data.timestamp.strftime("%H:%M:%S")
        text = f"[{timestamp}] {data.code} - {data.status.value.upper()}"
        if data.details:
            text += f" ({data.details})"
        return text
    
    def get_item_color(self, index: int, data: CodeResult) -> str:
        return self.status_colors.get(data.status, "#ffffff")
    
    def add_result(self, result: CodeResult) -> None:
        """Add a new result to the data source"""
        self.results.append(result)
    
    def update_results(self, results: List[CodeResult]) -> None:
        """Update the entire results list"""
        self.results = results
    
    def clear_results(self) -> None:
        """Clear all results"""
        self.results.clear()


class VirtualizedList(ctk.CTkFrame):
    """Virtualized list widget for efficient display of large datasets"""
    
    def __init__(self, parent, data_source: VirtualizedListDataSource, 
                 item_height: int = 25, visible_items: int = 10, buffer_size: int = 2):
        super().__init__(parent)
        
        self.data_source = data_source
        self.item_height = item_height
        self.visible_items = visible_items
        self.buffer_size = buffer_size
        
        # State
        self.scroll_position = 0
        self.selected_index = -1
        self.filtered_indices: List[int] = []
        self.rendered_items: Dict[int, ListItem] = {}
        self.search_term = ""
        self.filter_function: Optional[Callable[[Any], bool]] = None
        
        # Performance tracking
        self.render_count = 0
        self.last_render_time = 0.0
        
        # Callbacks
        self.item_selected_callback: Optional[Callable[[int, Any], None]] = None
        self.item_double_clicked_callback: Optional[Callable[[int, Any], None]] = None
        
        # Create UI
        self.setup_ui()
        
        # Initialize filtered indices
        self.update_filtered_indices()
        
        # Initial render
        self.render_visible_items()
    
    def setup_ui(self) -> None:
        """Setup the user interface"""
        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True)
        
        # Create container for items
        self.items_container = ctk.CTkFrame(self.scrollable_frame)
        self.items_container.pack(fill="both", expand=True)
        
        # Bind scroll events
        self.scrollable_frame.bind("<MouseWheel>", self.on_mouse_wheel)
        self.bind("<Prior>", lambda e: self.scroll_by(-self.visible_items))  # Page Up
        self.bind("<Next>", lambda e: self.scroll_by(self.visible_items))    # Page Down
        self.bind("<Home>", lambda e: self.scroll_to(0))                     # Home
        self.bind("<End>", lambda e: self.scroll_to(len(self.filtered_indices)))  # End
        
        # Make widget focusable for keyboard events
        self.focus_set()
    
    def update_filtered_indices(self) -> None:
        """Update the list of filtered indices based on search term and filter function"""
        self.filtered_indices.clear()
        
        for i in range(self.data_source.get_item_count()):
            try:
                data = self.data_source.get_item_data(i)
                
                # Apply search filter
                if self.search_term:
                    text = self.data_source.format_item_text(i, data)
                    if self.search_term.lower() not in text.lower():
                        continue
                
                # Apply custom filter
                if self.filter_function and not self.filter_function(data):
                    continue
                
                self.filtered_indices.append(i)
                
            except IndexError:
                break
    
    def render_visible_items(self) -> None:
        """Render only the visible items plus buffer"""
        start_time = time.time()
        
        # Calculate visible range with buffer
        start_index = max(0, self.scroll_position - self.buffer_size)
        end_index = min(len(self.filtered_indices), 
                       self.scroll_position + self.visible_items + self.buffer_size)
        
        # Clear existing widgets that are out of range
        for index in list(self.rendered_items.keys()):
            if index < start_index or index >= end_index:
                item = self.rendered_items.pop(index)
                if item.widget:
                    item.widget.destroy()
        
        # Create widgets for visible items
        for i in range(start_index, end_index):
            if i not in self.rendered_items and i < len(self.filtered_indices):
                actual_index = self.filtered_indices[i]
                try:
                    data = self.data_source.get_item_data(actual_index)
                    self.create_item_widget(i, actual_index, data)
                except IndexError:
                    continue
        
        # Update performance stats
        self.render_count += 1
        self.last_render_time = time.time() - start_time
    
    def create_item_widget(self, display_index: int, actual_index: int, data: Any) -> None:
        """Create a widget for a single item"""
        # Create label widget
        text = self.data_source.format_item_text(actual_index, data)
        color = self.data_source.get_item_color(actual_index, data)
        
        widget = ctk.CTkLabel(
            self.items_container,
            text=text,
            height=self.item_height,
            anchor="w",
            fg_color=color if color != "#ffffff" else "transparent"
        )
        
        # Position widget
        widget.pack(fill="x", pady=1)
        
        # Bind click events
        widget.bind("<Button-1>", lambda e: self.on_item_clicked_by_index(actual_index))
        widget.bind("<Double-Button-1>", lambda e: self.on_item_double_clicked_by_index(actual_index))
        
        # Store item
        item = ListItem(actual_index, data, widget)
        item.is_visible = True
        self.rendered_items[display_index] = item
    
    def on_mouse_wheel(self, event) -> None:
        """Handle mouse wheel scrolling"""
        delta = -1 if event.delta > 0 else 1
        self.scroll_by(delta)
    
    def scroll_to(self, position: int) -> None:
        """Scroll to specific position"""
        max_scroll = max(0, len(self.filtered_indices) - self.visible_items)
        self.scroll_position = max(0, min(position, max_scroll))
        self.render_visible_items()
    
    def scroll_by(self, delta: int) -> None:
        """Scroll by delta amount"""
        self.scroll_to(self.scroll_position + delta)
    
    def on_item_clicked_by_index(self, index: int) -> None:
        """Handle item click by actual index"""
        if 0 <= index < self.data_source.get_item_count():
            self.selected_index = index
            data = self.data_source.get_item_data(index)
            
            if self.item_selected_callback:
                self.item_selected_callback(index, data)
    
    def on_item_double_clicked_by_index(self, index: int) -> None:
        """Handle item double click by actual index"""
        if 0 <= index < self.data_source.get_item_count():
            data = self.data_source.get_item_data(index)
            
            if self.item_double_clicked_callback:
                self.item_double_clicked_callback(index, data)
    
    def select_item(self, index: int) -> None:
        """Select item by index"""
        if 0 <= index < self.data_source.get_item_count():
            self.selected_index = index
    
    def get_selected_data(self) -> Optional[Any]:
        """Get data for selected item"""
        if 0 <= self.selected_index < self.data_source.get_item_count():
            try:
                return self.data_source.get_item_data(self.selected_index)
            except IndexError:
                pass
        return None
    
    def set_search_term(self, search_term: str) -> None:
        """Set search term for filtering"""
        self.search_term = search_term
        self.update_filtered_indices()
        self.scroll_to(0)  # Reset scroll position
        self.render_visible_items()
    
    def set_filter_function(self, filter_func: Optional[Callable[[Any], bool]]) -> None:
        """Set custom filter function"""
        self.filter_function = filter_func
        self.update_filtered_indices()
        self.scroll_to(0)  # Reset scroll position
        self.render_visible_items()
    
    def set_item_selected_callback(self, callback: Callable[[int, Any], None]) -> None:
        """Set callback for item selection"""
        self.item_selected_callback = callback
    
    def set_item_double_clicked_callback(self, callback: Callable[[int, Any], None]) -> None:
        """Set callback for item double click"""
        self.item_double_clicked_callback = callback
    
    def refresh(self) -> None:
        """Refresh the display"""
        self.update_filtered_indices()
        self.render_visible_items()
    
    def get_visible_range(self) -> Tuple[int, int]:
        """Get the range of visible items"""
        start = self.scroll_position
        end = min(len(self.filtered_indices), start + self.visible_items)
        return start, end
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'render_count': self.render_count,
            'last_render_time': self.last_render_time,
            'rendered_items_count': len(self.rendered_items),
            'total_items': self.data_source.get_item_count(),
            'filtered_items': len(self.filtered_indices),
            'visible_items': self.visible_items,
            'scroll_position': self.scroll_position
        }