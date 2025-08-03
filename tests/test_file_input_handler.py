"""
Unit tests for FileInputHandler component
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import customtkinter as ctk
import tempfile
import os

from src.gui.components.file_input_handler import FileInputHandler
from src.data.models import AppConfig, WLIDToken
from src.data.file_manager import FileManager


class TestFileInputHandler(unittest.TestCase):
    """Test cases for FileInputHandler component"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock parent frame
        self.mock_parent = Mock(spec=ctk.CTkFrame)
        
        # Create test config
        self.config = AppConfig()
        
        # Create mock file manager
        self.mock_file_manager = Mock(spec=FileManager)
        
        # Create FileInputHandler instance with comprehensive mocking
        with patch('src.gui.components.file_input_handler.ctk.CTkFrame') as mock_frame, \
             patch('src.gui.components.file_input_handler.ctk.CTkLabel') as mock_label, \
             patch('src.gui.components.file_input_handler.ctk.CTkButton') as mock_button, \
             patch('src.gui.components.file_input_handler.ctk.CTkFont') as mock_font:
            
            # Setup mock returns
            mock_frame.return_value = Mock()
            mock_label.return_value = Mock()
            mock_button.return_value = Mock()
            mock_font.return_value = Mock()
            
            self.handler = FileInputHandler(self.mock_parent, self.config, self.mock_file_manager)
    
    def test_initialization(self):
        """Test FileInputHandler initialization"""
        self.assertEqual(self.handler.parent_frame, self.mock_parent)
        self.assertEqual(self.handler.config, self.config)
        self.assertEqual(self.handler.file_manager, self.mock_file_manager)
        self.assertEqual(len(self.handler.wlid_tokens), 0)
        self.assertEqual(len(self.handler.codes), 0)
        self.assertIsNone(self.handler.wlid_loaded_callback)
        self.assertIsNone(self.handler.codes_loaded_callback)
    
    def test_has_wlid_tokens(self):
        """Test has_wlid_tokens method"""
        # Initially should be False
        self.assertFalse(self.handler.has_wlid_tokens())
        
        # Add some tokens
        self.handler.wlid_tokens = [Mock(spec=WLIDToken)]
        self.assertTrue(self.handler.has_wlid_tokens())
    
    def test_has_codes(self):
        """Test has_codes method"""
        # Initially should be False
        self.assertFalse(self.handler.has_codes())
        
        # Add some codes
        self.handler.codes = ["test-code-1", "test-code-2"]
        self.assertTrue(self.handler.has_codes())
    
    def test_get_wlid_tokens(self):
        """Test get_wlid_tokens returns copy"""
        test_tokens = [Mock(spec=WLIDToken), Mock(spec=WLIDToken)]
        self.handler.wlid_tokens = test_tokens
        
        returned_tokens = self.handler.get_wlid_tokens()
        
        # Should return copy, not same list
        self.assertEqual(returned_tokens, test_tokens)
        self.assertIsNot(returned_tokens, test_tokens)
    
    def test_get_codes(self):
        """Test get_codes returns copy"""
        test_codes = ["code1", "code2", "code3"]
        self.handler.codes = test_codes
        
        returned_codes = self.handler.get_codes()
        
        # Should return copy, not same list
        self.assertEqual(returned_codes, test_codes)
        self.assertIsNot(returned_codes, test_codes)
    
    def test_clear_wlid_tokens(self):
        """Test clearing WLID tokens"""
        # Add some tokens first
        self.handler.wlid_tokens = [Mock(spec=WLIDToken)]
        self.handler.wlid_label = Mock()
        
        # Clear tokens
        self.handler.clear_wlid_tokens()
        
        # Should be empty and label updated
        self.assertEqual(len(self.handler.wlid_tokens), 0)
        self.handler.wlid_label.configure.assert_called_with(text="WLID файл не загружен")
    
    def test_clear_codes(self):
        """Test clearing codes"""
        # Add some codes first
        self.handler.codes = ["code1", "code2"]
        self.handler.codes_label = Mock()
        
        # Clear codes
        self.handler.clear_codes()
        
        # Should be empty and label updated
        self.assertEqual(len(self.handler.codes), 0)
        self.handler.codes_label.configure.assert_called_with(text="Файл кодов не загружен")
    
    def test_clear_all(self):
        """Test clearing all data"""
        # Add some data first
        self.handler.wlid_tokens = [Mock(spec=WLIDToken)]
        self.handler.codes = ["code1"]
        self.handler.wlid_label = Mock()
        self.handler.codes_label = Mock()
        
        # Clear all
        self.handler.clear_all()
        
        # Both should be empty
        self.assertEqual(len(self.handler.wlid_tokens), 0)
        self.assertEqual(len(self.handler.codes), 0)
    
    def test_set_enabled(self):
        """Test enabling/disabling controls"""
        self.handler.wlid_button = Mock()
        self.handler.codes_button = Mock()
        
        # Test enabling
        self.handler.set_enabled(True)
        self.handler.wlid_button.configure.assert_called_with(state="normal")
        self.handler.codes_button.configure.assert_called_with(state="normal")
        
        # Test disabling
        self.handler.set_enabled(False)
        self.handler.wlid_button.configure.assert_called_with(state="disabled")
        self.handler.codes_button.configure.assert_called_with(state="disabled")
    
    def test_set_callbacks(self):
        """Test setting callbacks"""
        wlid_callback = Mock()
        codes_callback = Mock()
        
        self.handler.set_wlid_loaded_callback(wlid_callback)
        self.handler.set_codes_loaded_callback(codes_callback)
        
        self.assertEqual(self.handler.wlid_loaded_callback, wlid_callback)
        self.assertEqual(self.handler.codes_loaded_callback, codes_callback)
    
    @patch('src.gui.components.file_input_handler.filedialog.askopenfilename')
    @patch('src.gui.components.file_input_handler.os.path.exists')
    @patch('src.gui.components.file_input_handler.os.path.isfile')
    @patch('src.gui.components.file_input_handler.os.access')
    def test_load_wlid_file_success(self, mock_access, mock_isfile, mock_exists, mock_filedialog):
        """Test successful WLID file loading"""
        # Setup mocks
        test_file_path = "/test/path/wlid.txt"
        test_tokens = [Mock(spec=WLIDToken), Mock(spec=WLIDToken)]
        
        mock_filedialog.return_value = test_file_path
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        self.mock_file_manager.read_wlid_file.return_value = (test_tokens, [])
        
        # Setup UI mocks
        self.handler.wlid_label = Mock()
        
        # Setup callback
        callback_mock = Mock()
        self.handler.set_wlid_loaded_callback(callback_mock)
        
        # Load file
        self.handler.load_wlid_file()
        
        # Verify results
        self.assertEqual(self.handler.wlid_tokens, test_tokens)
        self.assertEqual(self.config.last_wlid_path, test_file_path)
        self.handler.wlid_label.configure.assert_called_with(text=f"Загружено {len(test_tokens)} WLID токенов")
        callback_mock.assert_called_once_with(test_tokens)
    
    @patch('src.gui.components.file_input_handler.filedialog.askopenfilename')
    @patch('src.gui.components.file_input_handler.os.path.exists')
    @patch('src.gui.components.file_input_handler.os.path.isfile')
    @patch('src.gui.components.file_input_handler.os.access')
    @patch('src.gui.components.file_input_handler.messagebox.showwarning')
    def test_load_wlid_file_with_errors(self, mock_showwarning, mock_access, mock_isfile, mock_exists, mock_filedialog):
        """Test WLID file loading with parsing errors"""
        # Setup mocks
        test_file_path = "/test/path/wlid.txt"
        test_tokens = [Mock(spec=WLIDToken)]
        test_errors = ["Error 1", "Error 2", "Error 3"]
        
        mock_filedialog.return_value = test_file_path
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        self.mock_file_manager.read_wlid_file.return_value = (test_tokens, test_errors)
        
        # Setup UI mocks
        self.handler.wlid_label = Mock()
        
        # Load file
        self.handler.load_wlid_file()
        
        # Verify error dialog was shown
        mock_showwarning.assert_called_once()
        args, kwargs = mock_showwarning.call_args
        self.assertIn("Ошибки в WLID файле", args[0])
        
        # Verify tokens were still loaded
        self.assertEqual(self.handler.wlid_tokens, test_tokens)
    
    @patch('src.gui.components.file_input_handler.filedialog.askopenfilename')
    @patch('src.gui.components.file_input_handler.os.path.exists')
    @patch('src.gui.components.file_input_handler.messagebox.showerror')
    def test_load_wlid_file_not_found(self, mock_showerror, mock_exists, mock_filedialog):
        """Test WLID file loading when file doesn't exist"""
        # Setup mocks
        test_file_path = "/test/path/nonexistent.txt"
        
        mock_filedialog.return_value = test_file_path
        mock_exists.return_value = False
        
        # Load file
        self.handler.load_wlid_file()
        
        # Verify error dialog was shown
        mock_showerror.assert_called_once()
        args, kwargs = mock_showerror.call_args
        self.assertEqual(args[0], "Ошибка")
        self.assertIn("Файл не найден", args[1])
    
    @patch('src.gui.components.file_input_handler.filedialog.askopenfilename')
    @patch('src.gui.components.file_input_handler.os.path.exists')
    @patch('src.gui.components.file_input_handler.os.path.isfile')
    @patch('src.gui.components.file_input_handler.os.access')
    def test_load_codes_file_success(self, mock_access, mock_isfile, mock_exists, mock_filedialog):
        """Test successful codes file loading"""
        # Setup mocks
        test_file_path = "/test/path/codes.txt"
        test_codes = ["code1", "code2", "code3"]
        
        mock_filedialog.return_value = test_file_path
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        self.mock_file_manager.read_codes_file.return_value = (test_codes, [])
        
        # Setup UI mocks
        self.handler.codes_label = Mock()
        
        # Setup callback
        callback_mock = Mock()
        self.handler.set_codes_loaded_callback(callback_mock)
        
        # Load file
        self.handler.load_codes_file()
        
        # Verify results
        self.assertEqual(self.handler.codes, test_codes)
        self.assertEqual(self.config.last_codes_path, test_file_path)
        self.handler.codes_label.configure.assert_called_with(text=f"Загружено {len(test_codes)} кодов")
        callback_mock.assert_called_once_with(test_codes)
    
    @patch('src.gui.components.file_input_handler.filedialog.askopenfilename')
    def test_load_file_cancelled(self, mock_filedialog):
        """Test file loading when user cancels dialog"""
        # Setup mocks - user cancels dialog
        mock_filedialog.return_value = ""
        
        # Load file
        self.handler.load_wlid_file()
        
        # Should not call file manager
        self.mock_file_manager.read_wlid_file.assert_not_called()
    
    @patch('src.gui.components.file_input_handler.filedialog.askopenfilename')
    @patch('src.gui.components.file_input_handler.os.path.exists')
    @patch('src.gui.components.file_input_handler.os.path.isfile')
    @patch('src.gui.components.file_input_handler.os.access')
    @patch('src.gui.components.file_input_handler.messagebox.showerror')
    def test_load_file_exception_handling(self, mock_showerror, mock_access, mock_isfile, mock_exists, mock_filedialog):
        """Test exception handling during file loading"""
        # Setup mocks
        test_file_path = "/test/path/wlid.txt"
        
        mock_filedialog.return_value = test_file_path
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        self.mock_file_manager.read_wlid_file.side_effect = Exception("Test exception")
        
        # Load file
        self.handler.load_wlid_file()
        
        # Verify error dialog was shown
        mock_showerror.assert_called_once()
        args, kwargs = mock_showerror.call_args
        self.assertEqual(args[0], "Ошибка")
        self.assertIn("Не удалось загрузить WLID файл", args[1])


if __name__ == '__main__':
    unittest.main()