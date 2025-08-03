"""
Main window for Xbox Code Checker GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from typing import Optional, List, Dict, Any

from ..data.models import AppConfig, WLIDToken, CodeResult, CodeStatus, SessionStatus
from ..data.file_manager import FileManager
from ..core.code_checker import CodeChecker
from ..core.progress_manager import ProgressManager
from .settings_dialog import SettingsDialog
from .wlid_manager_dialog import WLIDManagerDialog
from .components.file_input_handler import FileInputHandler
from .components.progress_display_manager import ProgressDisplayManager
from .components.results_display_manager import ResultsDisplayManager


class MainWindow:
    """Main application window"""
    
    def __init__(self, root: ctk.CTk, config: AppConfig, file_manager: FileManager):
        self.root = root
        self.config = config
        self.file_manager = file_manager
        
        # Initialize components
        self.code_checker: Optional[CodeChecker] = None
        self.progress_manager = ProgressManager()
        self.settings_dialog: Optional[SettingsDialog] = None
        self.wlid_manager_dialog: Optional[WLIDManagerDialog] = None
        self.file_input_handler: Optional[FileInputHandler] = None
        self.progress_display_manager: Optional[ProgressDisplayManager] = None
        self.results_display_manager: Optional[ResultsDisplayManager] = None
        
        # Data
        self.wlid_tokens: List[WLIDToken] = []
        self.codes: List[str] = []
        self.current_results: List[CodeResult] = []
        
        # GUI elements
        self.main_frame: Optional[ctk.CTkFrame] = None
        self.progress_frame: Optional[ctk.CTkFrame] = None
        self.results_frame: Optional[ctk.CTkFrame] = None
        self.control_frame: Optional[ctk.CTkFrame] = None
        
        # Control elements
        self.start_button: Optional[ctk.CTkButton] = None
        self.pause_button: Optional[ctk.CTkButton] = None
        self.stop_button: Optional[ctk.CTkButton] = None
        self.settings_button: Optional[ctk.CTkButton] = None
        self.export_button: Optional[ctk.CTkButton] = None
        
        # Results elements (will be managed by ResultsDisplayManager)
        self.results_tabview: Optional[ctk.CTkTabview] = None
        
        # Setup UI
        self.setup_ui()
        
        # Setup callbacks (after UI is created)
        self.setup_callbacks()
    
    def setup_ui(self) -> None:
        """Setup the user interface"""
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create sections
        self.create_file_input_section()
        self.create_progress_section()
        self.create_control_buttons()
        self.create_results_section()
    
    def create_file_input_section(self) -> None:
        """Создает секцию загрузки файлов"""
        # Create file input frame
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Initialize FileInputHandler component
        self.file_input_handler = FileInputHandler(
            parent_frame=file_frame,
            file_manager=self.file_manager,
            config=self.config
        )
        
        # Set up callbacks for file loading
        self.file_input_handler.set_wlid_loaded_callback(self.on_wlid_loaded)
        self.file_input_handler.set_codes_loaded_callback(self.on_codes_loaded)
    
    def create_progress_section(self) -> None:
        """Создает секцию отслеживания прогресса"""
        # Create progress frame
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(fill="x", padx=10, pady=5)
        
        # Initialize ProgressDisplayManager component
        self.progress_display_manager = ProgressDisplayManager(
            parent_frame=self.progress_frame,
            update_interval=0.1  # 100ms update interval
        )
    

    
    def create_control_buttons(self) -> None:
        """Создает кнопки управления"""
        # Фрейм управления
        self.control_frame = ctk.CTkFrame(self.main_frame)
        self.control_frame.pack(fill="x", padx=10, pady=5)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            self.control_frame,
            text="Управление",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Фрейм кнопок
        buttons_frame = ctk.CTkFrame(self.control_frame)
        buttons_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Кнопка запуска
        self.start_button = ctk.CTkButton(
            buttons_frame,
            text="Начать проверку",
            command=self.start_checking,
            width=140,
            fg_color="#00aa00",
            hover_color="#00cc00"
        )
        self.start_button.pack(side="left", padx=5, pady=10)
        
        # Кнопка паузы
        self.pause_button = ctk.CTkButton(
            buttons_frame,
            text="Пауза",
            command=self.pause_checking,
            width=100,
            fg_color="#ffaa00",
            hover_color="#ffcc00",
            state="disabled"
        )
        self.pause_button.pack(side="left", padx=5, pady=10)
        
        # Кнопка остановки
        self.stop_button = ctk.CTkButton(
            buttons_frame,
            text="Стоп",
            command=self.stop_checking,
            width=100,
            fg_color="#aa0000",
            hover_color="#cc0000",
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5, pady=10)
        
        # Кнопка настроек
        self.settings_button = ctk.CTkButton(
            buttons_frame,
            text="Настройки",
            command=self.open_settings,
            width=100
        )
        self.settings_button.pack(side="right", padx=5, pady=10)
        
        # Кнопка управления WLID токенами
        self.wlid_manager_button = ctk.CTkButton(
            buttons_frame,
            text="WLID токены",
            command=self.open_wlid_manager,
            width=120
        )
        self.wlid_manager_button.pack(side="right", padx=5, pady=10)
        
        # Кнопка экспорта
        self.export_button = ctk.CTkButton(
            buttons_frame,
            text="Экспорт результатов",
            command=self.export_results,
            width=140,
            state="disabled"
        )
        self.export_button.pack(side="right", padx=5, pady=10)
    
    def create_results_section(self) -> None:
        """Создает секцию отображения результатов"""
        # Фрейм результатов
        self.results_frame = ctk.CTkFrame(self.main_frame)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Initialize ResultsDisplayManager component
        self.results_display_manager = ResultsDisplayManager(
            parent_frame=self.results_frame
        )
        
        # Set up callbacks for result interactions
        self.results_display_manager.set_result_selected_callback(self.on_result_selected)
        self.results_display_manager.set_result_double_clicked_callback(self.on_result_double_clicked)
    
    def setup_callbacks(self) -> None:
        """Setup progress manager callbacks"""
        # Bridge between ProgressManager and ProgressDisplayManager
        if self.progress_display_manager:
            self.progress_manager.add_progress_callback(self._on_progress_update)
            self.progress_manager.add_status_callback(self.progress_display_manager.update_status)
    
    def _on_progress_update(self, progress_info: Dict[str, Any]) -> None:
        """Bridge method to convert progress manager data to display manager format"""
        # The ProgressDisplayManager will be updated directly by individual CodeResult updates
        # This callback is mainly for other potential uses
        pass
    
    def on_wlid_loaded(self, tokens: List[WLIDToken]) -> None:
        """Callback when WLID tokens are loaded"""
        self.wlid_tokens = tokens
        
        # Update WLID manager button state
        if tokens:
            self.wlid_manager_button.configure(
                text=f"WLID токены ({len(tokens)})",
                fg_color="#0078d4",
                hover_color="#106ebe"
            )
        else:
            self.wlid_manager_button.configure(
                text="WLID токены",
                fg_color="#1f538d",
                hover_color="#14375e"
            )
    
    def on_codes_loaded(self, codes: List[str]) -> None:
        """Callback when codes are loaded"""
        self.codes = codes
    
    def start_checking(self) -> None:
        """Запускает процесс проверки кодов"""
        if not self.wlid_tokens:
            messagebox.showerror("Ошибка", "Сначала загрузите WLID токены")
            return
        
        if not self.codes:
            messagebox.showerror("Ошибка", "Сначала загрузите коды")
            return
        
        # Очищаем предыдущие результаты
        self.current_results.clear()
        if self.results_display_manager:
            self.results_display_manager.clear_results()
        
        # Инициализируем проверщик кодов
        self.code_checker = CodeChecker(
            self.wlid_tokens,
            max_threads=self.config.max_threads,
            request_delay=self.config.request_delay
        )
        
        # Устанавливаем колбэки
        self.code_checker.set_progress_callback(self.on_code_checked)
        self.code_checker.set_status_callback(self.on_status_update)
        self.code_checker.set_completion_callback(self.on_checking_completed)
        
        # Update WLID manager button to show it's available
        self.update_wlid_button_status()
        
        # Запускаем менеджер прогресса и дисплей
        self.progress_manager.start_session(len(self.codes))
        if self.progress_display_manager:
            self.progress_display_manager.start_session(len(self.codes))
        
        # Обновляем состояние кнопок
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Пауза")
        self.stop_button.configure(state="normal")
        
        # Start checking in separate thread
        checking_thread = threading.Thread(
            target=self.code_checker.check_codes_batch,
            args=(self.codes,),
            daemon=True
        )
        checking_thread.start()
    
    def pause_checking(self) -> None:
        """Приостанавливает или возобновляет процесс проверки"""
        if not self.code_checker:
            return
        
        if self.code_checker.session.status.value == "running":
            if self.code_checker.pause_checking():
                self.pause_button.configure(text="Продолжить")
                self.progress_manager.pause_session()
                if self.progress_display_manager:
                    self.progress_display_manager.pause_session()
        else:
            if self.code_checker.resume_checking():
                self.pause_button.configure(text="Пауза")
                self.progress_manager.resume_session()
                if self.progress_display_manager:
                    self.progress_display_manager.resume_session()
    
    def stop_checking(self) -> None:
        """Останавливает процесс проверки"""
        if self.code_checker:
            self.code_checker.stop_checking()
            self.progress_manager.stop_session()
            if self.progress_display_manager:
                self.progress_display_manager.stop_session()
        
        # Обновляем состояние кнопок
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Пауза")
        self.stop_button.configure(state="disabled")
        self.export_button.configure(state="normal" if self.current_results else "disabled")
    
    def on_code_checked(self, result: CodeResult) -> None:
        """Handle a code being checked"""
        # Only add final results (not RATE_LIMITED, PENDING, or WLID_TOKEN_ERROR)
        if result.status not in [CodeStatus.RATE_LIMITED, CodeStatus.PENDING, CodeStatus.WLID_TOKEN_ERROR]:
            self.current_results.append(result)
        
        # Update progress manager
        self.progress_manager.update_progress(result)
        
        # Update progress display manager directly with the result
        if self.progress_display_manager:
            self.progress_display_manager.update_progress(result)
        
        # Update results display using ResultsDisplayManager
        if self.results_display_manager:
            self.results_display_manager.add_result(result)
    
    def on_status_update(self, status: str) -> None:
        """Handle status updates"""
        # This will be handled by progress manager callbacks
        pass
    
    def on_checking_completed(self) -> None:
        """Обрабатывает завершение проверки"""
        # Schedule GUI updates on main thread
        self.root.after(0, self._handle_completion_on_main_thread)
    
    def _handle_completion_on_main_thread(self) -> None:
        """Handle completion on main thread for GUI updates"""
        # Mark progress as completed
        if self.progress_display_manager:
            self.progress_display_manager.complete_session()
        
        # Обновляем состояние кнопок
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Пауза")
        self.stop_button.configure(state="disabled")
        self.export_button.configure(state="normal")
        
        # Получаем статистику
        stats = self.progress_manager.get_statistics_summary()
        
        # Автосохранение если включено в настройках
        if self.config.auto_save and self.current_results:
            try:
                # Создаем резервную копию результатов
                backup_path = self.file_manager.backup_results(self.current_results, stats)
                auto_save_message = f"\n\nРезультаты автоматически сохранены в:\n{backup_path}"
            except Exception as e:
                auto_save_message = f"\n\nОшибка автосохранения: {str(e)}"
        else:
            auto_save_message = ""
        
        # Показываем сообщение о завершении
        message = (f"Проверка завершена!\n\n"
                  f"Всего: {stats['total']}\n"
                  f"Рабочие: {stats['valid']}\n"
                  f"Использованные: {stats['used']}\n"
                  f"Неверные: {stats['invalid']}\n"
                  f"Ошибки: {stats['error']}\n"
                  f"Пропущены: {stats.get('skipped', 0)}")
        
        messagebox.showinfo("Завершено", message + auto_save_message)
    

    
    def on_result_selected(self, result: CodeResult) -> None:
        """Handle result selection"""
        # Could be used for showing detailed information about selected result
        pass
    
    def on_result_double_clicked(self, result: CodeResult) -> None:
        """Handle result double click"""
        # Could be used for copying code to clipboard or showing details
        pass
    
    def open_settings(self) -> None:
        """Open settings dialog"""
        if self.settings_dialog is None or not self.settings_dialog.winfo_exists():
            self.settings_dialog = SettingsDialog(self.root, self.config)
            self.settings_dialog.set_apply_callback(self.apply_settings)
    
    def open_wlid_manager(self) -> None:
        """Open WLID tokens manager dialog"""
        if not self.code_checker:
            messagebox.showwarning("Предупреждение", "Сначала загрузите WLID токены и запустите проверку")
            return
        
        if self.wlid_manager_dialog is None or not hasattr(self.wlid_manager_dialog, 'dialog') or not self.wlid_manager_dialog.dialog.winfo_exists():
            self.wlid_manager_dialog = WLIDManagerDialog(
                self.root, 
                self.code_checker,
                self.file_manager,
                self.file_input_handler
            )
            self.wlid_manager_dialog.set_tokens_updated_callback(self.on_tokens_updated)
        else:
            self.wlid_manager_dialog.show()
    
    def on_tokens_updated(self) -> None:
        """Handle tokens being updated in manager"""
        # Refresh any UI elements that depend on token count
        if self.wlid_manager_dialog:
            self.wlid_manager_dialog.refresh_data()
        
        # Update button status
        self.update_wlid_button_status()
    
    def update_wlid_button_status(self) -> None:
        """Update WLID manager button status based on tokens"""
        if not self.code_checker:
            return
        
        try:
            tokens_status = self.code_checker.get_wlid_tokens_status()
            summary = tokens_status['summary']
            
            total = summary['total']
            invalid = summary['invalid']
            available = summary['available']
            
            if total == 0:
                self.wlid_manager_button.configure(
                    text="WLID токены",
                    fg_color="#1f538d",
                    hover_color="#14375e"
                )
            elif invalid > 0:
                self.wlid_manager_button.configure(
                    text=f"WLID токены ({available}/{total})",
                    fg_color="#cc4400",
                    hover_color="#dd5500"
                )
            else:
                self.wlid_manager_button.configure(
                    text=f"WLID токены ({total})",
                    fg_color="#00aa00",
                    hover_color="#00cc00"
                )
        except Exception:
            # Fallback if there's an error
            self.wlid_manager_button.configure(
                text="WLID токены",
                fg_color="#1f538d",
                hover_color="#14375e"
            )
    
    def apply_settings(self, new_config: AppConfig) -> None:
        """Apply new settings"""
        # Update config
        old_theme = self.config.theme
        self.config = new_config
        
        # Apply theme change
        if old_theme != new_config.theme:
            ctk.set_appearance_mode(new_config.theme)
        
        # Update code checker settings if active
        if self.code_checker:
            self.code_checker.update_settings(
                max_threads=new_config.max_threads,
                request_delay=new_config.request_delay
            )
    
    def export_results(self) -> None:
        """Экспорт результатов в файл"""
        # Get results from ResultsDisplayManager
        if self.results_display_manager:
            export_results = self.results_display_manager.get_all_results()
        else:
            export_results = self.current_results
            
        if not export_results:
            messagebox.showwarning("Предупреждение", "Нет результатов для экспорта")
            return
        
        # Запрашиваем формат экспорта
        format_dialog = ExportFormatDialog(self.root)
        export_format = format_dialog.get_format()
        
        if not export_format:
            return
        
        try:
            if export_format == "txt":
                file_path = filedialog.asksaveasfilename(
                    title="Экспорт результатов",
                    defaultextension=".txt",
                    filetypes=[("Текстовые файлы", "*.txt")],
                    initialdir="output"
                )
                if file_path:
                    exported_files = self.file_manager.export_results_txt(export_results, file_path)
                    messagebox.showinfo("Успешно", f"Результаты экспортированы в {len(exported_files)} файлов")
            
            elif export_format == "csv":
                file_path = filedialog.asksaveasfilename(
                    title="Экспорт результатов",
                    defaultextension=".csv",
                    filetypes=[("CSV файлы", "*.csv")],
                    initialdir="output"
                )
                if file_path:
                    self.file_manager.export_results_csv(export_results, file_path)
                    messagebox.showinfo("Успешно", f"Результаты экспортированы в {file_path}")
            
            elif export_format == "json":
                file_path = filedialog.asksaveasfilename(
                    title="Экспорт результатов",
                    defaultextension=".json",
                    filetypes=[("JSON файлы", "*.json")],
                    initialdir="output"
                )
                if file_path:
                    stats = self.progress_manager.get_statistics_summary()
                    self.file_manager.export_results_json(export_results, file_path, stats)
                    messagebox.showinfo("Успешно", f"Результаты экспортированы в {file_path}")
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать результаты: {str(e)}")
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        if self.code_checker:
            self.code_checker.cleanup()
        if self.progress_display_manager:
            self.progress_display_manager.cleanup()
        if self.file_input_handler and hasattr(self.file_input_handler, 'cleanup'):
            self.file_input_handler.cleanup()
        if self.results_display_manager:
            self.results_display_manager.cleanup()


class ExportFormatDialog:
    """Простой диалог для выбора формата экспорта"""
    
    def __init__(self, parent):
        self.result = None
        
        # Создаем диалог
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Формат экспорта")
        self.dialog.geometry("350x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрируем диалог
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 175
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 125
        self.dialog.geometry(f"350x250+{x}+{y}")
        
        # Создаем содержимое
        label = ctk.CTkLabel(self.dialog, text="Выберите формат экспорта:", font=ctk.CTkFont(size=14))
        label.pack(pady=20)
        
        # Кнопки форматов
        txt_btn = ctk.CTkButton(self.dialog, text="TXT (Отдельные файлы)", command=lambda: self.select_format("txt"))
        txt_btn.pack(pady=5)
        
        csv_btn = ctk.CTkButton(self.dialog, text="CSV (Один файл)", command=lambda: self.select_format("csv"))
        csv_btn.pack(pady=5)
        
        json_btn = ctk.CTkButton(self.dialog, text="JSON (С метаданными)", command=lambda: self.select_format("json"))
        json_btn.pack(pady=5)
        
        cancel_btn = ctk.CTkButton(self.dialog, text="Отмена", command=self.dialog.destroy)
        cancel_btn.pack(pady=10)
    
    def select_format(self, format_type: str) -> None:
        """Выбрать формат экспорта"""
        self.result = format_type
        self.dialog.destroy()
    
    def get_format(self) -> Optional[str]:
        """Получить выбранный формат"""
        self.dialog.wait_window()
        return self.result