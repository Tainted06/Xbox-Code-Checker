"""
Unit tests for file size validation in FileManager
"""

import unittest
import tempfile
import os
from unittest.mock import patch

from src.data.file_manager import FileManager
from src.data.models import FileSizeError


class TestFileSizeValidation(unittest.TestCase):
    """Test cases for file size validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create FileManager with small limit for testing (1KB)
        self.file_manager = FileManager(max_file_size=1024)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests"""
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_file(self, content: str, filename: str = "test_file.txt") -> str:
        """Create a temporary file with given content"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def test_validate_file_size_valid_file(self):
        """Test validation of file within size limit"""
        # Create small file (under 1KB)
        small_content = "This is a small test file"
        filepath = self.create_temp_file(small_content)
        
        # Should not raise exception
        try:
            self.file_manager.validate_file_size(filepath)
        except FileSizeError:
            self.fail("validate_file_size raised FileSizeError for valid file")
    
    def test_validate_file_size_oversized_file(self):
        """Test validation of file exceeding size limit"""
        # Create large file (over 1KB)
        large_content = "X" * 2048  # 2KB content
        filepath = self.create_temp_file(large_content)
        
        # Should raise FileSizeError
        with self.assertRaises(FileSizeError) as context:
            self.file_manager.validate_file_size(filepath)
        
        error = context.exception
        self.assertEqual(error.filepath, filepath)
        self.assertGreater(error.file_size, 1024)
        self.assertEqual(error.max_size, 1024)
    
    def test_validate_file_size_nonexistent_file(self):
        """Test validation of non-existent file"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.txt")
        
        with self.assertRaises(FileNotFoundError):
            self.file_manager.validate_file_size(nonexistent_path)
    
    def test_file_size_error_message(self):
        """Test FileSizeError message formatting"""
        filepath = "/test/file.txt"
        file_size = 2 * 1024 * 1024  # 2MB
        max_size = 1 * 1024 * 1024   # 1MB
        
        error = FileSizeError(filepath, file_size, max_size)
        
        message = str(error)
        self.assertIn("file.txt", message)
        self.assertIn("2.0 МБ", message)
        self.assertIn("1.0 МБ", message)
        self.assertIn("слишком большой", message)
    
    def test_file_size_error_size_info(self):
        """Test FileSizeError size information"""
        filepath = "/test/file.txt"
        file_size = 2 * 1024 * 1024  # 2MB
        max_size = 1 * 1024 * 1024   # 1MB
        
        error = FileSizeError(filepath, file_size, max_size)
        size_info = error.get_size_info()
        
        expected_fields = [
            'filepath', 'file_size_bytes', 'file_size_mb',
            'max_size_bytes', 'max_size_mb', 'excess_bytes', 'excess_mb'
        ]
        
        for field in expected_fields:
            self.assertIn(field, size_info)
        
        self.assertEqual(size_info['filepath'], filepath)
        self.assertEqual(size_info['file_size_bytes'], file_size)
        self.assertEqual(size_info['file_size_mb'], 2.0)
        self.assertEqual(size_info['max_size_bytes'], max_size)
        self.assertEqual(size_info['max_size_mb'], 1.0)
        self.assertEqual(size_info['excess_bytes'], 1024 * 1024)
        self.assertEqual(size_info['excess_mb'], 1.0)
    
    def test_get_file_size_info_valid_file(self):
        """Test getting file size information for valid file"""
        content = "Test content"
        filepath = self.create_temp_file(content)
        
        info = self.file_manager.get_file_size_info(filepath)
        
        self.assertTrue(info['exists'])
        self.assertEqual(info['filepath'], filepath)
        self.assertIsInstance(info['size_bytes'], int)
        self.assertIsInstance(info['size_mb'], float)
        self.assertEqual(info['max_size_bytes'], 1024)
        self.assertEqual(info['max_size_mb'], 0.0)  # 1024 bytes = 0.0 MB (rounded)
        self.assertTrue(info['size_valid'])  # Small file should be valid
        self.assertIsInstance(info['usage_percent'], float)
    
    def test_get_file_size_info_oversized_file(self):
        """Test getting file size information for oversized file"""
        large_content = "X" * 2048  # 2KB content
        filepath = self.create_temp_file(large_content)
        
        info = self.file_manager.get_file_size_info(filepath)
        
        self.assertTrue(info['exists'])
        self.assertFalse(info['size_valid'])  # Large file should be invalid
        self.assertGreater(info['usage_percent'], 100)  # Should exceed 100%
    
    def test_get_file_size_info_nonexistent_file(self):
        """Test getting file size information for non-existent file"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.txt")
        
        info = self.file_manager.get_file_size_info(nonexistent_path)
        
        self.assertFalse(info['exists'])
        self.assertIn('error', info)
        self.assertIn("не найден", info['error'])
    
    def test_update_max_file_size(self):
        """Test updating maximum file size"""
        original_size = self.file_manager.max_file_size
        new_size = 2048
        
        self.file_manager.update_max_file_size(new_size)
        
        self.assertEqual(self.file_manager.max_file_size, new_size)
        self.assertNotEqual(self.file_manager.max_file_size, original_size)
    
    def test_update_max_file_size_invalid(self):
        """Test updating maximum file size with invalid value"""
        with self.assertRaises(ValueError):
            self.file_manager.update_max_file_size(0)
        
        with self.assertRaises(ValueError):
            self.file_manager.update_max_file_size(-100)
    
    def test_read_wlid_file_size_validation(self):
        """Test that read_wlid_file validates file size"""
        # Create oversized WLID file
        large_content = "WLID1.0=\"" + "X" * 2048 + "\""  # Large WLID token
        filepath = self.create_temp_file(large_content, "large_wlid.txt")
        
        tokens, errors = self.file_manager.read_wlid_file(filepath)
        
        self.assertEqual(len(tokens), 0)  # No tokens should be read
        self.assertEqual(len(errors), 1)  # Should have one error
        self.assertIn("слишком большой", errors[0])
    
    def test_read_codes_file_size_validation(self):
        """Test that read_codes_file validates file size"""
        # Create oversized codes file
        large_content = "\n".join(["XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"] * 100)  # Many codes
        filepath = self.create_temp_file(large_content, "large_codes.txt")
        
        codes, errors = self.file_manager.read_codes_file(filepath)
        
        self.assertEqual(len(codes), 0)  # No codes should be read
        self.assertEqual(len(errors), 1)  # Should have one error
        self.assertIn("слишком большой", errors[0])
    
    def test_read_wlid_file_valid_size(self):
        """Test that read_wlid_file works with valid file size"""
        # Create small WLID file
        content = 'WLID1.0="valid_token_123"'
        filepath = self.create_temp_file(content, "valid_wlid.txt")
        
        tokens, errors = self.file_manager.read_wlid_file(filepath)
        
        self.assertEqual(len(errors), 0)  # No errors
        self.assertEqual(len(tokens), 1)  # One token should be read
        self.assertEqual(tokens[0].token, 'WLID1.0="valid_token_123"')
    
    def test_read_codes_file_valid_size(self):
        """Test that read_codes_file works with valid file size"""
        # Create small codes file
        content = "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX\nYYYYY-YYYYY-YYYYY-YYYYY-YYYYY"
        filepath = self.create_temp_file(content, "valid_codes.txt")
        
        codes, errors = self.file_manager.read_codes_file(filepath)
        
        self.assertEqual(len(errors), 0)  # No errors
        self.assertEqual(len(codes), 2)  # Two codes should be read
        self.assertIn("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX", codes)
        self.assertIn("YYYYY-YYYYY-YYYYY-YYYYY-YYYYY", codes)
    
    def test_file_manager_with_default_size(self):
        """Test FileManager with default file size limit"""
        default_manager = FileManager()
        
        # Default should be 50MB
        self.assertEqual(default_manager.max_file_size, 50 * 1024 * 1024)
    
    def test_file_manager_with_custom_size(self):
        """Test FileManager with custom file size limit"""
        custom_size = 10 * 1024 * 1024  # 10MB
        custom_manager = FileManager(max_file_size=custom_size)
        
        self.assertEqual(custom_manager.max_file_size, custom_size)


if __name__ == '__main__':
    unittest.main()