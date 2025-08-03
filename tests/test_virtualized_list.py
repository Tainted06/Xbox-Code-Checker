"""
Tests for VirtualizedList component
"""

import unittest
from unittest.mock import Mock, patch
import tkinter as tk
import customtkinter as ctk
from datetime import datetime

from src.gui.components.virtualized_list import (
    VirtualizedList, 
    VirtualizedListDataSource, 
    CodeResultDataSource,
    ListItem
)
from src.data.models import CodeResult, CodeStatus


class MockDataSource(VirtualizedListDataSource):
    """Mock data source for testing"""
    
    def __init__(self, item_count: int = 100):
        self.item_count = item_count
        self.items = [f"Item {i}" for i in range(item_count)]
    
    def get_item_count(self) -> int:
        return self.item_count
    
    def get_item_data(self, index: int) -> str:
        if 0 <= index < len(self.items):
            return self.items[index]
        raise IndexError(f"Index {index} out of range")
    
    def get_item_height(self, index: int) -> int:
        return 25
    
    def format_item_text(self, index: int, data: str) -> str:
        return f"[{index:03d}] {data}"
    
    def get_item_color(self, index: int, data: str) -> str:
        return "white" if index % 2 == 0 else "#cccccc"


class TestVirtualizedListDataSource(unittest.TestCase):
    """Test cases for VirtualizedListDataSource implementations"""
    
    def test_mock_data_source(self):
        """Test mock data source"""
        data_source = MockDataSource(50)
        
        self.assertEqual(data_source.get_item_count(), 50)
        self.assertEqual(data_source.get_item_data(0), "Item 0")
        self.assertEqual(data_source.get_item_height(0), 25)
        self.assertEqual(data_source.format_item_text(0, "Item 0"), "[000] Item 0")
        self.assertEqual(data_source.get_item_color(0, "Item 0"), "white")
        self.assertEqual(data_source.get_item_color(1, "Item 1"), "#cccccc")
        
        with self.assertRaises(IndexError):
            data_source.get_item_data(100)
    
    def test_code_result_data_source(self):
        """Test CodeResultDataSource"""
        # Create test results
        results = [
            CodeResult(
                code="TEST001",
                status=CodeStatus.VALID,
                timestamp=datetime.now(),
                details="Test details"
            ),
            CodeResult(
                code="TEST002", 
                status=CodeStatus.ERROR,
                timestamp=datetime.now(),
                details="Error details"
            )
        ]
        
        data_source = CodeResultDataSource(results)
        
        self.assertEqual(data_source.get_item_count(), 2)
        self.assertEqual(data_source.get_item_data(0).code, "TEST001")
        self.assertEqual(data_source.get_item_height(0), 25)
        
        # Test formatting
        formatted = data_source.format_item_text(0, results[0])
        self.assertIn("TEST001", formatted)
        self.assertIn("VALID", formatted)
        
        # Test colors
        self.assertEqual(data_source.get_item_color(0, results[0]), "#00ff00")  # Valid = green
        self.assertEqual(data_source.get_item_color(1, results[1]), "#ff0000")  # Error = red
    
    def test_code_result_data_source_operations(self):
        """Test CodeResultDataSource operations"""
        data_source = CodeResultDataSource([])
        
        # Test empty
        self.assertEqual(data_source.get_item_count(), 0)
        
        # Add result
        result = CodeResult(
            code="TEST001",
            status=CodeStatus.VALID,
            timestamp=datetime.now()
        )
        data_source.add_result(result)
        
        self.assertEqual(data_source.get_item_count(), 1)
        self.assertEqual(data_source.get_item_data(0).code, "TEST001")
        
        # Update results
        new_results = [
            CodeResult(code="NEW001", status=CodeStatus.USED, timestamp=datetime.now()),
            CodeResult(code="NEW002", status=CodeStatus.INVALID, timestamp=datetime.now())
        ]
        data_source.update_results(new_results)
        
        self.assertEqual(data_source.get_item_count(), 2)
        self.assertEqual(data_source.get_item_data(0).code, "NEW001")
        
        # Clear results
        data_source.clear_results()
        self.assertEqual(data_source.get_item_count(), 0)


