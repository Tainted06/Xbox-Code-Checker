"""
Results viewer for Xbox Code Checker GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import threading

from ..data.models import CodeResult, CodeStatus


class ResultsViewer(ctk.CTkFrame):
    """Advanced results viewer with filtering and search"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Data
        self.all_results: List[CodeResult] = []
        self.filtered_results: List[CodeResult] = []
        self.current_filter = "all"
        self.search_term = ""
        
        # UI elements
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="all")
        
        # Callbacks
        self.on_result_selected: Optional[Callable[[CodeResult], None]] = None
        
        # Setup UI
        self.setup_ui()
        
        # Bind events
        self.search_var.trace("w", self.on_search_changed)
        self.filter_var.trace("w", self.on_filter_changed)
    
    def setup_ui(self) -> None:
        """Setup the user interface"""
        # Заголовок
        title_label = ctk.CTkLabel(
            self,
            text="Просмотр результатов",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Controls frame
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        # Search section
        search_frame = ctk.CTkFrame(controls_frame)
        search_frame.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        
        search_label = ctk.CTkLabel(search_frame, text="Поиск:")
        search_label.pack(side="left", padx=(10, 5))
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Поиск кодов или деталей..."
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Секция фильтра
        filter_frame = ctk.CTkFrame(controls_frame)
        filter_frame.pack(side="right", padx=(5, 10), pady=10)
        
        filter_label = ctk.CTkLabel(filter_frame, text="Фильтр:")
        filter_label.pack(side="left", padx=(10, 5))
        
        self.filter_combo = ctk.CTkComboBox(
            filter_frame,
            values=["all", "valid", "used", "invalid", "error", "skipped"],
            variable=self.filter_var,
            width=100
        )
        self.filter_combo.pack(side="left", padx=(0, 10))
        
        # Results display frame
        results_frame = ctk.CTkFrame(self)
        results_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Create tabview for different views
        self.tabview = ctk.CTkTabview(results_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Добавляем вкладки
        self.tabview.add("Список")
        self.tabview.add("Подробно")
        self.tabview.add("Статистика")
        
        # Setup each tab
        self.setup_list_view()
        self.setup_detailed_view()
        self.setup_statistics_view()
        
        # Информационная метка
        self.info_label = ctk.CTkLabel(
            results_frame,
            text="Нет результатов для отображения",
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        )
        self.info_label.pack(pady=5)
    
    def setup_list_view(self) -> None:
        """Настройка вкладки списка"""
        list_tab = self.tabview.tab("Список")
        
        # Create treeview for results
        tree_frame = ctk.CTkFrame(list_tab)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create treeview with tkinter (CustomTkinter doesn't have treeview)
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure treeview colors for dark theme
        style.configure("Treeview",
                       background="#2b2b2b",
                       foreground="white",
                       fieldbackground="#2b2b2b",
                       borderwidth=0)
        style.configure("Treeview.Heading",
                       background="#1f538d",
                       foreground="white",
                       borderwidth=1)
        style.map("Treeview.Heading",
                 background=[('active', '#14375e')])
        
        # Создаем treeview
        columns = ("Code", "Status", "Time", "Details")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Настраиваем колонки
        self.tree.heading("Code", text="Код")
        self.tree.heading("Status", text="Статус")
        self.tree.heading("Time", text="Время")
        self.tree.heading("Details", text="Детали")
        
        self.tree.column("Code", width=200, minwidth=150)
        self.tree.column("Status", width=80, minwidth=60)
        self.tree.column("Time", width=100, minwidth=80)
        self.tree.column("Details", width=300, minwidth=200)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_selection)
    
    def setup_detailed_view(self) -> None:
        """Настройка вкладки подробного просмотра"""
        detail_tab = self.tabview.tab("Подробно")
        
        # Создаем текстовый виджет для подробного просмотра
        self.detail_text = ctk.CTkTextbox(detail_tab)
        self.detail_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Изначально показываем текст-заглушку
        self.detail_text.insert("1.0", "Выберите результат из списка для просмотра деталей здесь.")
        self.detail_text.configure(state="disabled")
    
    def setup_statistics_view(self) -> None:
        """Настройка вкладки статистики"""
        stats_tab = self.tabview.tab("Статистика")
        
        # Create scrollable frame for statistics
        self.stats_scrollable = ctk.CTkScrollableFrame(stats_tab)
        self.stats_scrollable.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Statistics will be populated when results are updated
        self.stats_labels = {}
    
    def set_result_selected_callback(self, callback: Callable[[CodeResult], None]) -> None:
        """Set callback for when a result is selected"""
        self.on_result_selected = callback
    
    def update_results(self, results: List[CodeResult]) -> None:
        """Update the results display"""
        self.all_results = results.copy()
        self.apply_filters()
        self.update_statistics()
    
    def add_result(self, result: CodeResult) -> None:
        """Add a single result"""
        self.all_results.append(result)
        
        # Check if result matches current filters
        if self.matches_filters(result):
            self.filtered_results.append(result)
            self.add_result_to_tree(result)
        
        self.update_info_label()
        self.update_statistics()
    
    def clear_results(self) -> None:
        """Clear all results"""
        self.all_results.clear()
        self.filtered_results.clear()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Clear detailed view
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "No results to display.")
        self.detail_text.configure(state="disabled")
        
        self.update_info_label()
        self.update_statistics()
    
    def apply_filters(self) -> None:
        """Apply current filters to results"""
        self.filtered_results = [
            result for result in self.all_results
            if self.matches_filters(result)
        ]
        
        self.update_tree_display()
        self.update_info_label()
    
    def matches_filters(self, result: CodeResult) -> bool:
        """Check if result matches current filters"""
        # Status filter
        if self.current_filter != "all" and result.status.value != self.current_filter:
            return False
        
        # Search filter
        if self.search_term:
            search_lower = self.search_term.lower()
            if (search_lower not in result.code.lower() and
                search_lower not in (result.details or "").lower()):
                return False
        
        return True
    
    def update_tree_display(self) -> None:
        """Update the tree display with filtered results"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add filtered results
        for result in self.filtered_results:
            self.add_result_to_tree(result)
    
    def add_result_to_tree(self, result: CodeResult) -> None:
        """Add a single result to the tree"""
        # Format data
        code = result.code
        status = result.status.value.upper()
        time_str = result.timestamp.strftime("%H:%M:%S")
        details = result.details or ""
        
        # Truncate long details
        if len(details) > 50:
            details = details[:47] + "..."
        
        # Determine status color tag
        status_tag = f"status_{result.status.value}"
        
        # Insert item
        item = self.tree.insert("", "end", values=(code, status, time_str, details))
        
        # Apply color tags
        self.tree.set(item, "Status", status)
        
        # Configure tags for colors
        if not hasattr(self, 'tags_configured'):
            self.configure_tree_tags()
            self.tags_configured = True
        
        self.tree.item(item, tags=(status_tag,))
    
    def configure_tree_tags(self) -> None:
        """Configure color tags for tree items"""
        self.tree.tag_configure("status_valid", foreground="#00ff00")
        self.tree.tag_configure("status_used", foreground="#ffff00")
        self.tree.tag_configure("status_invalid", foreground="#ff8000")
        self.tree.tag_configure("status_error", foreground="#ff0000")
        self.tree.tag_configure("status_skipped", foreground="#888888")
    
    def update_info_label(self) -> None:
        """Update the info label"""
        total = len(self.all_results)
        filtered = len(self.filtered_results)
        
        if total == 0:
            self.info_label.configure(text="No results to display")
        elif filtered == total:
            self.info_label.configure(text=f"Showing {total} results")
        else:
            self.info_label.configure(text=f"Showing {filtered} of {total} results")
    
    def update_statistics(self) -> None:
        """Update the statistics view"""
        # Clear existing statistics
        for widget in self.stats_scrollable.winfo_children():
            widget.destroy()
        
        if not self.all_results:
            no_stats_label = ctk.CTkLabel(
                self.stats_scrollable,
                text="No statistics available",
                font=ctk.CTkFont(size=14)
            )
            no_stats_label.pack(pady=20)
            return
        
        # Calculate statistics
        stats = self.calculate_statistics()
        
        # Display statistics
        self.display_statistics(stats)
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from results"""
        total = len(self.all_results)
        if total == 0:
            return {}
        
        # Count by status
        status_counts = {
            CodeStatus.VALID: 0,
            CodeStatus.USED: 0,
            CodeStatus.INVALID: 0,
            CodeStatus.ERROR: 0,
            CodeStatus.SKIPPED: 0,
            CodeStatus.WLID_TOKEN_ERROR: 0
        }
        
        for result in self.all_results:
            if result.status in status_counts:
                status_counts[result.status] += 1
        
        # Calculate percentages
        status_percentages = {
            status: (count / total) * 100
            for status, count in status_counts.items()
        }
        
        # Time statistics
        if self.all_results:
            first_time = min(result.timestamp for result in self.all_results)
            last_time = max(result.timestamp for result in self.all_results)
            duration = (last_time - first_time).total_seconds()
        else:
            duration = 0
        
        return {
            'total': total,
            'status_counts': status_counts,
            'status_percentages': status_percentages,
            'duration': duration,
            'average_speed': total / duration if duration > 0 else 0
        }
    
    def display_statistics(self, stats: Dict[str, Any]) -> None:
        """Display statistics in the statistics tab"""
        # Overall statistics
        overall_frame = ctk.CTkFrame(self.stats_scrollable)
        overall_frame.pack(fill="x", padx=10, pady=10)
        
        overall_title = ctk.CTkLabel(
            overall_frame,
            text="Overall Statistics",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        overall_title.pack(pady=(10, 5))
        
        total_label = ctk.CTkLabel(
            overall_frame,
            text=f"Total Results: {stats['total']}",
            font=ctk.CTkFont(size=14)
        )
        total_label.pack(pady=2)
        
        if stats['duration'] > 0:
            duration_label = ctk.CTkLabel(
                overall_frame,
                text=f"Duration: {stats['duration']:.1f} seconds",
                font=ctk.CTkFont(size=14)
            )
            duration_label.pack(pady=2)
            
            speed_label = ctk.CTkLabel(
                overall_frame,
                text=f"Average Speed: {stats['average_speed']:.2f} codes/sec",
                font=ctk.CTkFont(size=14)
            )
            speed_label.pack(pady=(2, 10))
        
        # Status breakdown
        status_frame = ctk.CTkFrame(self.stats_scrollable)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        status_title = ctk.CTkLabel(
            status_frame,
            text="Status Breakdown",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        status_title.pack(pady=(10, 5))
        
        # Status details
        status_colors = {
            CodeStatus.VALID: "#00ff00",
            CodeStatus.USED: "#ffff00",
            CodeStatus.INVALID: "#ff8000",
            CodeStatus.ERROR: "#ff0000",
            CodeStatus.SKIPPED: "#888888",
            CodeStatus.WLID_TOKEN_ERROR: "#ff4444"
        }
        
        for status, count in stats['status_counts'].items():
            percentage = stats['status_percentages'][status]
            color = status_colors[status]
            
            status_label = ctk.CTkLabel(
                status_frame,
                text=f"{status.value.title()}: {count} ({percentage:.1f}%)",
                font=ctk.CTkFont(size=14),
                text_color=color
            )
            status_label.pack(pady=2)
        
        # Add some padding at the bottom
        ctk.CTkLabel(status_frame, text="").pack(pady=5)
    
    def on_search_changed(self, *args) -> None:
        """Handle search term change"""
        self.search_term = self.search_var.get()
        self.apply_filters()
    
    def on_filter_changed(self, *args) -> None:
        """Handle filter change"""
        self.current_filter = self.filter_var.get()
        self.apply_filters()
    
    def on_tree_selection(self, event) -> None:
        """Handle tree selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected item
        item = selection[0]
        values = self.tree.item(item, "values")
        
        if not values:
            return
        
        # Find the corresponding result
        code = values[0]
        selected_result = None
        
        for result in self.filtered_results:
            if result.code == code:
                selected_result = result
                break
        
        if selected_result:
            self.show_detailed_view(selected_result)
            
            # Call callback if set
            if self.on_result_selected:
                self.on_result_selected(selected_result)
    
    def show_detailed_view(self, result: CodeResult) -> None:
        """Show detailed view of a result"""
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        
        # Format detailed information
        details = f"Code: {result.code}\n"
        details += f"Status: {result.status.value.upper()}\n"
        details += f"Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if result.details:
            details += f"Details: {result.details}\n"
        
        if result.response_data:
            details += "\nAPI Response:\n"
            details += str(result.response_data)
        
        self.detail_text.insert("1.0", details)
        self.detail_text.configure(state="disabled")
        
        # Switch to detailed view tab
        self.tabview.set("Detailed View")
    
    def export_filtered_results(self) -> List[CodeResult]:
        """Export currently filtered results"""
        return self.filtered_results.copy()
    
    def get_selected_result(self) -> Optional[CodeResult]:
        """Get currently selected result"""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = selection[0]
        values = self.tree.item(item, "values")
        
        if not values:
            return None
        
        code = values[0]
        for result in self.filtered_results:
            if result.code == code:
                return result
        
        return None