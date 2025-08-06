import customtkinter as ctk
from typing import Optional

from ...utils.localization import _

class ExportFormatDialog:
    """A simple dialog for selecting the export format."""

    def __init__(self, parent):
        self.result = None

        # Создаем диалог
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(_("main_window.export_format_dialog_title"))
        self.dialog.geometry("350x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Центрируем диалог
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 175
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 125
        self.dialog.geometry(f"350x250+{x}+{y}")

        # Создаем содержимое
        label = ctk.CTkLabel(self.dialog, text=_("main_window.export_format_dialog_label"), font=ctk.CTkFont(size=14))
        label.pack(pady=20)

        # Кнопки форматов
        txt_btn = ctk.CTkButton(self.dialog, text=_("main_window.export_format_txt"), command=lambda: self.select_format("txt"))
        txt_btn.pack(pady=5)

        csv_btn = ctk.CTkButton(self.dialog, text=_("main_window.export_format_csv"), command=lambda: self.select_format("csv"))
        csv_btn.pack(pady=5)

        json_btn = ctk.CTkButton(self.dialog, text=_("main_window.export_format_json"), command=lambda: self.select_format("json"))
        json_btn.pack(pady=5)

        cancel_btn = ctk.CTkButton(self.dialog, text=_("main_window.cancel_button"), command=self.dialog.destroy)
        cancel_btn.pack(pady=10)

    def select_format(self, format_type: str) -> None:
        """Selects the export format and closes the dialog."""
        self.result = format_type
        self.dialog.destroy()

    def get_format(self) -> Optional[str]:
        """Returns the selected format."""
        self.dialog.wait_window()
        return self.result
