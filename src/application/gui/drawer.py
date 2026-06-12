"""Bottom progress strip for backup pipeline activity."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from application.gui.theme import COLORS


class ProgressDrawer(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=(0, 8, 0, 0))
        self._message_var = tk.StringVar(value="Idle")
        self._detail_var = tk.StringVar(value="")

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="Progress", style="Muted.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self._message_var, style="Muted.TLabel").pack(
            side="right"
        )

        self._detail = ttk.Label(
            self,
            textvariable=self._detail_var,
            style="Muted.TLabel",
            wraplength=720,
        )
        self._detail.pack(anchor="w", pady=(2, 0))

        separator = tk.Frame(self, height=1, bg=COLORS["border"])
        separator.pack(fill="x", pady=(8, 0))

        self._bar = ttk.Progressbar(self, mode="indeterminate", length=400)

    def show_idle(self) -> None:
        self._message_var.set("Idle")
        self._detail_var.set("")
        self._bar.stop()
        if self._bar.winfo_ismapped():
            self._bar.pack_forget()

    def show_working(self, message: str, detail: str = "") -> None:
        self._message_var.set(message)
        self._detail_var.set(detail)
        if not self._bar.winfo_ismapped():
            self._bar.pack(anchor="w", pady=(6, 0))
        self._bar.start(12)

    def show_result(self, message: str, detail: str = "") -> None:
        self._message_var.set(message)
        self._detail_var.set(detail)
        self._bar.stop()
        if self._bar.winfo_ismapped():
            self._bar.pack_forget()
