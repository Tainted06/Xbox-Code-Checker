#!/usr/bin/env python3
"""
Xbox Code Checker GUI
A modern GUI application for checking Xbox/Microsoft codes validity
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import XboxCodeCheckerApp

def main():
    """Main entry point for the application"""
    app = XboxCodeCheckerApp()
    app.run()

if __name__ == "__main__":
    main()