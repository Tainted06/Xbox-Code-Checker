"""
RetryManager for handling API retry logic with exponential backoff
"""

import time
import random
import logging
from typing import Dict, Any, Optional, Callable, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..data.models import CodeStatus


class RetryReason(Enum):
    """Reasons for retry attempts"""
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    reason: RetryReason
    delay: float
    timestamp: datetime
    error_message: str = ""


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    base_delay: float = 1.0          # Base delay in seconds
    max_delay: float = 60.0          # Maximum delay in seconds
    backoff_factor: float = 2.0      # Exponential backoff multiplier
    max_attempts: int = 5            # Maximum number of retry attempts
    jitter_factor: float = 0.3       # Jitter factor (0.0 to 1.0)
    
    # Specific configurations for different error types
    rate_limit_base_delay: float = 2.0
    rate_limit_max_delay: float = 120.0
    rate_limit_max_attempts: int = 8
    
    network_error_base_delay: float = 0.5
    network_error_max_delay: float = 30.0
    network_error_max_attempts: int = 3
    
    server_error_base_delay: float = 1.0
    server_error_max_delay: float = 60.0
    server_error_max_attempts: int = 4


class RetryManager:
    """Manages retry logic with exponential backoff and jitter"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize RetryManager
        
        Args:
            config: Retry configuration, uses default if None
        """
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
        
        # Track retry attempts per code
        self.retry_attempts: Dict[str, list[RetryAttempt]] = {}
        
        # Statistics
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.retry_stats_by_reason: Dict[RetryReason, int] = {
            reason: 0 for reason in RetryReason
        }
        
        # Circuit breaker state
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 10
        self.circuit_breaker_reset_time = None
        self.circuit_breaker_timeout = 300  # 5 minutes
    
    def should_retry(self, code: str, error: Exception, status_code: Optional[int] = None) -> bool:
        """
        Determine if a request should be retried
        
        Args:
            code: The code being processed
            error: The exception that occurred
            status_code: HTTP status code if applicable
            
        Returns:
            True if should retry, False otherwise
        """
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            self.logger.warning("Circuit breaker is open, not retrying")
            return False
        
        # Determine retry reason
        retry_reason = self._classify_error(error, status_code)
        
        # Get retry configuration for this error type
        max_attempts = self._get_max_attempts_for_reason(retry_reason)
        
        # Check if we've exceeded max attempts
        attempts = self.retry_attempts.get(code, [])
        if len(attempts) >= max_attempts:
            self.logger.info(f"Max retry attempts ({max_attempts}) reached for code {code}")
            return False
        
        # Some errors should not be retried
        if retry_reason == RetryReason.UNKNOWN_ERROR and status_code in [400, 401, 403, 404]:
            self.logger.info(f"Non-retryable error for code {code}: {status_code}")
            return False
        
        return True
    
    def calculate_delay(self, code: str, error: Exception, status_code: Optional[int] = None) -> float:
        """
        Calculate delay before next retry attempt
        
        Args:
            code: The code being processed
            error: The exception that occurred
            status_code: HTTP status code if applicable
            
        Returns:
            Delay in seconds
        """
        retry_reason = self._classify_error(error, status_code)
        attempts = self.retry_attempts.get(code, [])
        attempt_number = len(attempts)
        
        # Get base configuration for this error type
        base_delay, max_delay, backoff_factor = self._get_delay_config_for_reason(retry_reason)
        
        # Calculate exponential backoff
        delay = min(base_delay * (backoff_factor ** attempt_number), max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.config.jitter_factor * random.uniform(-1, 1)
        delay = max(0.1, delay + jitter)  # Ensure minimum delay
        
        # Special handling for rate limiting
        if retry_reason == RetryReason.RATE_LIMITED:
            # Extract retry-after header if available
            retry_after = self._extract_retry_after(error)
            if retry_after:
                delay = max(delay, retry_after)
        
        return delay
    
    def record_retry_attempt(self, code: str, error: Exception, delay: float, 
                           status_code: Optional[int] = None) -> None:
        """
        Record a retry attempt
        
        Args:
            code: The code being processed
            error: The exception that occurred
            delay: Delay before retry
            status_code: HTTP status code if applicable
        """
        retry_reason = self._classify_error(error, status_code)
        
        attempt = RetryAttempt(
            attempt_number=len(self.retry_attempts.get(code, [])) + 1,
            reason=retry_reason,
            delay=delay,
            timestamp=datetime.now(),
            error_message=str(error)
        )
        
        if code not in self.retry_attempts:
            self.retry_attempts[code] = []
        
        self.retry_attempts[code].append(attempt)
        
        # Update statistics
        self.total_retries += 1
        self.retry_stats_by_reason[retry_reason] += 1
        
        # Update circuit breaker
        self.circuit_breaker_failures += 1
        
        self.logger.info(
            f"Retry attempt {attempt.attempt_number} for code {code}: "
            f"{retry_reason.value} (delay: {delay:.2f}s)"
        )
    
    def record_retry_success(self, code: str) -> None:
        """
        Record a successful retry
        
        Args:
            code: The code that was successfully processed
        """
        if code in self.retry_attempts:
            self.successful_retries += 1
            self.logger.info(f"Retry successful for code {code} after {len(self.retry_attempts[code])} attempts")
            
            # Reset circuit breaker on success
            self.circuit_breaker_failures = max(0, self.circuit_breaker_failures - 1)
    
    def record_retry_failure(self, code: str) -> None:
        """
        Record a failed retry (max attempts reached)
        
        Args:
            code: The code that failed all retry attempts
        """
        if code in self.retry_attempts:
            self.failed_retries += 1
            self.logger.warning(f"All retry attempts failed for code {code}")
    
    def get_retry_attempts(self, code: str) -> list[RetryAttempt]:
        """
        Get retry attempts for a specific code
        
        Args:
            code: The code to get attempts for
            
        Returns:
            List of retry attempts
        """
        return self.retry_attempts.get(code, []).copy()
    
    def clear_retry_attempts(self, code: str) -> None:
        """
        Clear retry attempts for a specific code
        
        Args:
            code: The code to clear attempts for
        """
        if code in self.retry_attempts:
            del self.retry_attempts[code]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get retry statistics
        
        Returns:
            Dictionary with retry statistics
        """
        return {
            'total_retries': self.total_retries,
            'successful_retries': self.successful_retries,
            'failed_retries': self.failed_retries,
            'success_rate': (self.successful_retries / max(1, self.total_retries)) * 100,
            'retry_stats_by_reason': {
                reason.value: count for reason, count in self.retry_stats_by_reason.items()
            },
            'active_retry_codes': len(self.retry_attempts),
            'circuit_breaker_failures': self.circuit_breaker_failures,
            'circuit_breaker_open': self._is_circuit_breaker_open()
        }
    
    def reset_statistics(self) -> None:
        """Reset all statistics"""
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.retry_stats_by_reason = {reason: 0 for reason in RetryReason}
        self.retry_attempts.clear()
        self.circuit_breaker_failures = 0
        self.circuit_breaker_reset_time = None
    
    def _classify_error(self, error: Exception, status_code: Optional[int] = None) -> RetryReason:
        """
        Classify error to determine retry strategy
        
        Args:
            error: The exception that occurred
            status_code: HTTP status code if applicable
            
        Returns:
            RetryReason enum value
        """
        error_str = str(error).lower()
        
        # Check status code first
        if status_code:
            if status_code == 429:
                return RetryReason.RATE_LIMITED
            elif 500 <= status_code < 600:
                return RetryReason.SERVER_ERROR
            elif status_code in [502, 503, 504]:
                return RetryReason.SERVER_ERROR
        
        # Check error message
        if 'timeout' in error_str or 'timed out' in error_str:
            return RetryReason.TIMEOUT
        elif 'connection' in error_str or 'network' in error_str:
            return RetryReason.CONNECTION_ERROR
        elif 'rate limit' in error_str or 'too many requests' in error_str:
            return RetryReason.RATE_LIMITED
        elif 'server error' in error_str or 'internal server error' in error_str:
            return RetryReason.SERVER_ERROR
        
        # Check exception type
        if isinstance(error, (ConnectionError, OSError)):
            return RetryReason.CONNECTION_ERROR
        elif isinstance(error, TimeoutError):
            return RetryReason.TIMEOUT
        
        return RetryReason.UNKNOWN_ERROR
    
    def _get_max_attempts_for_reason(self, reason: RetryReason) -> int:
        """Get maximum attempts for specific retry reason"""
        if reason == RetryReason.RATE_LIMITED:
            return self.config.rate_limit_max_attempts
        elif reason in [RetryReason.NETWORK_ERROR, RetryReason.CONNECTION_ERROR]:
            return self.config.network_error_max_attempts
        elif reason == RetryReason.SERVER_ERROR:
            return self.config.server_error_max_attempts
        else:
            return self.config.max_attempts
    
    def _get_delay_config_for_reason(self, reason: RetryReason) -> tuple[float, float, float]:
        """Get delay configuration for specific retry reason"""
        if reason == RetryReason.RATE_LIMITED:
            return (
                self.config.rate_limit_base_delay,
                self.config.rate_limit_max_delay,
                self.config.backoff_factor
            )
        elif reason in [RetryReason.NETWORK_ERROR, RetryReason.CONNECTION_ERROR]:
            return (
                self.config.network_error_base_delay,
                self.config.network_error_max_delay,
                self.config.backoff_factor
            )
        elif reason == RetryReason.SERVER_ERROR:
            return (
                self.config.server_error_base_delay,
                self.config.server_error_max_delay,
                self.config.backoff_factor
            )
        else:
            return (
                self.config.base_delay,
                self.config.max_delay,
                self.config.backoff_factor
            )
    
    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """
        Extract retry-after value from error if available
        
        Args:
            error: The exception that occurred
            
        Returns:
            Retry-after delay in seconds, or None if not available
        """
        # This would be implemented based on the specific HTTP client being used
        # For now, return None as we don't have access to response headers
        return None
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.circuit_breaker_failures < self.circuit_breaker_threshold:
            return False
        
        # Check if reset time has passed
        if self.circuit_breaker_reset_time is None:
            self.circuit_breaker_reset_time = datetime.now() + timedelta(seconds=self.circuit_breaker_timeout)
            return True
        
        if datetime.now() >= self.circuit_breaker_reset_time:
            # Reset circuit breaker
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            self.logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker"""
        self.circuit_breaker_failures = 0
        self.circuit_breaker_reset_time = None
        self.logger.info("Circuit breaker manually reset")


class RetryableOperation:
    """Context manager for retryable operations"""
    
    def __init__(self, retry_manager: RetryManager, code: str, 
                 operation: Callable[[], Any], max_attempts: Optional[int] = None):
        """
        Initialize retryable operation
        
        Args:
            retry_manager: RetryManager instance
            code: Code being processed
            operation: Operation to retry
            max_attempts: Override max attempts for this operation
        """
        self.retry_manager = retry_manager
        self.code = code
        self.operation = operation
        self.max_attempts = max_attempts
        self.result = None
        self.last_error = None
    
    def execute(self) -> Any:
        """
        Execute the operation with retry logic
        
        Returns:
            Result of the operation
            
        Raises:
            Last exception if all retries failed
        """
        attempt = 0
        
        while True:
            try:
                self.result = self.operation()
                
                # Record success if this was a retry
                if attempt > 0:
                    self.retry_manager.record_retry_success(self.code)
                
                return self.result
                
            except Exception as error:
                self.last_error = error
                attempt += 1
                
                # Check if we should retry
                if not self.retry_manager.should_retry(self.code, error):
                    self.retry_manager.record_retry_failure(self.code)
                    raise error
                
                # Calculate delay and record attempt
                delay = self.retry_manager.calculate_delay(self.code, error)
                self.retry_manager.record_retry_attempt(self.code, error, delay)
                
                # Wait before retry
                time.sleep(delay)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass