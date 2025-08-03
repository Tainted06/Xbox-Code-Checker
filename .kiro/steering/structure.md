# Project Structure

## Directory Organization

```
Xbox-Code-Checker/
├── src/                     # Main source code
│   ├── core/               # Core business logic
│   │   ├── code_checker.py    # Xbox code validation logic
│   │   ├── progress_manager.py # Progress tracking and updates
│   │   └── retry_manager.py   # Retry mechanism with exponential backoff
│   ├── data/               # Data layer and API communication
│   │   ├── api_client.py      # Microsoft API client
│   │   ├── file_manager.py    # File I/O operations
│   │   ├── models.py          # Data models and configuration
│   │   ├── browser_headers.py # HTTP headers for API requests
│   │   └── user_agents.py     # User agent strings
│   ├── gui/                # User interface components
│   │   ├── components/        # Reusable UI components
│   │   ├── main_window.py     # Primary application window
│   │   ├── results_viewer.py  # Results display interface
│   │   ├── settings_dialog.py # Configuration dialog
│   │   └── wlid_manager_dialog.py # WLID token management
│   └── app.py              # Main application class
├── assets/                 # Static resources (icons, images)
├── input/                  # Input files directory
│   ├── WLID.txt           # WLID tokens file
│   └── пример_*.txt       # Example files in Russian
├── output/                 # Generated output files
├── tests/                  # Unit and integration tests
├── main.py                 # Application entry point
├── build.py               # Build script for executable creation
├── config.json            # Application configuration
└── requirements.txt       # Python dependencies
```

## Module Responsibilities

### Core Layer (`src/core/`)
- **code_checker.py**: Handles the main Xbox code validation logic
- **progress_manager.py**: Manages progress tracking and UI updates
- **retry_manager.py**: Implements retry logic with exponential backoff

### Data Layer (`src/data/`)
- **api_client.py**: Manages communication with Microsoft's validation API
- **file_manager.py**: Handles file I/O operations for input/output
- **models.py**: Defines data structures and configuration classes
- **browser_headers.py** & **user_agents.py**: HTTP request configuration

### GUI Layer (`src/gui/`)
- **main_window.py**: Primary application interface
- **results_viewer.py**: Displays validation results
- **settings_dialog.py**: Configuration management interface
- **components/**: Reusable UI components

## File Naming Conventions

- **Snake_case**: Used for Python modules and functions
- **PascalCase**: Used for class names
- **Russian filenames**: Example files use Cyrillic characters (пример_*)
- **Descriptive names**: File names clearly indicate their purpose

## Import Structure

- Relative imports within the `src/` package
- Main entry point (`main.py`) adds project root to Python path
- Each module has `__init__.py` for proper package structure