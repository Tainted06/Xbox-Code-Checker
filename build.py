#!/usr/bin/env python3
"""
Build script for creating executable with PyInstaller
"""

import os
import sys
import subprocess
import shutil

def build_exe():
    """Build the executable using PyInstaller"""
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=XboxCodeChecker',
        '--icon=assets/icon.ico' if os.path.exists('assets/icon.ico') else '',
        '--add-data=assets;assets',
        '--hidden-import=customtkinter',
        '--hidden-import=PIL',
        'main.py'
    ]
    
    # Remove empty icon parameter if no icon exists
    cmd = [arg for arg in cmd if arg]
    
    try:
        subprocess.run(cmd, check=True)
        print("Build completed successfully!")
        print("Executable created in dist/XboxCodeChecker.exe")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe()