"""
Settings dialog for Xbox Code Checker GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable, Dict, Any

from ..data.models import AppConfig
from ..utils.localization import _


class SettingsDialog:
    """Advanced settings dialog with multiple categories"""
    
    def __init__(self, parent, config: AppConfig):
        self.parent = parent
        self.config = config.to_dict()  # Work with a copy
        self.original_config = config
        
        # Callbacks
        self.apply_callback: Optional[Callable[[AppConfig], None]] = None
        
        # UI variables
        self.theme_var = tk.StringVar(value=self.config['theme'])
        self.request_delay_var = tk.DoubleVar(value=self.config['request_delay'])
        self.max_threads_var = tk.IntVar(value=self.config['max_threads'])
        self.auto_save_var = tk.BooleanVar(value=self.config['auto_save'])
        self.export_format_var = tk.StringVar(value=self.config['export_format'])
        
        # Create dialog
        self.create_dialog()
    
    def create_dialog(self) -> None:
        """Создает диалог настроек"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(_("settings_dialog.title"))
        self.dialog.geometry("600x700")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Центрируем диалог
        self.center_dialog()
        
        # Настраиваем UI
        self.setup_ui()
    
    def center_dialog(self) -> None:
        """Center dialog on parent"""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 300
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 350
        self.dialog.geometry(f"600x700+{x}+{y}")
    
    def setup_ui(self) -> None:
        """Setup dialog UI"""
        # Заголовок
        title_label = ctk.CTkLabel(
            self.dialog,
            text=_("settings_dialog.title"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Создаем вкладки для разных категорий настроек
        self.tabview = ctk.CTkTabview(self.dialog)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Добавляем вкладки
        self.tabview.add(_("settings_dialog.appearance_tab"))
        self.tabview.add(_("settings_dialog.performance_tab"))
        self.tabview.add(_("settings_dialog.export_tab"))
        
        # Настраиваем каждую вкладку
        self.setup_appearance_tab()
        self.setup_performance_tab()
        self.setup_export_tab()
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.dialog)
        buttons_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # Кнопка применить
        apply_button = ctk.CTkButton(
            buttons_frame,
            text=_("settings_dialog.apply_button"),
            command=self.apply_settings,
            width=100,
            height=35,
            fg_color="#00aa00",
            hover_color="#00cc00",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        apply_button.pack(side="right", padx=(5, 10), pady=10)
        
        # Кнопка отмены
        cancel_button = ctk.CTkButton(
            buttons_frame,
            text=_("settings_dialog.cancel_button"),
            command=self.dialog.destroy,
            width=100,
            height=35
        )
        cancel_button.pack(side="right", padx=5, pady=10)
        
        # Кнопка сброса
        reset_button = ctk.CTkButton(
            buttons_frame,
            text=_("settings_dialog.reset_button"),
            command=self.reset_to_defaults,
            width=140,
            height=35,
            fg_color="#aa0000",
            hover_color="#cc0000"
        )
        reset_button.pack(side="left", padx=10, pady=10)
    
    def setup_appearance_tab(self) -> None:
        """Настраивает вкладку внешнего вида"""
        tab = self.tabview.tab(_("settings_dialog.appearance_tab"))
        
        # Theme section
        theme_frame = ctk.CTkFrame(tab)
        theme_frame.pack(fill="x", padx=10, pady=10)
        
        theme_title = ctk.CTkLabel(
            theme_frame,
            text=_("settings_dialog.theme_title"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        theme_title.pack(pady=(15, 10))
        
        # Выбор темы
        theme_options_frame = ctk.CTkFrame(theme_frame)
        theme_options_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        dark_radio = ctk.CTkRadioButton(
            theme_options_frame,
            text=_("settings_dialog.dark_theme"),
            variable=self.theme_var,
            value="dark"
        )
        dark_radio.pack(side="left", padx=20, pady=10)
        
        light_radio = ctk.CTkRadioButton(
            theme_options_frame,
            text=_("settings_dialog.light_theme"),
            variable=self.theme_var,
            value="light"
        )
        light_radio.pack(side="left", padx=20, pady=10)
        
        system_radio = ctk.CTkRadioButton(
            theme_options_frame,
            text=_("settings_dialog.system_theme"),
            variable=self.theme_var,
            value="system"
        )
        system_radio.pack(side="left", padx=20, pady=10)

        # Language section
        language_frame = ctk.CTkFrame(tab)
        language_frame.pack(fill="x", padx=10, pady=10)

        language_title = ctk.CTkLabel(
            language_frame,
            text=_("settings_dialog.language_title"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        language_title.pack(pady=(15, 10))

        language_options_frame = ctk.CTkFrame(language_frame)
        language_options_frame.pack(fill="x", padx=15, pady=(5, 15))

        from ...utils.localization import localization_manager
        self.language_var = tk.StringVar(value=self.config['language'])
        language_menu = ctk.CTkOptionMenu(
            language_options_frame,
            variable=self.language_var,
            values=localization_manager.get_available_languages()
        )
        language_menu.pack(pady=10)
    
    def setup_performance_tab(self) -> None:
        """Настраивает вкладку производительности"""
        tab = self.tabview.tab(_("settings_dialog.performance_tab"))
        
        # Request settings
        request_frame = ctk.CTkFrame(tab)
        request_frame.pack(fill="x", padx=10, pady=10)
        
        request_title = ctk.CTkLabel(
            request_frame,
            text=_("settings_dialog.request_settings_title"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        request_title.pack(pady=(15, 10))
        
        # Задержка запросов
        delay_frame = ctk.CTkFrame(request_frame)
        delay_frame.pack(fill="x", padx=15, pady=5)
        
        delay_label = ctk.CTkLabel(
            delay_frame,
            text=_("settings_dialog.request_delay_label"),
            font=ctk.CTkFont(size=12)
        )
        delay_label.pack(side="left", padx=10, pady=10)
        
        self.delay_slider = ctk.CTkSlider(
            delay_frame,
            from_=0.1,
            to=5.0,
            number_of_steps=49,
            variable=self.request_delay_var,
            command=self.update_delay_label
        )
        self.delay_slider.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        
        self.delay_value_label = ctk.CTkLabel(
            delay_frame,
            text=f"{self.request_delay_var.get():.1f}s",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=50
        )
        self.delay_value_label.pack(side="right", padx=10, pady=10)
        
        # Threading settings
        thread_frame = ctk.CTkFrame(tab)
        thread_frame.pack(fill="x", padx=10, pady=10)
        
        thread_title = ctk.CTkLabel(
            thread_frame,
            text=_("settings_dialog.threading_settings_title"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        thread_title.pack(pady=(15, 10))
        
        # Максимум потоков
        threads_frame = ctk.CTkFrame(thread_frame)
        threads_frame.pack(fill="x", padx=15, pady=5)
        
        threads_label = ctk.CTkLabel(
            threads_frame,
            text=_("settings_dialog.max_threads_label"),
            font=ctk.CTkFont(size=12)
        )
        threads_label.pack(side="left", padx=10, pady=10)
        
        self.threads_slider = ctk.CTkSlider(
            threads_frame,
            from_=1,
            to=20,
            number_of_steps=19,
            variable=self.max_threads_var,
            command=self.update_threads_label
        )
        self.threads_slider.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        
        self.threads_value_label = ctk.CTkLabel(
            threads_frame,
            text=str(self.max_threads_var.get()),
            font=ctk.CTkFont(size=12, weight="bold"),
            width=50
        )
        self.threads_value_label.pack(side="right", padx=10, pady=10)
    
    def setup_export_tab(self) -> None:
        """Настраивает вкладку экспорта"""
        tab = self.tabview.tab(_("settings_dialog.export_tab"))
        
        # Default format
        format_frame = ctk.CTkFrame(tab)
        format_frame.pack(fill="x", padx=10, pady=10)
        
        format_title = ctk.CTkLabel(
            format_frame,
            text=_("settings_dialog.default_export_format_title"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        format_title.pack(pady=(15, 10))
        
        # Выбор формата
        format_options_frame = ctk.CTkFrame(format_frame)
        format_options_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        formats = [
            ("txt", _("settings_dialog.txt_format")),
            ("csv", _("settings_dialog.csv_format")),
            ("json", _("settings_dialog.json_format"))
        ]
        
        for value, text in formats:
            radio = ctk.CTkRadioButton(
                format_options_frame,
                text=text,
                variable=self.export_format_var,
                value=value
            )
            radio.pack(anchor="w", padx=20, pady=5)
        
        # Auto-save settings
        autosave_frame = ctk.CTkFrame(tab)
        autosave_frame.pack(fill="x", padx=10, pady=10)
        
        autosave_title = ctk.CTkLabel(
            autosave_frame,
            text=_("settings_dialog.autosave_settings_title"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        autosave_title.pack(pady=(15, 10))
        
        autosave_check = ctk.CTkCheckBox(
            autosave_frame,
            text=_("settings_dialog.autosave_checkbox"),
            variable=self.auto_save_var
        )
        autosave_check.pack(anchor="w", padx=15, pady=(5, 15))
    
    def update_delay_label(self, value) -> None:
        """Update delay value label"""
        self.delay_value_label.configure(text=f"{float(value):.1f}s")
    
    def update_threads_label(self, value) -> None:
        """Update threads value label"""
        self.threads_value_label.configure(text=str(int(float(value))))
    
    def apply_settings(self) -> None:
        """Apply settings and close dialog"""
        try:
            # Проверяем настройки
            if self.request_delay_var.get() < 0.1:
                messagebox.showwarning(_("settings_dialog.invalid_delay_warning_title"), _("settings_dialog.invalid_delay_warning"))
                return
            
            if self.max_threads_var.get() < 1:
                messagebox.showwarning(_("settings_dialog.invalid_threads_warning_title"), _("settings_dialog.invalid_threads_warning"))
                return
            
            # Update config
            self.config['theme'] = self.theme_var.get()
            self.config['language'] = self.language_var.get()
            self.config['request_delay'] = self.request_delay_var.get()
            self.config['max_threads'] = self.max_threads_var.get()
            self.config['auto_save'] = self.auto_save_var.get()
            self.config['export_format'] = self.export_format_var.get()
            
            # Create new config object
            new_config = AppConfig.from_dict(self.config)
            
            # Call apply callback
            if self.apply_callback:
                self.apply_callback(new_config)
            
            # Save to file
            new_config.save_to_file("config.json")
            
            messagebox.showinfo(_("settings_dialog.settings_applied_success_title"), _("settings_dialog.settings_applied_success"))
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror(_("settings_dialog.settings_apply_error_title"), _("settings_dialog.settings_apply_error", error=str(e)))
    
    def reset_to_defaults(self) -> None:
        """Сброс всех настроек к значениям по умолчанию"""
        if messagebox.askyesno(_("settings_dialog.reset_settings_confirm_title"), _("settings_dialog.reset_settings_confirm")):
            default_config = AppConfig()
            
            self.theme_var.set(default_config.theme)
            self.request_delay_var.set(default_config.request_delay)
            self.max_threads_var.set(default_config.max_threads)
            self.auto_save_var.set(default_config.auto_save)
            self.export_format_var.set(default_config.export_format)
            
            # Обновляем отображение слайдеров
            self.update_delay_label(default_config.request_delay)
            self.update_threads_label(default_config.max_threads)
    
    def set_apply_callback(self, callback: Callable[[AppConfig], None]) -> None:
        """Set callback for when settings are applied"""
        self.apply_callback = callback
    
    def winfo_exists(self) -> bool:
        """Check if dialog window exists"""
        try:
            return self.dialog.winfo_exists()
        except:
            return False