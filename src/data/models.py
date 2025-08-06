"""
Data models for Xbox Code Checker GUI
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import json


class FileSizeError(Exception):
    """Exception raised when file size exceeds limits"""
    def __init__(self, filepath: str, file_size: int, max_size: int):
        self.filepath = filepath
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format user-friendly error message"""
        file_size_mb = self.file_size / (1024 * 1024)
        max_size_mb = self.max_size / (1024 * 1024)
        return (f"Файл '{self.filepath}' слишком большой ({file_size_mb:.1f} МБ). "
                f"Максимальный размер: {max_size_mb:.1f} МБ")
    
    def get_size_info(self) -> Dict[str, Any]:
        """Get detailed size information"""
        return {
            'filepath': self.filepath,
            'file_size_bytes': self.file_size,
            'file_size_mb': round(self.file_size / (1024 * 1024), 2),
            'max_size_bytes': self.max_size,
            'max_size_mb': round(self.max_size / (1024 * 1024), 2),
            'excess_bytes': self.file_size - self.max_size,
            'excess_mb': round((self.file_size - self.max_size) / (1024 * 1024), 2)
        }


class CodeStatus(Enum):
    """Enumeration for code checking status"""
    PENDING = 'pending'
    VALID = 'valid'
    USED = 'used'
    INVALID = 'invalid'
    EXPIRED = 'expired'
    RATE_LIMITED = 'rate_limited'
    ERROR = 'error'
    SKIPPED = 'skipped'
    WLID_TOKEN_ERROR = 'wlid_token_error'  # Ошибка WLID токена, не кода


class SessionStatus(Enum):
    """Status of a checking session"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class CodeResult:
    """Result of a single code check"""
    code: str
    status: CodeStatus
    timestamp: datetime
    details: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'code': self.code,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'response_data': self.response_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeResult':
        """Create from dictionary"""
        return cls(
            code=data['code'],
            status=CodeStatus(data['status']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            details=data.get('details'),
            response_data=data.get('response_data')
        )


@dataclass
class AppConfig:
    """Application configuration"""
    theme: str = "dark"
    language: str = "ru"
    request_delay: float = 1.0
    max_threads: int = 5
    auto_save: bool = True
    export_format: str = "txt"
    window_width: int = 1000
    window_height: int = 700
    last_wlid_path: str = ""
    last_codes_path: str = ""
    last_export_path: str = ""
    max_file_size: int = 50 * 1024 * 1024  # 50MB default limit
    api_endpoint: str = "https://purchase.mp.microsoft.com/v7.0/tokenDescriptions/{code}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'theme': self.theme,
            'language': self.language,
            'request_delay': self.request_delay,
            'max_threads': self.max_threads,
            'auto_save': self.auto_save,
            'export_format': self.export_format,
            'window_width': self.window_width,
            'window_height': self.window_height,
            'last_wlid_path': self.last_wlid_path,
            'last_codes_path': self.last_codes_path,
            'last_export_path': self.last_export_path,
            'max_file_size': self.max_file_size,
            'api_endpoint': self.api_endpoint
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Create from dictionary"""
        return cls(**data)
    
    def save_to_file(self, filepath: str) -> None:
        """Save configuration to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'AppConfig':
        """Load configuration from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return cls()  # Return default config if file doesn't exist or is invalid


@dataclass
class CheckingSession:
    """A session of code checking"""
    codes: List[str] = field(default_factory=list)
    wlids: List[str] = field(default_factory=list)
    results: List[CodeResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.IDLE
    total_codes: int = 0
    checked_codes: int = 0
    valid_codes: int = 0
    used_codes: int = 0
    invalid_codes: int = 0
    error_codes: int = 0
    skipped_codes: int = 0
    
    def add_result(self, result: CodeResult) -> None:
        """Add a result and update statistics"""
        self.results.append(result)
        
        # Only count final results (not RATE_LIMITED, PENDING, or WLID_TOKEN_ERROR)
        if result.status not in [CodeStatus.RATE_LIMITED, CodeStatus.PENDING, CodeStatus.WLID_TOKEN_ERROR]:
            self.checked_codes += 1
            
            if result.status == CodeStatus.VALID:
                self.valid_codes += 1
            elif result.status == CodeStatus.USED:
                self.used_codes += 1
            elif result.status == CodeStatus.INVALID:
                self.invalid_codes += 1
            elif result.status == CodeStatus.ERROR:
                self.error_codes += 1
            elif result.status == CodeStatus.SKIPPED:
                self.skipped_codes += 1
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_codes == 0:
            return 0.0
        return (self.checked_codes / self.total_codes) * 100
    
    def get_statistics(self) -> Dict[str, int]:
        """Get session statistics"""
        return {
            'total': self.total_codes,
            'checked': self.checked_codes,
            'valid': self.valid_codes,
            'used': self.used_codes,
            'invalid': self.invalid_codes,
            'error': self.error_codes,
            'skipped': self.skipped_codes,
            'remaining': self.total_codes - self.checked_codes
        }
    
    def reset(self) -> None:
        """Reset session data"""
        self.results.clear()
        self.start_time = None
        self.end_time = None
        self.status = SessionStatus.IDLE
        self.checked_codes = 0
        self.valid_codes = 0
        self.used_codes = 0
        self.invalid_codes = 0
        self.error_codes = 0
        self.skipped_codes = 0


@dataclass
class WLIDToken:
    """WLID token with metadata"""
    token: str
    is_valid: bool = True
    last_used: Optional[datetime] = None
    error_count: int = 0
    rate_limited_until: Optional[datetime] = None  # Индивидуальный rate limit для токена
    
    def mark_error(self) -> None:
        """Mark token as having an error"""
        self.error_count += 1
        if self.error_count >= 3:
            self.is_valid = False
    
    def mark_used(self) -> None:
        """Mark token as recently used"""
        self.last_used = datetime.now()
    
    def mark_rate_limited(self, duration_seconds: int = 300) -> None:
        """Mark token as rate limited for specific duration"""
        from datetime import timedelta
        self.rate_limited_until = datetime.now() + timedelta(seconds=duration_seconds)
    
    def is_rate_limited(self) -> bool:
        """Check if token is currently rate limited"""
        if self.rate_limited_until is None:
            return False
        return datetime.now() < self.rate_limited_until
    
    def is_available(self) -> bool:
        """Check if token is available for use (valid and not rate limited)"""
        return self.is_valid and not self.is_rate_limited()
    
    def get_formatted_token(self) -> str:
        """Get properly formatted WLID token"""
        if self.token.startswith('WLID1.0='):
            return self.token
        else:
            return f'WLID1.0="{self.token}"'