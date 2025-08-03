"""
File Input Handler Component

Handles all file loading operations for the Xbox Code Checker GUI.
Extracted from MainWindow to follow single responsibility principle.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import List, Optional, Callable, Tuple
import os

from ...data.models import WLIDToken, AppConfig
from ...data.file_manager import FileManager


class FileInputHandler:
    """Handles file input operations and UI for loading WLID tokens and codes"""
    
    def __init__(self, parent_frame: ctk.CTkFrame, config: AppConfig, file_manager: FileManager):
        """
        Initialize FileInputHandler
        
        Args:
            parent_frame: Parent frame to contain the file input UI
            config: Application configuration
            file_manager: File manager instance for file operations
        """
        self.parent_frame = parent_frame
        self.config = config
        self.file_manager = file_manager
        
        # Data
        self.wlid_tokens: List[WLIDToken] = []
        self.codes: List[str] = []
        self.wlid_file_path: Optional[str] = None  # Путь к файлу с WLID токенами
        self.codes_file_path: Optional[str] = None  # Путь к файлу с кодами
        
        # Callbacks
        self.wlid_loaded_callback: Optional[Callable[[List[WLIDToken]], None]] = None
        self.codes_loaded_callback: Optional[Callable[[List[str]], None]] = None
        
        # UI elements
        self.file_frame: Optional[ctk.CTkFrame] = None
        self.wlid_button: Optional[ctk.CTkButton] = None
        self.codes_button: Optional[ctk.CTkButton] = None
        self.wlid_label: Optional[ctk.CTkLabel] = None
        self.codes_label: Optional[ctk.CTkLabel] = None
        
        # Create UI
        self.create_ui()
    
    def create_ui(self) -> None:
        """Create the file input user interface"""
        # Main file frame
        self.file_frame = ctk.CTkFrame(self.parent_frame)
        self.file_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Title
        title_label = ctk.CTkLabel(
            self.file_frame, 
            text="Загрузка файлов", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # WLID section
        self._create_wlid_section()
        
        # Codes section
        self._create_codes_section()
    
    def _create_wlid_section(self) -> None:
        """Create WLID file loading section"""
        wlid_frame = ctk.CTkFrame(self.file_frame)
        wlid_frame.pack(fill="x", padx=10, pady=5)
        
        self.wlid_button = ctk.CTkButton(
            wlid_frame,
            text="Загрузить WLID",
            command=self.load_wlid_file,
            width=140
        )
        self.wlid_button.pack(side="left", padx=10, pady=10)
        
        self.wlid_label = ctk.CTkLabel(
            wlid_frame,
            text="WLID файл не загружен",
            font=ctk.CTkFont(size=12)
        )
        self.wlid_label.pack(side="left", padx=10, pady=10)
    
    def _create_codes_section(self) -> None:
        """Create codes file loading section"""
        codes_frame = ctk.CTkFrame(self.file_frame)
        codes_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.codes_button = ctk.CTkButton(
            codes_frame,
            text="Загрузить коды",
            command=self.load_codes_file,
            width=140
        )
        self.codes_button.pack(side="left", padx=10, pady=10)
        
        self.codes_label = ctk.CTkLabel(
            codes_frame,
            text="Файл кодов не загружен",
            font=ctk.CTkFont(size=12)
        )
        self.codes_label.pack(side="left", padx=10, pady=10)
    
    def load_wlid_file(self) -> None:
        """Load WLID tokens from file with proper error handling and validation"""
        try:
            # Get file path from user
            file_path = self._get_wlid_file_path()
            if not file_path:
                return
            
            # Validate file exists and is readable
            if not self._validate_file_path(file_path):
                return
            
            # Load tokens using file manager
            tokens, errors = self.file_manager.read_wlid_file(file_path)
            
            # Handle loading errors
            if errors:
                self._show_file_errors("WLID файле", errors)
            
            # Process loaded tokens
            if tokens:
                self._handle_wlid_loaded(tokens, file_path)
            else:
                messagebox.showerror("Ошибка", "В файле не найдено валидных WLID токенов")
                
        except Exception as e:
            self._handle_file_error("WLID файл", e)
    
    def load_codes_file(self) -> None:
        """Load codes from file with proper error handling and validation"""
        try:
            # Get file path from user
            file_path = self._get_codes_file_path()
            if not file_path:
                return
            
            # Validate file exists and is readable
            if not self._validate_file_path(file_path):
                return
            
            # Load codes using file manager
            codes, errors = self.file_manager.read_codes_file(file_path)
            
            # Handle loading errors
            if errors:
                self._show_file_errors("файле кодов", errors)
            
            # Process loaded codes
            if codes:
                self._handle_codes_loaded(codes, file_path)
            else:
                messagebox.showerror("Ошибка", "В файле не найдено валидных кодов")
                
        except Exception as e:
            self._handle_file_error("файл кодов", e)
    
    def _get_wlid_file_path(self) -> Optional[str]:
        """Get WLID file path from user"""
        initial_dir = "input"
        if self.config.last_wlid_path:
            initial_dir = os.path.dirname(self.config.last_wlid_path)
        
        return filedialog.askopenfilename(
            title="Выберите файл WLID",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            initialdir=initial_dir
        )
    
    def _get_codes_file_path(self) -> Optional[str]:
        """Get codes file path from user"""
        initial_dir = "input"
        if self.config.last_codes_path:
            initial_dir = os.path.dirname(self.config.last_codes_path)
        
        return filedialog.askopenfilename(
            title="Выберите файл с кодами",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            initialdir=initial_dir
        )
    
    def _validate_file_path(self, file_path: str) -> bool:
        """Validate that file exists and is readable"""
        if not os.path.exists(file_path):
            messagebox.showerror("Ошибка", f"Файл не найден: {file_path}")
            return False
        
        if not os.path.isfile(file_path):
            messagebox.showerror("Ошибка", f"Указанный путь не является файлом: {file_path}")
            return False
        
        if not os.access(file_path, os.R_OK):
            messagebox.showerror("Ошибка", f"Нет прав на чтение файла: {file_path}")
            return False
        
        return True
    
    def _show_file_errors(self, file_type: str, errors: List[str]) -> None:
        """Show file parsing errors to user"""
        error_msg = f"Ошибки в {file_type}:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            error_msg += f"\n... и еще {len(errors) - 5} ошибок"
        messagebox.showwarning(f"Ошибки в {file_type}", error_msg)
    
    def _handle_wlid_loaded(self, tokens: List[WLIDToken], file_path: str) -> None:
        """Handle successfully loaded WLID tokens"""
        self.wlid_tokens = tokens
        self.wlid_file_path = file_path  # Сохраняем путь к файлу
        self.config.last_wlid_path = file_path
        self.wlid_label.configure(text=f"Загружено {len(tokens)} WLID токенов")
        
        # Notify callback if set
        if self.wlid_loaded_callback:
            self.wlid_loaded_callback(tokens)
    
    def _handle_codes_loaded(self, codes: List[str], file_path: str) -> None:
        """Handle successfully loaded codes"""
        self.codes = codes
        self.codes_file_path = file_path  # Сохраняем путь к файлу
        self.config.last_codes_path = file_path
        self.codes_label.configure(text=f"Загружено {len(codes)} кодов")
        
        # Notify callback if set
        if self.codes_loaded_callback:
            self.codes_loaded_callback(codes)
    
    def _handle_file_error(self, file_type: str, error: Exception) -> None:
        """Handle file loading errors"""
        error_msg = f"Не удалось загрузить {file_type}: {str(error)}"
        messagebox.showerror("Ошибка", error_msg)
    
    def set_wlid_loaded_callback(self, callback: Callable[[List[WLIDToken]], None]) -> None:
        """Set callback for when WLID tokens are loaded"""
        self.wlid_loaded_callback = callback
    
    def set_codes_loaded_callback(self, callback: Callable[[List[str]], None]) -> None:
        """Set callback for when codes are loaded"""
        self.codes_loaded_callback = callback
    
    def get_wlid_tokens(self) -> List[WLIDToken]:
        """Get currently loaded WLID tokens"""
        return self.wlid_tokens.copy()
    
    def get_codes(self) -> List[str]:
        """Get currently loaded codes"""
        return self.codes.copy()
    
    def has_wlid_tokens(self) -> bool:
        """Check if WLID tokens are loaded"""
        return len(self.wlid_tokens) > 0
    
    def has_codes(self) -> bool:
        """Check if codes are loaded"""
        return len(self.codes) > 0
    
    def get_wlid_file_path(self) -> Optional[str]:
        """Get path to loaded WLID file"""
        return self.wlid_file_path
    
    def get_codes_file_path(self) -> Optional[str]:
        """Get path to loaded codes file"""
        return self.codes_file_path
    
    def clear_wlid_tokens(self) -> None:
        """Clear loaded WLID tokens"""
        self.wlid_tokens.clear()
        self.wlid_label.configure(text="WLID файл не загружен")
    
    def clear_codes(self) -> None:
        """Clear loaded codes"""
        self.codes.clear()
        self.codes_label.configure(text="Файл кодов не загружен")
    
    def clear_all(self) -> None:
        """Clear all loaded data"""
        self.clear_wlid_tokens()
        self.clear_codes()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable file input controls"""
        state = "normal" if enabled else "disabled"
        if self.wlid_button:
            self.wlid_button.configure(state=state)
        if self.codes_button:
            self.codes_button.configure(state=state)