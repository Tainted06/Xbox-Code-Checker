"""
File management utilities for Xbox Code Checker GUI
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .models import CodeResult, CodeStatus, WLIDToken, FileSizeError


class FileManager:
    """Handles file operations for the application"""
    
    def __init__(self, max_file_size: int = 50 * 1024 * 1024):  # 50MB default
        self.max_file_size = max_file_size
        self.ensure_directories()
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist"""
        directories = ['input', 'output']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def validate_file_size(self, filepath: str) -> None:
        """
        Validate that file size doesn't exceed the maximum limit
        Raises FileSizeError if file is too large
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл не найден: {filepath}")
        
        file_size = os.path.getsize(filepath)
        
        if file_size > self.max_file_size:
            raise FileSizeError(filepath, file_size, self.max_file_size)
    
    def get_file_size_info(self, filepath: str) -> Dict[str, Any]:
        """Get detailed file size information"""
        if not os.path.exists(filepath):
            return {
                'exists': False,
                'error': f"Файл не найден: {filepath}"
            }
        
        try:
            file_size = os.path.getsize(filepath)
            file_size_mb = file_size / (1024 * 1024)
            max_size_mb = self.max_file_size / (1024 * 1024)
            
            return {
                'exists': True,
                'filepath': filepath,
                'size_bytes': file_size,
                'size_mb': round(file_size_mb, 2),
                'max_size_bytes': self.max_file_size,
                'max_size_mb': round(max_size_mb, 2),
                'size_valid': file_size <= self.max_file_size,
                'usage_percent': round((file_size / self.max_file_size) * 100, 1)
            }
        except Exception as e:
            return {
                'exists': True,
                'error': f"Ошибка получения размера файла: {str(e)}"
            }
    
    def update_max_file_size(self, max_size: int) -> None:
        """Update maximum file size limit"""
        if max_size <= 0:
            raise ValueError("Максимальный размер файла должен быть больше 0")
        self.max_file_size = max_size
    
    def read_wlid_file(self, filepath: str) -> Tuple[List[WLIDToken], List[str]]:
        """
        Reads WLID tokens from a file.

        This function handles different formats of WLID tokens, including
        plain tokens and tokens in the format 'WLID1.0="..."'.

        Args:
            filepath: The path to the file containing the WLID tokens.

        Returns:
            A tuple containing a list of valid WLIDToken objects and a list of
            error messages.
        """
        tokens = []
        errors = []
        
        if not os.path.exists(filepath):
            errors.append(f"Файл не найден: {filepath}")
            return tokens, errors
        
        # Validate file size before reading
        try:
            self.validate_file_size(filepath)
        except FileSizeError as e:
            errors.append(str(e))
            return tokens, errors
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    # Обрабатываем разные форматы WLID
                    token_value = line
                    if token_value.startswith('WLID1.0='):
                        token_value = token_value.split('=', 1)[1].strip('"')
                    
                    if token_value:
                        tokens.append(WLIDToken(token=token_value))
                    else:
                        errors.append(f"Строка {line_num}: Пустой токен")
                        
                except Exception as e:
                    errors.append(f"Строка {line_num}: {str(e)}")
            
            if not tokens:
                errors.append("В файле не найдено валидных WLID токенов")
                
        except Exception as e:
            errors.append(f"Ошибка чтения файла: {str(e)}")
        
        return tokens, errors
    
    def format_xbox_code(self, code: str) -> Optional[str]:
        """
        Форматирует Xbox код в правильный формат
        Из: QHR663JVTVWGTVXJXW4QR767Z (25 символов)
        В: QHR66-3JVTV-WGTVX-JXW4Q-R767Z (29 символов с дефисами)
        """
        if not code:
            return None
        
        # Убираем все пробелы и дефисы
        clean_code = ''.join(c for c in code.upper() if c.isalnum())
        
        # Проверяем длину (должно быть 25 символов)
        if len(clean_code) != 25:
            return None
        
        # Проверяем, что все символы буквенно-цифровые
        if not clean_code.isalnum():
            return None
        
        # Форматируем в группы по 5 символов
        formatted = f"{clean_code[0:5]}-{clean_code[5:10]}-{clean_code[10:15]}-{clean_code[15:20]}-{clean_code[20:25]}"
        
        return formatted

    def read_codes_file(self, filepath: str) -> Tuple[List[str], List[str]]:
        """
        Reads Xbox codes from a file.

        This function reads codes from a file, formats them to the standard
        Xbox code format (XXXXX-XXXXX-XXXXX-XXXXX-XXXXX), and validates them.

        Args:
            filepath: The path to the file containing the Xbox codes.

        Returns:
            A tuple containing a list of valid Xbox codes and a list of
            error messages.
        """
        codes = []
        errors = []
        
        if not os.path.exists(filepath):
            errors.append(f"Файл не найден: {filepath}")
            return codes, errors
        
        # Validate file size before reading
        try:
            self.validate_file_size(filepath)
        except FileSizeError as e:
            errors.append(str(e))
            return codes, errors
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Пытаемся отформатировать код
                formatted_code = self.format_xbox_code(line.strip())
                
                if formatted_code:
                    codes.append(formatted_code)
                elif self.validate_xbox_code(line.strip()):
                    codes.append(line.strip().upper())
                else:
                    errors.append(f"Строка {line_num}: Неверный формат кода '{line}' (должно быть 25 или 29 символов)")
            
            if not codes:
                errors.append("В файле не найдено валидных Xbox кодов")
                
        except Exception as e:
            errors.append(f"Ошибка чтения файла: {str(e)}")
        
        return codes, errors
    
    def validate_xbox_code(self, code: str) -> bool:
        """Проверяет формат Xbox кода"""
        if not code:
            return False
        
        # Убираем пробелы
        code = code.strip()
        
        # Проверяем длину (должно быть 29 символов: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX)
        if len(code) != 29:
            return False
        
        # Проверяем формат (5 групп по 5 символов, разделенных дефисами)
        parts = code.split('-')
        if len(parts) != 5:
            return False
        
        for part in parts:
            if len(part) != 5:
                return False
            # Разрешаем буквенно-цифровые символы
            if not all(c.isalnum() for c in part):
                return False
        
        return True
    
    def export_results_txt(self, results: List[CodeResult], base_path: str) -> List[str]:
        """
        Exports the results to separate TXT files based on their status.

        Args:
            results: A list of CodeResult objects.
            base_path: The base path for the exported files. The directory of
                this path will be used to create the files.

        Returns:
            A list of paths to the exported files.
        """
        exported_files = []
        
        # Группируем результаты по статусу
        grouped_results = {
            CodeStatus.VALID: [],
            CodeStatus.USED: [],
            CodeStatus.INVALID: [],
            CodeStatus.EXPIRED: [],
            CodeStatus.ERROR: [],
            CodeStatus.SKIPPED: [],
            CodeStatus.WLID_TOKEN_ERROR: []
        }
        
        for result in results:
            if result.status in grouped_results:
                grouped_results[result.status].append(result)
        
        # Экспортируем каждую категорию в отдельные файлы
        file_mapping = {
            CodeStatus.VALID: "рабочие.txt",
            CodeStatus.USED: "использованные.txt", 
            CodeStatus.INVALID: "неверные.txt",
            CodeStatus.EXPIRED: "истекшие.txt",
            CodeStatus.ERROR: "ошибки.txt",
            CodeStatus.SKIPPED: "пропущенные.txt",
            CodeStatus.WLID_TOKEN_ERROR: "проблемы_с_токенами.txt"
        }
        
        for status, filename in file_mapping.items():
            if grouped_results[status]:
                filepath = os.path.join(os.path.dirname(base_path), filename)
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        for result in grouped_results[status]:
                            f.write(f"{result.code}\n")
                    exported_files.append(filepath)
                except Exception as e:
                    raise Exception(f"Ошибка записи {filename}: {str(e)}")
        
        return exported_files
    
    def export_results_csv(self, results: List[CodeResult], filepath: str) -> None:
        """
        Exports the results to a CSV file.

        Args:
            results: A list of CodeResult objects.
            filepath: The path to the CSV file.
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Записываем заголовок
                writer.writerow(['Код', 'Статус', 'Время', 'Детали'])
                
                # Записываем данные
                status_translation = {
                    'valid': 'Рабочий',
                    'used': 'Использованный',
                    'invalid': 'Неверный',
                    'expired': 'Истекший',
                    'error': 'Ошибка',
                    'skipped': 'Пропущен'
                }
                
                for result in results:
                    writer.writerow([
                        result.code,
                        status_translation.get(result.status.value, result.status.value),
                        result.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        result.details or ''
                    ])
                    
        except Exception as e:
            raise Exception(f"Ошибка записи CSV файла: {str(e)}")
    
    def export_results_json(self, results: List[CodeResult], filepath: str, 
                           session_stats: Optional[Dict[str, Any]] = None) -> None:
        """
        Exports the results to a JSON file with metadata.

        Args:
            results: A list of CodeResult objects.
            filepath: The path to the JSON file.
            session_stats: Optional dictionary with session statistics.
        """
        try:
            export_data = {
                'время_экспорта': datetime.now().isoformat(),
                'всего_результатов': len(results),
                'статистика_сессии': session_stats or {},
                'результаты': [result.to_dict() for result in results]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise Exception(f"Ошибка записи JSON файла: {str(e)}")
    

    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Get information about a file"""
        if not os.path.exists(filepath):
            return {'exists': False}
        
        stat = os.stat(filepath)
        return {
            'exists': True,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'readable': os.access(filepath, os.R_OK)
        }
    
