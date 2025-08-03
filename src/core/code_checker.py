"""
Core code checking functionality for Xbox Code Checker GUI
"""

import threading
import time
import queue
from typing import List, Callable, Optional, Dict, Any
from datetime import datetime
import logging

from ..data.models import WLIDToken, CodeResult, CodeStatus, CheckingSession, SessionStatus
from ..data.api_client import APIClient


class CodeChecker:
    """Handles the core logic of checking Xbox codes"""
    
    def __init__(self, wlid_tokens: List[WLIDToken], max_threads: int = 5, request_delay: float = 1.0):
        self.wlid_tokens = wlid_tokens
        self.max_threads = max_threads
        self.request_delay = request_delay
        
        # Threading control
        self.threads: List[threading.Thread] = []
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start unpaused
        
        # Queues for thread communication
        self.code_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # Session management
        self.session = CheckingSession()
        
        # Callbacks
        self.progress_callback: Optional[Callable[[CodeResult], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        self.completion_callback: Optional[Callable[[], None]] = None
        
        # API client
        self.api_client: Optional[APIClient] = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.codes_per_second = 0.0
        self.last_speed_update = time.time()
        self.codes_checked_for_speed = 0
        
        # Rate limit tracking with thread safety
        self.pending_codes = set()  # Коды, которые еще не обработаны окончательно
        self.pending_codes_lock = threading.Lock()  # Lock for thread-safe access to pending_codes
        self.retry_counts = {}  # Счетчик повторных попыток для каждого кода
        self.retry_counts_lock = threading.Lock()  # Lock for thread-safe access to retry_counts
        self.max_retries = 3  # Максимальное количество повторных попыток
    
    def set_progress_callback(self, callback: Callable[[CodeResult], None]) -> None:
        """Set callback for progress updates"""
        self.progress_callback = callback
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for status updates"""
        self.status_callback = callback
    
    def set_completion_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for session completion"""
        self.completion_callback = callback
    
    def update_settings(self, max_threads: int, request_delay: float) -> None:
        """Update checker settings"""
        self.max_threads = max_threads
        self.request_delay = request_delay
        
        if self.api_client:
            self.api_client.update_request_delay(request_delay)
    
    def check_codes_batch(self, codes: List[str]) -> None:
        """
        Start checking a batch of codes
        This method runs in a separate thread and manages the checking process
        """
        if self.session.status == SessionStatus.RUNNING:
            self.logger.warning("Проверка уже выполняется")
            return
        
        # Reset session
        self.session.reset()
        self.session.codes = codes.copy()
        self.session.wlids = [token.token for token in self.wlid_tokens]
        self.session.total_codes = len(codes)
        self.session.status = SessionStatus.RUNNING
        self.session.start_time = datetime.now()
        
        # Reset control events
        self.stop_event.clear()
        self.pause_event.set()
        
        # Reset rate limit tracking with thread safety
        with self.pending_codes_lock:
            self.pending_codes = set(codes)
        with self.retry_counts_lock:
            self.retry_counts = {code: 0 for code in codes}
        
        # Initialize API client
        self.api_client = APIClient(self.wlid_tokens, self.request_delay)
        
        # Clear queues
        while not self.code_queue.empty():
            try:
                self.code_queue.get_nowait()
            except queue.Empty:
                break
        
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break
        
        # Add codes to queue
        for code in codes:
            self.code_queue.put(code)
        
        # Start worker threads
        self.threads = []
        for i in range(min(self.max_threads, len(codes))):
            thread = threading.Thread(target=self._worker_thread, name=f"CodeChecker-{i}")
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        # Start result collector thread
        collector_thread = threading.Thread(target=self._result_collector, name="ResultCollector")
        collector_thread.daemon = True
        collector_thread.start()
        
        # Update status
        if self.status_callback:
            self.status_callback(f"Started checking {len(codes)} codes with {len(self.threads)} threads")
        
        self.logger.info(f"Начата проверка {len(codes)} кодов с {len(self.threads)} потоками")
    
    def _worker_thread(self) -> None:
        """Worker thread that processes codes from the queue"""
        while not self.stop_event.is_set():
            try:
                # Wait if paused
                self.pause_event.wait()
                
                # Check if we should stop
                if self.stop_event.is_set():
                    break
                
                # Get next code
                try:
                    code = self.code_queue.get(timeout=1.0)
                except queue.Empty:
                    # No more codes to process, but check if we have pending codes
                    with self.pending_codes_lock:
                        has_pending = bool(self.pending_codes)
                    if has_pending and not self.stop_event.is_set():
                        # Wait a bit and continue - maybe some codes will be retried
                        time.sleep(5)
                        continue
                    break
                
                # Check the code
                result = self.api_client.check_code(code)
                
                # Handle rate limited codes
                if result.status == CodeStatus.RATE_LIMITED:
                    with self.retry_counts_lock:
                        retry_count = self.retry_counts.get(code, 0)
                    
                    if retry_count < self.max_retries:
                        # Increment retry count
                        with self.retry_counts_lock:
                            self.retry_counts[code] = retry_count + 1
                        
                        # Wait before putting back in queue (progressive backoff)
                        wait_time = min(30, 10 * (retry_count + 1))  # 10s, 20s, 30s
                        self.logger.info(f"Код {code} заблокирован лимитами, попытка {retry_count + 1}/{self.max_retries} через {wait_time}с")
                        
                        # Wait and put back in queue if not stopped
                        time.sleep(wait_time)
                        if not self.stop_event.is_set():
                            self.code_queue.put(code)
                        
                        self.code_queue.task_done()
                        continue
                    else:
                        # Max retries reached, mark as skipped (not an error)
                        self.logger.info(f"Код {code} пропущен после {self.max_retries} попыток из-за лимитов API")
                        result = CodeResult(
                            code=code,
                            status=CodeStatus.SKIPPED,
                            timestamp=datetime.now(),
                            details=f"Код пропущен из-за постоянных лимитов API (попыток: {self.max_retries})"
                        )
                
                # Handle WLID token errors - retry with different token
                elif result.status == CodeStatus.WLID_TOKEN_ERROR:
                    with self.retry_counts_lock:
                        retry_count = self.retry_counts.get(code, 0)
                    
                    if retry_count < self.max_retries:
                        # Increment retry count
                        with self.retry_counts_lock:
                            self.retry_counts[code] = retry_count + 1
                        
                        self.logger.info(f"WLID токен недействителен для кода {code}, попытка {retry_count + 1}/{self.max_retries} с другим токеном")
                        
                        # Put back in queue immediately (no wait needed for token errors)
                        if not self.stop_event.is_set():
                            self.code_queue.put(code)
                        
                        self.code_queue.task_done()
                        continue
                    else:
                        # Max retries reached, mark as skipped
                        self.logger.warning(f"Код {code} пропущен после {self.max_retries} попыток - все WLID токены недействительны")
                        result = CodeResult(
                            code=code,
                            status=CodeStatus.SKIPPED,
                            timestamp=datetime.now(),
                            details=f"Код пропущен - все WLID токены недействительны (попыток: {self.max_retries})"
                        )
                
                # Put result in queue (this removes code from pending)
                self.result_queue.put(result)
                
                # Mark task as done
                self.code_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Ошибка в рабочем потоке: {str(e)}")
                # Create error result for unknown code
                error_result = CodeResult(
                    code="UNKNOWN",
                    status=CodeStatus.ERROR,
                    timestamp=datetime.now(),
                    details=f"Worker thread error: {str(e)}"
                )
                self.result_queue.put(error_result)
    
    def _result_collector(self) -> None:
        """Collects results from worker threads and updates session"""
        while not self.stop_event.is_set() or not self.result_queue.empty():
            try:
                result = self.result_queue.get(timeout=1.0)
                
                # Remove code from pending set (final result received) - use discard to prevent KeyError
                with self.pending_codes_lock:
                    self.pending_codes.discard(result.code)
                
                # Add result to session
                self.session.add_result(result)
                
                # Update speed calculation
                self._update_speed()
                
                # Call progress callback
                if self.progress_callback:
                    self.progress_callback(result)
                
                # Check if we're done (all codes processed, not just checked count)
                with self.pending_codes_lock:
                    pending_count = len(self.pending_codes)
                if pending_count == 0:
                    self._finish_session()
                    break
                
            except queue.Empty:
                # Check if we have any pending codes and active threads
                with self.pending_codes_lock:
                    pending_count = len(self.pending_codes)
                if pending_count == 0:
                    self._finish_session()
                    break
                continue
            except Exception as e:
                self.logger.error(f"Ошибка в сборщике результатов: {str(e)}")
    
    def _update_speed(self) -> None:
        """Update checking speed calculation"""
        current_time = time.time()
        self.codes_checked_for_speed += 1
        
        # Update speed every 5 seconds or every 10 codes
        if (current_time - self.last_speed_update > 5.0 or 
            self.codes_checked_for_speed >= 10):
            
            time_elapsed = current_time - self.last_speed_update
            if time_elapsed > 0:
                self.codes_per_second = self.codes_checked_for_speed / time_elapsed
            
            self.last_speed_update = current_time
            self.codes_checked_for_speed = 0
    
    def _finish_session(self) -> None:
        """Finish the checking session"""
        self.session.end_time = datetime.now()
        self.session.status = SessionStatus.COMPLETED
        
        # Close API client
        if self.api_client:
            self.api_client.close()
            self.api_client = None
        
        # Update status
        if self.status_callback:
            duration = (self.session.end_time - self.session.start_time).total_seconds()
            stats = self.session.get_statistics()
            status_msg = (f"Завершено! Проверено {stats['checked']}/{stats['total']} кодов за {duration:.1f}с. "
                         f"Рабочие: {stats['valid']}, Использованные: {stats['used']}, Неверные: {stats['invalid']}, "
                         f"Ошибки: {stats['error']}, Пропущены: {stats.get('skipped', 0)}")
            self.status_callback(status_msg)
        
        # Call completion callback
        if self.completion_callback:
            self.completion_callback()
        
        self.logger.info("Сессия проверки завершена")
    
    def pause_checking(self) -> bool:
        """Pause the checking process"""
        if self.session.status != SessionStatus.RUNNING:
            return False
        
        self.pause_event.clear()
        self.session.status = SessionStatus.PAUSED
        
        if self.status_callback:
            self.status_callback("Checking paused")
        
        self.logger.info("Проверка приостановлена")
        return True
    
    def resume_checking(self) -> bool:
        """Resume the checking process"""
        if self.session.status != SessionStatus.PAUSED:
            return False
        
        self.pause_event.set()
        self.session.status = SessionStatus.RUNNING
        
        if self.status_callback:
            self.status_callback("Checking resumed")
        
        self.logger.info("Проверка возобновлена")
        return True
    
    def stop_checking(self) -> bool:
        """Stop the checking process with graceful thread termination"""
        if self.session.status not in [SessionStatus.RUNNING, SessionStatus.PAUSED, SessionStatus.COMPLETED]:
            return False
        
        self.logger.info("Начинаем остановку проверки...")
        
        # Set stop event first to signal all threads to stop
        self.stop_event.set()
        self.pause_event.set()  # Unpause if paused to allow threads to see stop event
        
        # Monitor thread termination with timeout and logging
        thread_termination_timeout = 10.0  # Total timeout for all threads
        individual_thread_timeout = 3.0    # Timeout per thread
        
        active_threads = []
        for thread in self.threads:
            if thread.is_alive():
                active_threads.append(thread)
        
        if active_threads:
            self.logger.info(f"Ожидаем завершения {len(active_threads)} активных потоков...")
            
            # Wait for threads with individual timeouts and monitoring
            for i, thread in enumerate(active_threads):
                self.logger.debug(f"Ожидаем завершения потока {thread.name} ({i+1}/{len(active_threads)})")
                
                thread.join(timeout=individual_thread_timeout)
                
                if thread.is_alive():
                    self.logger.warning(f"Поток {thread.name} не завершился в течение {individual_thread_timeout}с")
                else:
                    self.logger.debug(f"Поток {thread.name} успешно завершен")
            
            # Check for any remaining alive threads
            still_alive = [t for t in active_threads if t.is_alive()]
            if still_alive:
                self.logger.error(f"Следующие потоки не завершились: {[t.name for t in still_alive]}")
                # Force cleanup anyway - we can't wait forever
            else:
                self.logger.info("Все потоки успешно завершены")
        
        # Perform cleanup sequence
        self._cleanup_resources()
        
        # Update session status
        self.session.status = SessionStatus.STOPPED
        self.session.end_time = datetime.now()
        
        if self.status_callback:
            stats = self.session.get_statistics()
            self.status_callback(f"Stopped. Checked {stats['checked']}/{stats['total']} codes")
        
        self.logger.info("Проверка остановлена")
        return True
    
    def _cleanup_resources(self) -> None:
        """Clean up all resources during shutdown"""
        try:
            # Clear pending codes and retry counts with thread safety
            if hasattr(self, 'pending_codes'):
                with self.pending_codes_lock:
                    pending_count = len(self.pending_codes)
                    self.pending_codes.clear()
                    if pending_count > 0:
                        self.logger.info(f"Очищено {pending_count} ожидающих кодов")
            
            if hasattr(self, 'retry_counts'):
                with self.retry_counts_lock:
                    retry_count = len(self.retry_counts)
                    self.retry_counts.clear()
                    if retry_count > 0:
                        self.logger.info(f"Очищено {retry_count} счетчиков повторов")
            
            # Clear queues
            self._clear_queues()
            
            # Close API client
            if self.api_client:
                try:
                    self.api_client.close()
                    self.logger.debug("API клиент закрыт")
                except Exception as e:
                    self.logger.error(f"Ошибка при закрытии API клиента: {e}")
                finally:
                    self.api_client = None
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке ресурсов: {e}")
    
    def _clear_queues(self) -> None:
        """Clear all queues safely"""
        try:
            # Clear code queue
            codes_cleared = 0
            while not self.code_queue.empty():
                try:
                    self.code_queue.get_nowait()
                    codes_cleared += 1
                except queue.Empty:
                    break
            if codes_cleared > 0:
                self.logger.debug(f"Очищено {codes_cleared} кодов из очереди")
            
            # Clear result queue
            results_cleared = 0
            while not self.result_queue.empty():
                try:
                    self.result_queue.get_nowait()
                    results_cleared += 1
                except queue.Empty:
                    break
            if results_cleared > 0:
                self.logger.debug(f"Очищено {results_cleared} результатов из очереди")
                
        except Exception as e:
            self.logger.error(f"Ошибка при очистке очередей: {e}")
    
    def get_thread_status(self) -> Dict[str, Any]:
        """Get current thread status information"""
        thread_info = []
        
        for thread in self.threads:
            thread_info.append({
                'name': thread.name,
                'is_alive': thread.is_alive(),
                'daemon': thread.daemon,
                'ident': thread.ident
            })
        
        return {
            'total_threads': len(self.threads),
            'active_threads': sum(1 for t in self.threads if t.is_alive()),
            'stop_event_set': self.stop_event.is_set(),
            'pause_event_set': self.pause_event.is_set(),
            'thread_details': thread_info
        }
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        stats = self.session.get_statistics()
        
        # Calculate real progress based on pending codes
        if hasattr(self, 'pending_codes'):
            with self.pending_codes_lock:
                pending_count = len(self.pending_codes)
        else:
            pending_count = 0
        real_progress = ((self.session.total_codes - pending_count) / self.session.total_codes * 100) if self.session.total_codes > 0 else 0
        
        info = {
            'status': self.session.status.value,
            'progress_percentage': real_progress,
            'codes_per_second': self.codes_per_second,
            'statistics': stats,
            'pending_codes': pending_count
        }
        
        # Add retry information
        if hasattr(self, 'retry_counts'):
            with self.retry_counts_lock:
                retry_info = {
                    'codes_being_retried': sum(1 for count in self.retry_counts.values() if count > 0),
                    'total_retries': sum(self.retry_counts.values()),
                    'max_retries_per_code': self.max_retries
                }
            info['retry_info'] = retry_info
        
        if self.session.start_time:
            info['start_time'] = self.session.start_time.isoformat()
            
            if self.session.status == SessionStatus.RUNNING:
                elapsed = (datetime.now() - self.session.start_time).total_seconds()
                info['elapsed_time'] = elapsed
                
                # Estimate remaining time based on pending codes
                if self.codes_per_second > 0 and pending_count > 0:
                    estimated_remaining = pending_count / self.codes_per_second
                    info['estimated_remaining_time'] = estimated_remaining
        
        if self.session.end_time:
            info['end_time'] = self.session.end_time.isoformat()
            total_time = (self.session.end_time - self.session.start_time).total_seconds()
            info['total_time'] = total_time
        
        return info
    
    def get_results(self) -> List[CodeResult]:
        """Get all results from current session"""
        return self.session.results.copy()
    
    def get_results_by_status(self, status: CodeStatus) -> List[CodeResult]:
        """Get results filtered by status"""
        return [result for result in self.session.results if result.status == status]
    
    def is_checking(self) -> bool:
        """Check if currently checking codes"""
        return self.session.status in [SessionStatus.RUNNING, SessionStatus.PAUSED]
    
    def get_pending_codes_info(self) -> Dict[str, Any]:
        """Get information about codes that are still being processed"""
        if not hasattr(self, 'pending_codes') or not hasattr(self, 'retry_counts'):
            return {'pending_codes': [], 'retry_summary': {}}
        
        # Get thread-safe copies of the data
        with self.pending_codes_lock:
            pending_codes_copy = self.pending_codes.copy()
        with self.retry_counts_lock:
            retry_counts_copy = self.retry_counts.copy()
        
        pending_info = []
        for code in pending_codes_copy:
            retry_count = retry_counts_copy.get(code, 0)
            pending_info.append({
                'code': code,
                'retry_count': retry_count,
                'max_retries': self.max_retries,
                'status': 'retrying' if retry_count > 0 else 'pending'
            })
        
        retry_summary = {
            'total_pending': len(pending_codes_copy),
            'codes_being_retried': sum(1 for count in retry_counts_copy.values() if count > 0),
            'codes_awaiting_first_attempt': len([code for code in pending_codes_copy if retry_counts_copy.get(code, 0) == 0])
        }
        
        return {
            'pending_codes': pending_info,
            'retry_summary': retry_summary
        }
    
    def get_wlid_tokens_status(self) -> Dict[str, Any]:
        """Get detailed status of all WLID tokens"""
        tokens_info = []
        
        for i, token in enumerate(self.wlid_tokens):
            token_info = {
                'index': i,
                'token_preview': token.token[:20] + "..." if len(token.token) > 20 else token.token,
                'full_token': token.token,
                'is_valid': token.is_valid,
                'error_count': token.error_count,
                'last_used': token.last_used.isoformat() if token.last_used else None,
                'is_rate_limited': token.is_rate_limited(),
                'rate_limited_until': token.rate_limited_until.isoformat() if token.rate_limited_until else None,
                'is_available': token.is_available()
            }
            tokens_info.append(token_info)
        
        # Calculate summary statistics
        total_tokens = len(self.wlid_tokens)
        valid_tokens = sum(1 for token in self.wlid_tokens if token.is_valid)
        invalid_tokens = total_tokens - valid_tokens
        rate_limited_tokens = sum(1 for token in self.wlid_tokens if token.is_rate_limited())
        available_tokens = sum(1 for token in self.wlid_tokens if token.is_available())
        
        return {
            'tokens': tokens_info,
            'summary': {
                'total': total_tokens,
                'valid': valid_tokens,
                'invalid': invalid_tokens,
                'rate_limited': rate_limited_tokens,
                'available': available_tokens
            }
        }
    
    def remove_invalid_tokens(self) -> int:
        """Remove all invalid WLID tokens and return count of removed tokens"""
        initial_count = len(self.wlid_tokens)
        self.wlid_tokens = [token for token in self.wlid_tokens if token.is_valid]
        removed_count = initial_count - len(self.wlid_tokens)
        
        if removed_count > 0:
            self.logger.info(f"Удалено {removed_count} недействительных WLID токенов")
        
        return removed_count
    
    def remove_token_by_index(self, index: int) -> bool:
        """Remove WLID token by index"""
        if 0 <= index < len(self.wlid_tokens):
            removed_token = self.wlid_tokens.pop(index)
            self.logger.info(f"Удален WLID токен: {removed_token.token[:20]}...")
            return True
        return False
    
    def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Начинаем полную очистку ресурсов...")
        
        # Stop checking if still running
        if self.is_checking():
            self.stop_checking()
        
        # Additional cleanup for any remaining resources
        self._cleanup_resources()
        
        # Clear thread list
        self.threads.clear()
        
        self.logger.info("Очистка ресурсов завершена")