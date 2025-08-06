"""
Main application class for Xbox Code Checker GUI
"""

import customtkinter as ctk
import threading
import os
import logging
from typing import Optional

from .gui.main_window import MainWindow
from .data.models import AppConfig
from .data.file_manager import FileManager
from .utils.localization import localization_manager


class XboxCodeCheckerApp:
    """Main application class"""
    
    def __init__(self):
        # Setup basic logging
        self.setup_logging()
        
        # Load configuration
        self.config = AppConfig.load_from_file("config.json")

        # Setup localization
        localization_manager.set_language(self.config.language)

        # Initialize CustomTkinter
        ctk.set_appearance_mode("dark")  # Default to dark mode
        ctk.set_default_color_theme("blue")
        
        # Apply theme from config
        ctk.set_appearance_mode(self.config.theme)
        
        # Initialize file manager
        self.file_manager = FileManager()
        
        # Create main window
        self.root = ctk.CTk()
        self.main_window: Optional[MainWindow] = None
        
        # Setup window
        self.setup_window()
        
        # Create main window
        self.main_window = MainWindow(self.root, self.config, self.file_manager)
        
        # Setup close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Log application start
        logging.info("Xbox Code Checker GUI started")
    
    def setup_logging(self) -> None:
        """Setup basic logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('app.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def setup_window(self) -> None:
        """Setup the main window properties"""
        self.root.title("Xbox Code Checker GUI - Проверка Xbox кодов")
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        
        # Set minimum size
        self.root.minsize(800, 600)
        
        # Center window on screen
        self.center_window()
        
        # Set icon if available
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass  # Ignore if icon can't be loaded
    
    def center_window(self) -> None:
        """Center the window on the screen"""
        self.root.update_idletasks()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position
        x = (screen_width - self.config.window_width) // 2
        y = (screen_height - self.config.window_height) // 2
        
        # Set position
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}+{x}+{y}")
    
    def on_closing(self) -> None:
        """Handle application closing"""
        try:
            # Save current window size
            self.config.window_width = self.root.winfo_width()
            self.config.window_height = self.root.winfo_height()
            
            # Save configuration
            self.config.save_to_file("config.json")
            
            # Cleanup main window
            if self.main_window:
                self.main_window.cleanup()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.root.destroy()
    
    def run(self) -> None:
        """Run the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Application error: {e}")
            self.on_closing()