class TestVirtualizedListLogic(unittest.TestCase):
    """Test cases for VirtualizedList logic without GUI"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data_source = MockDataSource(100)
    
    def test_data_source_filtering_logic(self):
        """Test filtering logic without GUI"""
        # Test search filtering
        search_term = "Item 1"
        matching_indices = []
        
        for i in range(self.data_source.get_item_count()):
            data = self.data_source.get_item_data(i)
            text = self.data_source.format_item_text(i, data)
            if search_term.lower() in text.lower():
                matching_indices.append(i)
        
        # Should match items 1, 10-19, 100 (if exists)
        expected_matches = [1] + list(range(10, 20))
        if 100 < self.data_source.get_item_count():
            expected_matches.append(100)
        
        self.assertEqual(matching_indices, expected_matches)
    
    def test_scroll_position_calculation(self):
        """Test scroll position calculations"""
        total_items = 100
        visible_items = 10
        
        # Test max scroll position
        max_scroll = max(0, total_items - visible_items)
        self.assertEqual(max_scroll, 90)
        
        # Test clamping
        def clamp_scroll(position):
            return max(0, min(position, max_scroll))
        
        self.assertEqual(clamp_scroll(-5), 0)
        self.assertEqual(clamp_scroll(50), 50)
        self.assertEqual(clamp_scroll(100), 90)
    
    def test_visible_range_calculation(self):
        """Test visible range calculations"""
        scroll_position = 25
        visible_items = 10
        buffer_size = 2
        
        start_index = max(0, scroll_position - buffer_size)
        end_index = scroll_position + visible_items + buffer_size
        
        self.assertEqual(start_index, 23)
        self.assertEqual(end_index, 37)


class TestVirtualizedList(unittest.TestCase):
    """Test cases for VirtualizedList widget"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test data source
        self.data_source = MockDataSource(100)
        
        # Skip GUI tests if no display available
        try:
            # Create root window for testing
            self.root = ctk.CTk()
            self.root.withdraw()  # Hide window during tests
            
            # Create virtualized list
            self.vlist = VirtualizedList(
                parent=self.root,
                data_source=self.data_source,
                item_height=25,
                visible_items=10,
                buffer_size=2
            )
            self.gui_available = True
        except Exception as e:
            self.gui_available = False
            self.skipTest(f"GUI not available: {e}")
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'root'):
            try:
                self.root.destroy()
            except:
                pass
    
    def test_initialization(self):
        """Test virtualized list initialization"""
        self.assertEqual(self.vlist.data_source, self.data_source)
        self.assertEqual(self.vlist.item_height, 25)
        self.assertEqual(self.vlist.visible_items, 10)
        self.assertEqual(self.vlist.buffer_size, 2)
        self.assertEqual(self.vlist.scroll_position, 0)
        self.assertEqual(self.vlist.selected_index, -1)
    
    def test_filtered_indices_update(self):
        """Test updating filtered indices"""
        # Initially all items should be included
        self.vlist.update_filtered_indices()
        self.assertEqual(len(self.vlist.filtered_indices), 100)
        self.assertEqual(self.vlist.filtered_indices[:5], [0, 1, 2, 3, 4])
    
    def test_search_filtering(self):
        """Test search term filtering"""
        # Set search term
        self.vlist.set_search_term("Item 1")
        
        # Should match items containing "Item 1" (1, 10, 11, ..., 19, 100)
        expected_matches = [1] + list(range(10, 20)) + [100] if 100 < self.data_source.get_item_count() else [1] + list(range(10, 20))
        
        # Check that filtered indices contain expected items
        for expected in expected_matches[:10]:  # Check first 10 matches
            self.assertIn(expected, self.vlist.filtered_indices)
    
    def test_custom_filter_function(self):
        """Test custom filter function"""
        # Filter for even indices only
        def even_filter(data):
            # Extract index from data (format: "Item X")
            index = int(data.split()[1])
            return index % 2 == 0
        
        self.vlist.set_filter_function(even_filter)
        
        # Should only have even indices
        for index in self.vlist.filtered_indices[:10]:  # Check first 10
            item_data = self.data_source.get_item_data(index)
            item_index = int(item_data.split()[1])
            self.assertEqual(item_index % 2, 0)
    
    def test_scrolling(self):
        """Test scrolling functionality"""
        # Test scroll to position
        self.vlist.scroll_to(10)
        self.assertEqual(self.vlist.scroll_position, 10)
        
        # Test scroll by delta
        self.vlist.scroll_by(5)
        self.assertEqual(self.vlist.scroll_position, 15)
        
        # Test scroll bounds
        self.vlist.scroll_to(-5)  # Should clamp to 0
        self.assertEqual(self.vlist.scroll_position, 0)
        
        # Test scroll beyond end
        max_scroll = max(0, len(self.vlist.filtered_indices) - self.vlist.visible_items)
        self.vlist.scroll_to(max_scroll + 10)
        self.assertEqual(self.vlist.scroll_position, max_scroll)
    
    def test_item_selection(self):
        """Test item selection"""
        # Test select item
        self.vlist.select_item(5)
        self.assertEqual(self.vlist.selected_index, 5)
        
        # Test get selected data
        selected_data = self.vlist.get_selected_data()
        self.assertEqual(selected_data, "Item 5")
        
        # Test select invalid index
        self.vlist.select_item(-1)
        self.assertEqual(self.vlist.selected_index, 5)  # Should not change
        
        self.vlist.select_item(1000)
        self.assertEqual(self.vlist.selected_index, 5)  # Should not change
    
    def test_callbacks(self):
        """Test callback functionality"""
        selected_callback = Mock()
        double_click_callback = Mock()
        
        self.vlist.set_item_selected_callback(selected_callback)
        self.vlist.set_item_double_clicked_callback(double_click_callback)
        
        # Simulate item selection
        self.vlist.on_item_clicked_by_index(3)
        
        selected_callback.assert_called_once_with(3, "Item 3")
        
        # Simulate double click
        self.vlist.on_item_double_clicked_by_index(3)
        
        double_click_callback.assert_called_once_with(3, "Item 3")
    
    def test_performance_stats(self):
        """Test performance statistics"""
        stats = self.vlist.get_performance_stats()
        
        self.assertIn('render_count', stats)
        self.assertIn('last_render_time', stats)
        self.assertIn('rendered_items_count', stats)
        self.assertIn('total_items', stats)
        self.assertIn('filtered_items', stats)
        self.assertIn('visible_items', stats)
        self.assertIn('scroll_position', stats)
        
        self.assertEqual(stats['total_items'], 100)
        self.assertEqual(stats['visible_items'], 10)
        self.assertEqual(stats['scroll_position'], 0)
    
    def test_visible_range(self):
        """Test getting visible range"""
        start, end = self.vlist.get_visible_range()
        self.assertEqual(start, 0)
        self.assertEqual(end, 10)
        
        # Test after scrolling
        self.vlist.scroll_to(5)
        start, end = self.vlist.get_visible_range()
        self.assertEqual(start, 5)
        self.assertEqual(end, 15)
    
    def test_refresh(self):
        """Test refresh functionality"""
        # Change data source
        self.data_source.items[0] = "Modified Item 0"
        
        # Refresh should update display
        self.vlist.refresh()
        
        # Verify the change is reflected
        data = self.vlist.data_source.get_item_data(0)
        self.assertEqual(data, "Modified Item 0")
    
    def test_empty_data_source(self):
        """Test with empty data source"""
        empty_source = MockDataSource(0)
        empty_list = VirtualizedList(
            parent=self.root,
            data_source=empty_source,
            visible_items=10
        )
        
        self.assertEqual(len(empty_list.filtered_indices), 0)
        self.assertEqual(empty_list.get_selected_data(), None)
        
        stats = empty_list.get_performance_stats()
        self.assertEqual(stats['total_items'], 0)
        self.assertEqual(stats['filtered_items'], 0)
    
    def test_large_dataset_performance(self):
        """Test performance with large dataset"""
        # Create large data source
        large_source = MockDataSource(10000)
        large_list = VirtualizedList(
            parent=self.root,
            data_source=large_source,
            visible_items=20,
            buffer_size=5
        )
        
        # Should handle large dataset efficiently
        self.assertEqual(large_list.data_source.get_item_count(), 10000)
        
        # Rendered items should be limited to visible + buffer
        expected_max_rendered = 20 + (5 * 2)  # visible + buffer on both sides
        stats = large_list.get_performance_stats()
        self.assertLessEqual(stats['rendered_items_count'], expected_max_rendered)
        
        # Test scrolling through large dataset
        large_list.scroll_to(5000)
        self.assertEqual(large_list.scroll_position, 5000)
        
        # Should still have limited rendered items
        stats = large_list.get_performance_stats()
        self.assertLessEqual(stats['rendered_items_count'], expected_max_rendered)


if __name__ == '__main__':
    # Set up customtkinter for testing
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    unittest.main()