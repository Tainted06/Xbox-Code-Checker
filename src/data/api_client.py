"""
Microsoft API client for Xbox Code Checker GUI
"""

import requests
import json
import time
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import socket
from urllib3.exceptions import NewConnectionError, MaxRetryError

from .models import WLIDToken, CodeResult, CodeStatus
from .user_agents import get_compatible_user_agent
from .browser_headers import get_conservative_headers
from ..core.retry_manager import RetryManager, RetryConfig, RetryableOperation


class InvalidWLIDTokenError(Exception):
    """Exception raised when WLID token is invalid (401 Unauthorized)"""
    def __init__(self, token: 'WLIDToken', message: str = "WLID token is invalid"):
        self.token = token
        self.message = message
        super().__init__(self.message)


class APIClient:
    """Handles communication with Microsoft API with enhanced network error handling and retry logic"""
    
    def __init__(self, wlid_tokens: List[WLIDToken], request_delay: float = 1.0, 
                 connection_timeout: float = 10.0, read_timeout: float = 30.0,
                 retry_config: Optional[RetryConfig] = None):
        self.wlid_tokens = wlid_tokens
        self.request_delay = request_delay
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self.session = None
        self.last_request_time = 0
        self.rate_limit_until = None
        self._session_closed = False
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize retry manager with enhanced configuration
        self.retry_manager = RetryManager(retry_config or self._create_default_retry_config())
        
        # Network connectivity tracking
        self._last_connectivity_check = 0
        self._connectivity_check_interval = 30  # Check every 30 seconds
        self._is_connected = True
        
        # Circuit breaker for repeated failures
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        self._circuit_breaker_reset_time = None
        self._circuit_breaker_timeout = 60  # 1 minute
        
        # Initialize session with proper configuration
        self._initialize_session()
    
    def _initialize_session(self) -> None:
        """Initialize HTTP session with proper connection pooling and timeouts"""
        if self.session is not None:
            self.close()
        
        self.session = requests.Session()
        self._session_closed = False
        
        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,      # Maximum number of connections in pool
            max_retries=0,        # We handle retries manually
            pool_block=False      # Don't block when pool is full
        )
        
        # Mount adapter for both HTTP and HTTPS
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Setup session headers with conservative approach
        user_agent = get_compatible_user_agent()
        headers = get_conservative_headers()
        headers['user-agent'] = user_agent
        
        self.session.headers.update(headers)
        
        self.logger.debug("HTTP session initialized with connection pooling")
    
    def update_user_agent(self) -> None:
        """Обновляет User-Agent с консервативными заголовками"""
        if self.session:
            new_user_agent = get_compatible_user_agent()
            # Обновляем только User-Agent, оставляя остальные заголовки без изменений
            self.session.headers['user-agent'] = new_user_agent
            self.logger.debug(f"User-Agent updated to: {new_user_agent[:50]}...")
    
    def _create_default_retry_config(self) -> RetryConfig:
        """Create default retry configuration optimized for Xbox API"""
        return RetryConfig(
            base_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            max_attempts=3,
            jitter_factor=0.3,
            
            # Rate limiting specific settings
            rate_limit_base_delay=5.0,
            rate_limit_max_delay=300.0,  # 5 minutes max
            rate_limit_max_attempts=5,
            
            # Network error specific settings
            network_error_base_delay=0.5,
            network_error_max_delay=30.0,
            network_error_max_attempts=3,
            
            # Server error specific settings
            server_error_base_delay=2.0,
            server_error_max_delay=120.0,
            server_error_max_attempts=4
        )
    
    def _check_network_connectivity(self) -> bool:
        """Check network connectivity to Microsoft services"""
        current_time = time.time()
        
        # Only check connectivity periodically to avoid overhead
        if current_time - self._last_connectivity_check < self._connectivity_check_interval:
            return self._is_connected
        
        self._last_connectivity_check = current_time
        
        try:
            # Try to resolve Microsoft's hostname
            socket.gethostbyname('purchase.mp.microsoft.com')
            
            # Try a simple HTTP request to check connectivity
            test_response = requests.get(
                'https://purchase.mp.microsoft.com',
                timeout=(5, 10),
                allow_redirects=False
            )
            
            self._is_connected = True
            self.logger.debug("Network connectivity check passed")
            return True
            
        except (socket.gaierror, requests.exceptions.RequestException) as e:
            self._is_connected = False
            self.logger.warning(f"Network connectivity check failed: {e}")
            return False
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open due to consecutive failures"""
        if self._consecutive_failures < self._max_consecutive_failures:
            return False
        
        # Check if reset time has passed
        if self._circuit_breaker_reset_time is None:
            self._circuit_breaker_reset_time = time.time() + self._circuit_breaker_timeout
            self.logger.warning(f"Circuit breaker opened due to {self._consecutive_failures} consecutive failures")
            return True
        
        if time.time() >= self._circuit_breaker_reset_time:
            # Reset circuit breaker
            self._consecutive_failures = 0
            self._circuit_breaker_reset_time = None
            self.logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def _handle_network_error(self, error: Exception, code: str) -> CodeResult:
        """Handle network-related errors with appropriate classification"""
        timestamp = datetime.now()
        
        # Classify the network error
        if isinstance(error, requests.exceptions.Timeout):
            status = CodeStatus.ERROR
            details = f"Таймаут запроса ({self.connection_timeout + self.read_timeout}s)"
        elif isinstance(error, requests.exceptions.ConnectionError):
            if isinstance(error.args[0], (NewConnectionError, MaxRetryError)):
                status = CodeStatus.ERROR
                details = "Не удалось установить соединение с сервером"
            else:
                status = CodeStatus.ERROR
                details = f"Ошибка соединения: {str(error)[:100]}"
        elif isinstance(error, requests.exceptions.HTTPError):
            status = CodeStatus.ERROR
            details = f"HTTP ошибка: {error.response.status_code if error.response else 'Unknown'}"
        elif isinstance(error, requests.exceptions.RequestException):
            status = CodeStatus.ERROR
            details = f"Ошибка запроса: {str(error)[:100]}"
        else:
            status = CodeStatus.ERROR
            details = f"Сетевая ошибка: {str(error)[:100]}"
        
        return CodeResult(
            code=code,
            status=status,
            timestamp=timestamp,
            details=details
        )
    
    def _handle_http_status_code(self, response: requests.Response, code: str, timestamp: datetime) -> Optional[CodeResult]:
        """Handle specific HTTP status codes with appropriate retry logic"""
        status_code = response.status_code
        
        # Handle different status codes
        if status_code == 429:  # Rate Limited
            # Extract retry-after header if available
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_seconds = int(retry_after)
                    details = f"Превышен лимит запросов (повтор через {retry_seconds}s)"
                except ValueError:
                    details = "Превышен лимит запросов"
            else:
                details = "Превышен лимит запросов"
            
            return CodeResult(
                code=code,
                status=CodeStatus.RATE_LIMITED,
                timestamp=timestamp,
                details=details,
                response_data={'status_code': status_code, 'headers': dict(response.headers)}
            )
        
        elif status_code == 401:  # Unauthorized - это проблема с WLID токеном, не с кодом
            # Это специальный случай - нужно пометить токен как недействительный
            # и попробовать с другим токеном, если он есть
            return CodeResult(
                code=code,
                status=CodeStatus.WLID_TOKEN_ERROR,  # Специальный статус для проблем с токеном
                timestamp=timestamp,
                details="Недействительный WLID токен (401 Unauthorized)",
                response_data={'status_code': status_code}
            )
        
        elif status_code == 403:  # Forbidden
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details="Доступ запрещен (403 Forbidden)",
                response_data={'status_code': status_code}
            )
        
        elif status_code == 404:  # Not Found
            return CodeResult(
                code=code,
                status=CodeStatus.INVALID,
                timestamp=timestamp,
                details="Код не найден (404 Not Found)",
                response_data={'status_code': status_code}
            )
        
        elif 500 <= status_code < 600:  # Server Errors
            server_errors = {
                500: "Внутренняя ошибка сервера",
                502: "Неверный шлюз",
                503: "Сервис недоступен",
                504: "Таймаут шлюза"
            }
            
            error_message = server_errors.get(status_code, f"Ошибка сервера ({status_code})")
            
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details=error_message,
                response_data={'status_code': status_code}
            )
        
        elif status_code != 200:  # Other non-success codes
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details=f"Неожиданный HTTP статус: {status_code} {response.reason}",
                response_data={'status_code': status_code}
            )
        
        return None  # Status code 200, continue with normal processing
    
    def get_available_wlid(self) -> Optional[WLIDToken]:
        """Get an available WLID token (not rate limited)"""
        # Фильтруем доступные токены (валидные и не заблокированные)
        available_tokens = [token for token in self.wlid_tokens if token.is_available()]
        
        if not available_tokens:
            # Проверяем, есть ли токены, которые скоро разблокируются
            rate_limited_tokens = [token for token in self.wlid_tokens 
                                 if token.is_valid and token.is_rate_limited()]
            
            if rate_limited_tokens:
                # Находим токен с наименьшим временем блокировки
                next_available = min(rate_limited_tokens, 
                                   key=lambda t: t.rate_limited_until or datetime.max)
                wait_time = (next_available.rate_limited_until - datetime.now()).total_seconds()
                self.logger.info(f"Все токены заблокированы лимитами. Следующий доступен через {wait_time:.1f} секунд")
            
            return None
        
        # Приоритет токенам, которые не использовались недавно
        now = datetime.now()
        unused_tokens = [
            token for token in available_tokens 
            if token.last_used is None or (now - token.last_used).seconds > 60
        ]
        
        if unused_tokens:
            return random.choice(unused_tokens)
        else:
            return random.choice(available_tokens)
    

    
    def enforce_request_delay(self) -> None:
        """Enforce minimum delay between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def check_code(self, code: str) -> CodeResult:
        """
        Check a single Xbox code with enhanced network error handling and retry logic
        Returns CodeResult with status and details
        """
        timestamp = datetime.now()
        
        # Validate code format first
        if len(code) < 18:
            return CodeResult(
                code=code,
                status=CodeStatus.INVALID,
                timestamp=timestamp,
                details="Код слишком короткий (менее 18 символов)"
            )
        
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details="Сервис временно недоступен (circuit breaker)"
            )
        
        # Check network connectivity
        if not self._check_network_connectivity():
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details="Нет подключения к интернету"
            )
        
        # Редко обновляем User-Agent для лучшей маскировки
        if random.random() < 0.01:  # 1% шанс обновить User-Agent
            self.update_user_agent()
        
        # Use RetryableOperation for automatic retry handling
        def make_request():
            return self._make_api_request(code, timestamp)
        
        try:
            with RetryableOperation(self.retry_manager, code, make_request) as operation:
                result = operation.execute()
                
                # Reset consecutive failures on success
                self._consecutive_failures = 0
                return result
                
        except Exception as e:
            # Increment consecutive failures
            self._consecutive_failures += 1
            
            # Handle the final error after all retries failed
            return self._handle_network_error(e, code)
    
    def _make_api_request(self, code: str, timestamp: datetime) -> CodeResult:
        """Make the actual API request (used by retry logic)"""
        # Enforce request delay
        self.enforce_request_delay()
        
        # Get available WLID token (with smart waiting)
        wlid_token = self.wait_for_available_token()
        if not wlid_token:
            # Check reason for unavailability
            valid_tokens = [token for token in self.wlid_tokens if token.is_valid]
            
            if not valid_tokens:
                return CodeResult(
                    code=code,
                    status=CodeStatus.WLID_TOKEN_ERROR,
                    timestamp=timestamp,
                    details="Все WLID токены недействительны"
                )
            elif all(token.is_rate_limited() for token in valid_tokens):
                return CodeResult(
                    code=code,
                    status=CodeStatus.WLID_TOKEN_ERROR,
                    timestamp=timestamp,
                    details="Все WLID токены временно заблокированы лимитами"
                )
            else:
                return CodeResult(
                    code=code,
                    status=CodeStatus.WLID_TOKEN_ERROR,
                    timestamp=timestamp,
                    details="Нет доступных WLID токенов (проверьте конфигурацию)"
                )
        
        # Ensure session is active
        self._ensure_session_active()
        
        # Prepare request
        url = f"https://purchase.mp.microsoft.com/v7.0/tokenDescriptions/{code}"
        params = {
            'market': 'US',
            'language': 'en-US',
            'supportMultiAvailabilities': 'true'
        }
        
        headers = self.session.headers.copy()
        headers['authorization'] = wlid_token.get_formatted_token()
        
        # Make request with proper timeouts
        timeout = (self.connection_timeout, self.read_timeout)
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=timeout)
            wlid_token.mark_used()
            
            # Handle specific HTTP status codes
            status_result = self._handle_http_status_code(response, code, timestamp)
            if status_result:
                # Handle rate limiting for specific token
                if status_result.status == CodeStatus.RATE_LIMITED:
                    wlid_token.mark_rate_limited(300)  # 5 minutes for this token
                    self.logger.warning(f"Token {wlid_token.token[:20]}... rate limited for 5 minutes")
                elif status_result.status == CodeStatus.WLID_TOKEN_ERROR:
                    # Mark token as invalid when we get 401 error
                    wlid_token.mark_error()
                    self.logger.warning(f"Token {wlid_token.token[:20]}... marked as invalid due to 401 error")
                
                return status_result
            
            # Parse successful response (status code 200)
            try:
                json_data = response.json()
                return self._parse_api_response(code, json_data, timestamp)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {code}. Response: {response.text[:500]}")
                raise requests.exceptions.RequestException(f"Invalid JSON response: {str(e)}")
        
        except requests.exceptions.Timeout as e:
            self.logger.warning(f"Request timeout for code {code}: {e}")
            raise e
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Connection error for code {code}: {e}")
            raise e
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"HTTP error for code {code}: {e}")
            raise e
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Request exception for code {code}: {e}")
            raise e
    
    def _parse_api_response(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> CodeResult:
        """Enhanced API response parsing with comprehensive error handling and fallback mechanisms"""
        
        # Validate response structure first
        if not isinstance(json_data, dict):
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details="Неверная структура ответа API (не JSON объект)",
                response_data={'raw_response': str(json_data)[:200]}
            )
        
        # Sanitize response data for logging
        sanitized_data = self._sanitize_response_data(json_data)
        
        try:
            # Try multiple parsing strategies in order of reliability
            
            # Strategy 1: Parse Microsoft API error format with innererror
            result = self._parse_inner_error_format(code, json_data, timestamp)
            if result:
                return result
            
            # Strategy 2: Parse events format (newer API response format)
            result = self._parse_events_format(code, json_data, timestamp)
            if result:
                return result
            
            # Strategy 3: Parse tokenState format (most common)
            result = self._parse_token_state_format(code, json_data, timestamp)
            if result:
                return result
            
            # Strategy 4: Parse error code format
            result = self._parse_error_code_format(code, json_data, timestamp)
            if result:
                return result
            
            # Strategy 5: Parse message/description fields
            result = self._parse_message_format(code, json_data, timestamp)
            if result:
                return result
            
            # Strategy 6: Fallback pattern matching
            result = self._parse_fallback_patterns(code, json_data, timestamp)
            if result:
                return result
            
            # Strategy 7: Unknown response structure - detailed analysis
            return self._handle_unknown_response(code, json_data, timestamp)
            
        except Exception as e:
            self.logger.error(f"Exception during response parsing for code {code}: {str(e)}")
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details=f"Ошибка парсинга ответа API: {str(e)}",
                response_data=sanitized_data
            )
    
    def _sanitize_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response data for safe logging and storage"""
        try:
            # Create a deep copy and remove/truncate sensitive or large fields
            sanitized = {}
            
            for key, value in data.items():
                if key.lower() in ['authorization', 'token', 'secret', 'key']:
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, str) and len(value) > 500:
                    sanitized[key] = value[:500] + "...[TRUNCATED]"
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_response_data(value)
                elif isinstance(value, list) and len(value) > 10:
                    sanitized[key] = value[:10] + ["...[TRUNCATED]"]
                else:
                    sanitized[key] = value
            
            return sanitized
        except Exception:
            return {"error": "Failed to sanitize response data"}
    
    def _parse_inner_error_format(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> Optional[CodeResult]:
        """Parse Microsoft API error format with innererror"""
        if 'innererror' not in json_data:
            return None
        
        inner_error = json_data['innererror']
        if not isinstance(inner_error, dict):
            return None
        
        inner_code = inner_error.get('code', '')
        inner_message = inner_error.get('message', '').lower()
        inner_data = inner_error.get('data', [])
        
        # Enhanced expired token detection
        expired_codes = ['TokenExpired', 'RedeemTokenExpired', 'ExpiredToken', 'CodeExpired']
        expired_keywords = ['expired', 'no longer valid', 'cannot be redeemed']
        
        if (inner_code in expired_codes or
            any(keyword in inner_message for keyword in expired_keywords) or
            any('expired' in str(data).lower() for data in inner_data if isinstance(data, (str, dict)))):
            
            return CodeResult(
                code=code,
                status=CodeStatus.EXPIRED,
                timestamp=timestamp,
                details=f"Код истек: {inner_message or inner_code}",
                response_data=self._sanitize_response_data(json_data)
            )
        
        # Check for invalid token codes
        invalid_codes = ['InvalidToken', 'InvalidRedeemToken', 'NotFound', 'BadRequest']
        if inner_code in invalid_codes:
            return CodeResult(
                code=code,
                status=CodeStatus.INVALID,
                timestamp=timestamp,
                details=f"Недействительный код: {inner_message or inner_code}",
                response_data=self._sanitize_response_data(json_data)
            )
        
        return None
    
    def _parse_events_format(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> Optional[CodeResult]:
        """Parse events format (alternative API response format)"""
        if 'events' not in json_data:
            return None
        
        events = json_data['events']
        if not isinstance(events, dict) or 'cart' not in events:
            return None
        
        cart_events = events['cart']
        if not isinstance(cart_events, list):
            return None
        
        for event in cart_events:
            if not isinstance(event, dict) or event.get('type') != 'error':
                continue
            
            error_code = event.get('code', '')
            event_data = event.get('data', {})
            reason = event_data.get('reason', '') if isinstance(event_data, dict) else ''
            
            if error_code == 'InvalidRedeemToken':
                if reason == 'RedeemTokenExpired':
                    return CodeResult(
                        code=code,
                        status=CodeStatus.EXPIRED,
                        timestamp=timestamp,
                        details="Код истек и не может быть использован",
                        response_data=self._sanitize_response_data(json_data)
                    )
                else:
                    return CodeResult(
                        code=code,
                        status=CodeStatus.INVALID,
                        timestamp=timestamp,
                        details=f"Недействительный код: {reason or 'неизвестная причина'}",
                        response_data=self._sanitize_response_data(json_data)
                    )
        
        return None
    
    def _parse_token_state_format(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> Optional[CodeResult]:
        """Parse tokenState format (most common format)"""
        if 'tokenState' not in json_data:
            return None
        
        token_state = json_data['tokenState']
        
        if token_state == 'Active':
            # Check for expiry date with enhanced date parsing
            expiry_details = self._parse_expiry_date(json_data)
            if expiry_details['is_expired']:
                return CodeResult(
                    code=code,
                    status=CodeStatus.EXPIRED,
                    timestamp=timestamp,
                    details=expiry_details['message'],
                    response_data=self._sanitize_response_data(json_data)
                )
            
            return CodeResult(
                code=code,
                status=CodeStatus.VALID,
                timestamp=timestamp,
                details="Код действителен и не использован",
                response_data=self._sanitize_response_data(json_data)
            )
        
        elif token_state == 'Redeemed':
            return CodeResult(
                code=code,
                status=CodeStatus.USED,
                timestamp=timestamp,
                details="Код был использован",
                response_data=self._sanitize_response_data(json_data)
            )
        
        elif token_state in ['Expired', 'Invalid']:
            return CodeResult(
                code=code,
                status=CodeStatus.EXPIRED if token_state == 'Expired' else CodeStatus.INVALID,
                timestamp=timestamp,
                details=f"Код {token_state.lower()}",
                response_data=self._sanitize_response_data(json_data)
            )
        
        else:
            # Unknown token state - log for analysis
            self.logger.warning(f"Unknown tokenState '{token_state}' for code {code}")
            return CodeResult(
                code=code,
                status=CodeStatus.ERROR,
                timestamp=timestamp,
                details=f"Неизвестное состояние токена: {token_state}",
                response_data=self._sanitize_response_data(json_data)
            )
    
    def _parse_error_code_format(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> Optional[CodeResult]:
        """Parse error code format"""
        if 'code' not in json_data:
            return None
        
        error_code = json_data['code']
        error_message = json_data.get('message', '')
        
        # Map error codes to statuses
        error_mappings = {
            'NotFound': (CodeStatus.INVALID, "Код не найден"),
            'Expired': (CodeStatus.EXPIRED, "Код истек"),
            'TokenExpired': (CodeStatus.EXPIRED, "Код истек"),
            'InvalidToken': (CodeStatus.INVALID, "Недействительный код"),
            'InvalidRedeemToken': (CodeStatus.INVALID, "Недействительный код для активации"),
            'Unauthorized': (CodeStatus.ERROR, "Неавторизован - неверный WLID"),
            'Forbidden': (CodeStatus.ERROR, "Доступ запрещен"),
            'BadRequest': (CodeStatus.INVALID, "Неверный формат кода"),
            'InternalServerError': (CodeStatus.ERROR, "Внутренняя ошибка сервера"),
            'ServiceUnavailable': (CodeStatus.ERROR, "Сервис недоступен"),
            'TooManyRequests': (CodeStatus.ERROR, "Слишком много запросов")
        }
        
        if error_code in error_mappings:
            status, default_message = error_mappings[error_code]
            details = error_message or default_message
            
            return CodeResult(
                code=code,
                status=status,
                timestamp=timestamp,
                details=details,
                response_data=self._sanitize_response_data(json_data)
            )
        
        # Unknown error code
        self.logger.warning(f"Unknown error code '{error_code}' for code {code}")
        return CodeResult(
            code=code,
            status=CodeStatus.ERROR,
            timestamp=timestamp,
            details=f"Неизвестная ошибка API: {error_code} - {error_message}",
            response_data=self._sanitize_response_data(json_data)
        )
    
    def _parse_message_format(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> Optional[CodeResult]:
        """Parse message and description fields"""
        message = json_data.get('message', '').lower()
        description = json_data.get('description', '').lower()
        combined_text = f"{message} {description}".strip()
        
        if not combined_text:
            return None
        
        # Enhanced pattern matching
        patterns = {
            CodeStatus.EXPIRED: [
                'expired', 'cannot be redeemed', 'this token has expired',
                'token is no longer valid', 'redemption code has expired',
                'code has expired', 'no longer available'
            ],
            CodeStatus.USED: [
                'already redeemed', 'already used', 'previously redeemed',
                'code has been used', 'already claimed'
            ],
            CodeStatus.INVALID: [
                'invalid code', 'not found', 'does not exist',
                'invalid format', 'malformed', 'not valid'
            ]
        }
        
        for status, keywords in patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                return CodeResult(
                    code=code,
                    status=status,
                    timestamp=timestamp,
                    details=f"Определено по сообщению: {message or description}",
                    response_data=self._sanitize_response_data(json_data)
                )
        
        return None
    
    def _parse_fallback_patterns(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> Optional[CodeResult]:
        """Fallback pattern matching across entire response"""
        response_text = str(json_data).lower()
        
        # Last resort pattern matching
        if ('expired' in response_text and ('token' in response_text or 'code' in response_text)):
            return CodeResult(
                code=code,
                status=CodeStatus.EXPIRED,
                timestamp=timestamp,
                details="Код истек (определено по содержимому ответа)",
                response_data=self._sanitize_response_data(json_data)
            )
        
        if 'cannot be redeemed' in response_text or 'not available' in response_text:
            return CodeResult(
                code=code,
                status=CodeStatus.INVALID,
                timestamp=timestamp,
                details="Код недоступен для активации",
                response_data=self._sanitize_response_data(json_data)
            )
        
        return None
    
    def _parse_expiry_date(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced expiry date parsing with multiple format support"""
        result = {'is_expired': False, 'message': ''}
        
        # Try different expiry date field names
        date_fields = ['tokenExpiryDate', 'expiryDate', 'expiry', 'validUntil', 'expires']
        
        for field in date_fields:
            if field not in json_data:
                continue
            
            date_str = json_data[field]
            if not isinstance(date_str, str):
                continue
            
            try:
                # Try different date formats
                date_formats = [
                    '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO with microseconds
                    '%Y-%m-%dT%H:%M:%SZ',     # ISO without microseconds
                    '%Y-%m-%dT%H:%M:%S',      # ISO without timezone
                    '%Y-%m-%d %H:%M:%S',      # Standard format
                    '%Y-%m-%d',               # Date only
                ]
                
                expiry_date = None
                for fmt in date_formats:
                    try:
                        expiry_date = datetime.strptime(date_str.replace('Z', ''), fmt.replace('Z', ''))
                        break
                    except ValueError:
                        continue
                
                if expiry_date is None:
                    # Try ISO format parsing as fallback
                    expiry_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Check if expired (with timezone awareness)
                now = datetime.now()
                if expiry_date.tzinfo:
                    now = now.replace(tzinfo=expiry_date.tzinfo)
                
                if expiry_date < now:
                    result['is_expired'] = True
                    result['message'] = f"Код истек {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                
                break
                
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Could not parse {field} '{date_str}': {e}")
                continue
        
        return result
    
    def _handle_unknown_response(self, code: str, json_data: Dict[str, Any], timestamp: datetime) -> CodeResult:
        """Handle unknown response structure with detailed analysis"""
        # Log the unknown response structure for analysis
        self.logger.warning(f"Unknown API response structure for code {code}: {list(json_data.keys())}")
        
        # Try to extract any useful information
        details_parts = []
        
        # Check for any status-like fields
        status_fields = ['status', 'state', 'result', 'outcome']
        for field in status_fields:
            if field in json_data:
                details_parts.append(f"{field}: {json_data[field]}")
        
        # Check for any message-like fields
        message_fields = ['message', 'description', 'error', 'reason']
        for field in message_fields:
            if field in json_data:
                value = str(json_data[field])[:100]  # Limit length
                details_parts.append(f"{field}: {value}")
        
        details = "; ".join(details_parts) if details_parts else "Неизвестная структура ответа API"
        
        return CodeResult(
            code=code,
            status=CodeStatus.ERROR,
            timestamp=timestamp,
            details=f"Не удалось определить статус кода: {details}",
            response_data=self._sanitize_response_data(json_data)
        )
    
    def test_wlid_tokens(self) -> Dict[str, Any]:
        """Test all WLID tokens to see which ones are valid"""
        results = {
            'valid_tokens': [],
            'invalid_tokens': [],
            'errors': []
        }
        
        test_code = "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"  # Dummy code for testing
        
        for token in self.wlid_tokens:
            try:
                # Ensure session is active
                self._ensure_session_active()
                
                url = f"https://purchase.mp.microsoft.com/v7.0/tokenDescriptions/{test_code}"
                params = {
                    'market': 'US',
                    'language': 'en-US',
                    'supportMultiAvailabilities': 'true'
                }
                
                headers = self.session.headers.copy()
                headers['authorization'] = token.get_formatted_token()
                
                # Use proper timeouts (shorter for testing)
                timeout = (min(5.0, self.connection_timeout), min(10.0, self.read_timeout))
                response = self.session.get(url, params=params, headers=headers, timeout=timeout)
                
                if response.status_code == 401:
                    token.is_valid = False
                    results['invalid_tokens'].append(token.token)
                elif response.status_code in [200, 404]:  # 404 is expected for dummy code
                    token.is_valid = True
                    results['valid_tokens'].append(token.token)
                else:
                    results['errors'].append(f"Token {token.token[:20]}...: HTTP {response.status_code}")
                
                time.sleep(0.5)  # Small delay between tests
                
            except Exception as e:
                results['errors'].append(f"Token {token.token[:20]}...: {str(e)}")
        
        return results
    
    def get_token_status(self) -> Dict[str, Any]:
        """Get detailed status of all tokens"""
        now = datetime.now()
        status = {
            'total_tokens': len(self.wlid_tokens),
            'available_tokens': 0,
            'rate_limited_tokens': 0,
            'invalid_tokens': 0,
            'tokens_detail': []
        }
        
        for i, token in enumerate(self.wlid_tokens):
            token_info = {
                'index': i + 1,
                'token_preview': token.token[:20] + "...",
                'is_valid': token.is_valid,
                'is_rate_limited': token.is_rate_limited(),
                'is_available': token.is_available(),
                'error_count': token.error_count,
                'last_used': token.last_used.strftime('%H:%M:%S') if token.last_used else 'Never'
            }
            
            if token.is_rate_limited():
                wait_time = (token.rate_limited_until - now).total_seconds()
                token_info['rate_limit_remaining'] = f"{wait_time:.0f}s"
                status['rate_limited_tokens'] += 1
            elif not token.is_valid:
                status['invalid_tokens'] += 1
            else:
                status['available_tokens'] += 1
                
            status['tokens_detail'].append(token_info)
        
        return status
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get network and connectivity status"""
        return {
            'is_connected': self._is_connected,
            'last_connectivity_check': datetime.fromtimestamp(self._last_connectivity_check).strftime('%H:%M:%S'),
            'consecutive_failures': self._consecutive_failures,
            'circuit_breaker_open': self._is_circuit_breaker_open(),
            'circuit_breaker_reset_time': (
                datetime.fromtimestamp(self._circuit_breaker_reset_time).strftime('%H:%M:%S')
                if self._circuit_breaker_reset_time else None
            ),
            'retry_statistics': self.retry_manager.get_statistics()
        }
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker"""
        self._consecutive_failures = 0
        self._circuit_breaker_reset_time = None
        self.retry_manager.reset_circuit_breaker()
        self.logger.info("Circuit breaker manually reset")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the API client"""
        retry_stats = self.retry_manager.get_statistics()
        
        return {
            'session_active': not self._session_closed,
            'request_delay': self.request_delay,
            'connection_timeout': self.connection_timeout,
            'read_timeout': self.read_timeout,
            'total_retries': retry_stats['total_retries'],
            'successful_retries': retry_stats['successful_retries'],
            'failed_retries': retry_stats['failed_retries'],
            'retry_success_rate': retry_stats['success_rate'],
            'network_connectivity': self._is_connected,
            'circuit_breaker_failures': self._consecutive_failures
        }
    
    def update_request_delay(self, delay: float) -> None:
        """Update the request delay"""
        self.request_delay = max(0.1, delay)  # Minimum 0.1 seconds
    
    def update_timeouts(self, connection_timeout: float, read_timeout: float) -> None:
        """Update connection and read timeouts"""
        self.connection_timeout = max(1.0, connection_timeout)
        self.read_timeout = max(5.0, read_timeout)
        self.logger.debug(f"Updated timeouts: connection={self.connection_timeout}s, read={self.read_timeout}s")
    
    def _ensure_session_active(self) -> None:
        """Ensure session is active and not closed"""
        if self._session_closed or self.session is None:
            self.logger.warning("Session was closed, reinitializing...")
            self._initialize_session()
    
    def close(self) -> None:
        """Close the session and clean up resources"""
        if self.session is not None and not self._session_closed:
            try:
                self.session.close()
                self.logger.debug("HTTP session closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing HTTP session: {e}")
            finally:
                self._session_closed = True
                self.session = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure session is closed"""
        self.close()
        return False  # Don't suppress exceptions
    
    def __del__(self):
        """Destructor - ensure session is closed"""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup