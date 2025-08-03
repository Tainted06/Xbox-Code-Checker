"""
WLID Token Manager Dialog for Xbox Code Checker GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from ..data.models import WLIDToken
from ..core.code_checker import CodeChecker


class WLIDManagerDialog:
    """Dialog for managing WLID tokens"""
    
    def __init__(self, parent: ctk.CTk, code_checker: Optional[CodeChecker] = None, 
                 file_manager=None, file_input_handler=None):
        self.parent = parent
        self.code_checker = code_checker
        self.file_manager = file_manager
        self.file_input_handler = file_input_handler
        self.dialog: Optional[ctk.CTkToplevel] = None
        self.tokens_data: List[Dict[str, Any]] = []
        
        # GUI elements
        self.tokens_tree: Optional[ttk.Treeview] = None
        self.summary_frame: Optional[ctk.CTkFrame] = None
        self.buttons_frame: Optional[ctk.CTkFrame] = None
        
        # Callbacks
        self.tokens_updated_callback: Optional[Callable[[], None]] = None
        
        self.create_dialog()
    
    def create_dialog(self) -> None:
        """Create the WLID manager dialog"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Управление WLID токенами")
        self.dialog.geometry("900x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.center_dialog()
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create sections
        self.create_summary_section(main_frame)
        self.create_tokens_list_section(main_frame)
        self.create_buttons_section(main_frame)
        
        # Load initial data
        self.refresh_data()
    
    def center_dialog(self) -> None:
        """Center the dialog on parent window"""
        self.dialog.update_idletasks()
        
        # Get parent position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate dialog position
        dialog_width = 900
        dialog_height = 600
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def create_summary_section(self, parent: ctk.CTkFrame) -> None:
        """Create summary statistics section"""
        self.summary_frame = ctk.CTkFrame(parent)
        self.summary_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            self.summary_frame,
            text="Статистика WLID токенов",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Stats frame
        self.stats_frame = ctk.CTkFrame(self.summary_frame)
        self.stats_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Create stats labels (will be updated in refresh_data)
        self.stats_labels = {}
        stats_row = ctk.CTkFrame(self.stats_frame)
        stats_row.pack(fill="x", pady=5)
        
        stats_names = [
            ("total", "Всего"),
            ("valid", "Действительные"),
            ("invalid", "Недействительные"),
            ("rate_limited", "Заблокированы"),
            ("available", "Доступны")
        ]
        
        for i, (key, label) in enumerate(stats_names):
            stat_frame = ctk.CTkFrame(stats_row)
            stat_frame.pack(side="left", fill="x", expand=True, padx=2)
            
            ctk.CTkLabel(stat_frame, text=label, font=ctk.CTkFont(size=12)).pack(pady=2)
            self.stats_labels[key] = ctk.CTkLabel(
                stat_frame, 
                text="0", 
                font=ctk.CTkFont(size=14, weight="bold")
            )
            self.stats_labels[key].pack(pady=2)
    
    def create_tokens_list_section(self, parent: ctk.CTkFrame) -> None:
        """Create tokens list section"""
        list_frame = ctk.CTkFrame(parent)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Title
        title_label = ctk.CTkLabel(
            list_frame,
            text="Список WLID токенов",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Create treeview frame (using tkinter for better table support)
        tree_frame = tk.Frame(list_frame, bg="#212121")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Create treeview with scrollbars
        tree_scroll_frame = tk.Frame(tree_frame, bg="#212121")
        tree_scroll_frame.pack(fill="both", expand=True)
        
        # Vertical scrollbar
        v_scrollbar = tk.Scrollbar(tree_scroll_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        # Horizontal scrollbar
        h_scrollbar = tk.Scrollbar(tree_scroll_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Treeview
        self.tokens_tree = ttk.Treeview(
            tree_scroll_frame,
            columns=("status", "token", "errors", "last_used", "rate_limited"),
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Configure scrollbars
        v_scrollbar.config(command=self.tokens_tree.yview)
        h_scrollbar.config(command=self.tokens_tree.xview)
        
        # Define columns
        columns_config = [
            ("status", "Статус", 100),
            ("token", "Токен", 300),
            ("errors", "Ошибки", 80),
            ("last_used", "Последнее использование", 150),
            ("rate_limited", "Заблокирован до", 150)
        ]
        
        for col_id, heading, width in columns_config:
            self.tokens_tree.heading(col_id, text=heading)
            self.tokens_tree.column(col_id, width=width, minwidth=50)
        
        self.tokens_tree.pack(fill="both", expand=True)
        
        # Configure treeview style for dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                       background="#2b2b2b",
                       foreground="white",
                       fieldbackground="#2b2b2b",
                       borderwidth=0)
        style.configure("Treeview.Heading",
                       background="#1f1f1f",
                       foreground="white",
                       borderwidth=1)
        style.map("Treeview.Heading",
                 background=[('active', '#3f3f3f')])
        style.map("Treeview",
                 background=[('selected', '#0078d4')])
    
    def create_buttons_section(self, parent: ctk.CTkFrame) -> None:
        """Create buttons section"""
        self.buttons_frame = ctk.CTkFrame(parent)
        self.buttons_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # Left side buttons
        left_buttons = ctk.CTkFrame(self.buttons_frame)
        left_buttons.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        
        refresh_btn = ctk.CTkButton(
            left_buttons,
            text="Обновить",
            command=self.refresh_data,
            width=100
        )
        refresh_btn.pack(side="left", padx=5)
        
        remove_invalid_btn = ctk.CTkButton(
            left_buttons,
            text="Удалить недействительные",
            command=self.remove_invalid_tokens,
            width=180,
            fg_color="#cc4400",
            hover_color="#dd5500"
        )
        remove_invalid_btn.pack(side="left", padx=5)
        
        remove_selected_btn = ctk.CTkButton(
            left_buttons,
            text="Удалить выбранный",
            command=self.remove_selected_token,
            width=140,
            fg_color="#aa0000",
            hover_color="#cc0000"
        )
        remove_selected_btn.pack(side="left", padx=5)
        
        # Right side buttons
        right_buttons = ctk.CTkFrame(self.buttons_frame)
        right_buttons.pack(side="right", padx=(5, 10), pady=10)
        
        close_btn = ctk.CTkButton(
            right_buttons,
            text="Закрыть",
            command=self.close_dialog,
            width=100
        )
        close_btn.pack(side="right", padx=5)
    
    def refresh_data(self) -> None:
        """Refresh tokens data from code checker"""
        if not self.code_checker:
            return
        
        try:
            # Get tokens status
            tokens_status = self.code_checker.get_wlid_tokens_status()
            self.tokens_data = tokens_status['tokens']
            summary = tokens_status['summary']
            
            # Update summary statistics
            for key, value in summary.items():
                if key in self.stats_labels:
                    self.stats_labels[key].configure(text=str(value))
                    
                    # Color coding
                    if key == "invalid" and value > 0:
                        self.stats_labels[key].configure(text_color="#ff6666")
                    elif key == "available":
                        if value == 0:
                            self.stats_labels[key].configure(text_color="#ff6666")
                        else:
                            self.stats_labels[key].configure(text_color="#66ff66")
                    else:
                        self.stats_labels[key].configure(text_color="white")
            
            # Update tokens list
            self.update_tokens_list()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить данные: {str(e)}")
    
    def update_tokens_list(self) -> None:
        """Update the tokens list in treeview"""
        if not self.tokens_tree:
            return
        
        # Clear existing items
        for item in self.tokens_tree.get_children():
            self.tokens_tree.delete(item)
        
        # Add tokens
        for token_info in self.tokens_data:
            # Determine status
            if not token_info['is_valid']:
                status = "❌ Недействителен"
                status_color = "red"
            elif token_info['is_rate_limited']:
                status = "⏳ Заблокирован"
                status_color = "orange"
            elif token_info['is_available']:
                status = "✅ Доступен"
                status_color = "green"
            else:
                status = "⚠️ Неизвестно"
                status_color = "gray"
            
            # Format last used
            last_used = "Никогда"
            if token_info['last_used']:
                try:
                    last_used_dt = datetime.fromisoformat(token_info['last_used'])
                    last_used = last_used_dt.strftime("%H:%M:%S")
                except:
                    last_used = "Ошибка формата"
            
            # Format rate limited until
            rate_limited_until = ""
            if token_info['rate_limited_until']:
                try:
                    rate_limited_dt = datetime.fromisoformat(token_info['rate_limited_until'])
                    rate_limited_until = rate_limited_dt.strftime("%H:%M:%S")
                except:
                    rate_limited_until = "Ошибка формата"
            
            # Insert item
            item = self.tokens_tree.insert("", "end", values=(
                status,
                token_info['token_preview'],
                str(token_info['error_count']),
                last_used,
                rate_limited_until
            ))
            
            # Color coding based on status
            if not token_info['is_valid']:
                self.tokens_tree.set(item, "status", "❌ Недействителен")
            elif token_info['is_rate_limited']:
                self.tokens_tree.set(item, "status", "⏳ Заблокирован")
            elif token_info['is_available']:
                self.tokens_tree.set(item, "status", "✅ Доступен")
    
    def remove_invalid_tokens(self) -> None:
        """Remove all invalid tokens"""
        if not self.code_checker:
            return
        
        # Confirm action
        invalid_count = sum(1 for token in self.tokens_data if not token['is_valid'])
        if invalid_count == 0:
            messagebox.showinfo("Информация", "Нет недействительных токенов для удаления")
            return
        
        result = messagebox.askyesno(
            "Подтверждение",
            f"Удалить {invalid_count} недействительных токенов?\n\nЭто действие нельзя отменить."
        )
        
        if result:
            try:
                removed_count = self.code_checker.remove_invalid_tokens()
                
                # Ask if user wants to update the original file
                self._ask_update_wlid_file(removed_count)
                
                messagebox.showinfo("Успешно", f"Удалено {removed_count} недействительных токенов")
                self.refresh_data()
                
                # Notify parent about tokens update
                if self.tokens_updated_callback:
                    self.tokens_updated_callback()
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить токены: {str(e)}")
    
    def remove_selected_token(self) -> None:
        """Remove selected token"""
        if not self.code_checker or not self.tokens_tree:
            return
        
        # Get selected item
        selected_items = self.tokens_tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите токен для удаления")
            return
        
        # Get token index
        selected_item = selected_items[0]
        item_index = self.tokens_tree.index(selected_item)
        
        if 0 <= item_index < len(self.tokens_data):
            token_info = self.tokens_data[item_index]
            
            # Confirm action
            result = messagebox.askyesno(
                "Подтверждение",
                f"Удалить токен {token_info['token_preview']}?\n\nЭто действие нельзя отменить."
            )
            
            if result:
                try:
                    success = self.code_checker.remove_token_by_index(token_info['index'])
                    if success:
                        # Ask if user wants to update the original file
                        self._ask_update_wlid_file(1)
                        
                        messagebox.showinfo("Успешно", "Токен удален")
                        self.refresh_data()
                        
                        # Notify parent about tokens update
                        if self.tokens_updated_callback:
                            self.tokens_updated_callback()
                    else:
                        messagebox.showerror("Ошибка", "Не удалось удалить токен")
                        
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось удалить токен: {str(e)}")
    
    def _ask_update_wlid_file(self, removed_count: int) -> None:
        """Ask user if they want to update the original WLID file"""
        try:
            if not self.file_input_handler or not self.file_manager:
                return
            
            wlid_file_path = self.file_input_handler.get_wlid_file_path()
            
            if wlid_file_path:
                result = messagebox.askyesno(
                    "Обновить файл?",
                    f"Удалено {removed_count} токенов из памяти.\n\n"
                    f"Обновить исходный файл WLID токенов?\n"
                    f"Файл: {wlid_file_path}\n\n"
                    f"Будет создана резервная копия оригинального файла."
                )
                
                if result:
                    self._update_wlid_file(wlid_file_path)
                    
        except Exception as e:
            print(f"Ошибка при обновлении файла WLID: {e}")
    
    def _update_wlid_file(self, file_path: str) -> None:
        """Update the WLID file with current valid tokens"""
        try:
            if not self.code_checker or not self.file_manager:
                return
            
            # Get current valid tokens
            tokens_status = self.code_checker.get_wlid_tokens_status()
            valid_tokens = []
            
            for token_info in tokens_status['tokens']:
                if token_info['is_valid']:
                    from ..data.models import WLIDToken
                    valid_tokens.append(WLIDToken(token=token_info['full_token']))
            
            removed_count, backup_path = self.file_manager.update_wlid_file_remove_invalid(file_path, valid_tokens)
            
            messagebox.showinfo(
                "Файл обновлен",
                f"Файл WLID токенов обновлен!\n\n"
                f"Удалено из файла: {removed_count} токенов\n"
                f"Осталось: {len(valid_tokens)} токенов\n"
                f"Резервная копия: {backup_path}"
            )
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить файл: {str(e)}")
    
    def set_tokens_updated_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when tokens are updated"""
        self.tokens_updated_callback = callback
    
    def close_dialog(self) -> None:
        """Close the dialog"""
        if self.dialog:
            self.dialog.destroy()
    
    def show(self) -> None:
        """Show the dialog"""
        if self.dialog:
            self.dialog.deiconify()
            self.dialog.lift()
            self.dialog.focus()