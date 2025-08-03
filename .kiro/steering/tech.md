# Technology Stack

## Core Technologies

- **Python 3.9+**: Main programming language
- **CustomTkinter 5.2.0+**: Modern GUI framework for the desktop interface
- **Requests 2.31.0+**: HTTP client for API communication
- **Pillow 10.0.0+**: Image processing library
- **Packaging 23.0+**: Python packaging utilities

## Build System

- **PyInstaller**: Used for creating standalone executable files
- **Custom build script**: `build.py` handles the compilation process

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Run tests
python -m pytest tests/
```

### Building
```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# Build standalone executable
python build.py
```

The executable will be created in the `dist/` directory as `XboxCodeChecker.exe`.

## Configuration

- **config.json**: Main configuration file containing UI settings, API parameters, and user preferences
- **Logging**: Uses Python's built-in logging module, outputs to `app.log`
- **Theme Support**: Dark/light theme switching via CustomTkinter

## Architecture Patterns

- **MVC-like Structure**: Separation of GUI, core logic, and data layers
- **Threading**: Multi-threaded processing for non-blocking UI
- **Event-driven**: GUI events trigger core functionality
- **Configuration-driven**: Behavior controlled via JSON configuration