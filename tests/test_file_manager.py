import os
import json
import csv
import unittest
from unittest.mock import patch, mock_open
from src.data.file_manager import FileManager
from src.data.models import WLIDToken, CodeResult, CodeStatus, AppConfig
from datetime import datetime

class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.file_manager = FileManager()
        self.test_wlid_content = 'WLID1.0="test_token_1"'
        self.test_codes_content = 'QHR663JVTVWGTVXJXW4QR767Z'

    def test_read_wlid_file_valid(self):
        with patch("builtins.open", mock_open(read_data=self.test_wlid_content)) as mock_file, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=len(self.test_wlid_content)):
            tokens, errors = self.file_manager.read_wlid_file("dummy_path.txt")
            self.assertEqual(len(tokens), 1)
            self.assertEqual(tokens[0].token, 'test_token_1')
            self.assertEqual(len(errors), 0)

    def test_read_wlid_file_with_errors(self):
        invalid_content = 'WLID1.0=""' # Empty token
        with patch("builtins.open", mock_open(read_data=invalid_content)) as mock_file, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=len(invalid_content)):
            tokens, errors = self.file_manager.read_wlid_file("dummy_path.txt")
            self.assertEqual(len(tokens), 0)
            self.assertEqual(len(errors), 2)
            self.assertIn("Пустой токен", errors[0])
            self.assertIn("В файле не найдено валидных WLID токенов", errors[1])

    def test_read_codes_file_valid(self):
        with patch("builtins.open", mock_open(read_data=self.test_codes_content)) as mock_file, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=len(self.test_codes_content)):
            codes, errors = self.file_manager.read_codes_file("dummy_path.txt")
            self.assertEqual(len(codes), 1)
            self.assertEqual(codes[0], 'QHR66-3JVTV-WGTVX-JXW4Q-R767Z')
            self.assertEqual(len(errors), 0)

    def test_read_codes_file_with_errors(self):
        invalid_content = 'invalid-code\\n'
        with patch("builtins.open", mock_open(read_data=invalid_content)) as mock_file, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=len(invalid_content)):
            codes, errors = self.file_manager.read_codes_file("dummy_path.txt")
            self.assertEqual(len(codes), 0)
            self.assertEqual(len(errors), 2)
            self.assertIn("Неверный формат кода", errors[0])
            self.assertIn("В файле не найдено валидных Xbox кодов", errors[1])

    def test_format_xbox_code(self):
        unformatted_code = "QHR663JVTVWGTVXJXW4QR767Z"
        formatted_code = "QHR66-3JVTV-WGTVX-JXW4Q-R767Z"
        self.assertEqual(self.file_manager.format_xbox_code(unformatted_code), formatted_code)

    def test_export_results_txt(self):
        results = [
            CodeResult("code1", CodeStatus.VALID, datetime.now()),
            CodeResult("code2", CodeStatus.USED, datetime.now()),
        ]
        with patch("builtins.open", mock_open()) as mock_file:
            exported_files = self.file_manager.export_results_txt(results, "dummy_path.txt")
            self.assertEqual(len(exported_files), 2)
            mock_file.assert_any_call(os.path.join(os.path.dirname("dummy_path.txt"), "рабочие.txt"), 'w', encoding='utf-8')
            mock_file.assert_any_call(os.path.join(os.path.dirname("dummy_path.txt"), "использованные.txt"), 'w', encoding='utf-8')

    def test_export_results_csv(self):
        results = [CodeResult("code1", CodeStatus.VALID, datetime.now(), "details")]
        m = mock_open()
        with patch("builtins.open", m) as mock_file:
            self.file_manager.export_results_csv(results, "dummy.csv")
            mock_file.assert_called_with("dummy.csv", 'w', newline='', encoding='utf-8')

            # The mock_open needs to be read to see what was written.
            # The following is a bit of a hack to get the written content.
            m.return_value.write.assert_any_call('Код,Статус,Время,Детали\r\n')
            m.return_value.write.assert_any_call('code1,Рабочий,{},details\r\n'.format(results[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')))

    def test_export_results_json(self):
        results = [CodeResult("code1", CodeStatus.VALID, datetime.now(), "details")]
        m = mock_open()
        with patch("builtins.open", m) as mock_file:
            self.file_manager.export_results_json(results, "dummy.json")
            mock_file.assert_called_with("dummy.json", 'w', encoding='utf-8')

            # Check the content of the json dump
            written_data = "".join(call.args[0] for call in m.return_value.write.call_args_list)
            data = json.loads(written_data)
            self.assertEqual(len(data['результаты']), 1)
            self.assertEqual(data['результаты'][0]['code'], 'code1')

if __name__ == '__main__':
    unittest.main()
