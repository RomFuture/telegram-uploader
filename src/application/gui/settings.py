"""Settings dialog with General / Client API / Bot API tabs."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import cast

from application.gui.telegram_login import show_login_instructions
from application.gui.theme import style_toplevel
from application.settings_values import SettingsValues


@dataclass(frozen=True, slots=True)
class TestClientApiDialogResult:
    ok: bool
    stage: str
    message: str


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        initial: SettingsValues,
        on_test_client_api: Callable[[SettingsValues], TestClientApiDialogResult] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.resizable(False, False)
        style_toplevel(self)
        self.transient(cast(tk.Wm, parent))
        self.grab_set()

        self._result: SettingsValues | None = None
        self._on_test_client_api = on_test_client_api
        self._test_running = False

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        self._key_var = tk.StringVar(value=initial.encryption_key or "")
        self._chat_var = tk.StringVar(value=initial.target_chat_id)
        self._provider_var = tk.StringVar(value=initial.telegram_provider)
        self._api_id_var = tk.StringVar(value=initial.telegram_api_id)
        self._api_hash_var = tk.StringVar(value=initial.telegram_api_hash)
        self._session_var = tk.StringVar(value=initial.telegram_session_path)
        self._bot_token_var = tk.StringVar(value=initial.telegram_bot_token)
        self._bot_api_url_var = tk.StringVar(value=initial.telegram_bot_api_url)
        self._ram_var = tk.IntVar(value=initial.archive_ram_limit_mb)

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)

        general = ttk.Frame(notebook, padding=8)
        client = ttk.Frame(notebook, padding=8)
        bot = ttk.Frame(notebook, padding=8)
        notebook.add(general, text="General")
        notebook.add(client, text="Client API")
        notebook.add(bot, text="Bot API")

        self._build_general_tab(general)
        self._build_client_tab(client)
        self._build_bot_tab(bot)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._on_cancel).pack(side="right")
        ttk.Button(buttons, text="Save", command=self._on_save).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _event: self._on_cancel())
        self.wait_window()

    def _build_general_tab(self, frame: ttk.Frame) -> None:
        row = 0
        row = self._add_entry(
            frame, row, "Default encryption key (optional)", self._key_var, show="*"
        )
        row = self._add_entry(frame, row, "Target chat ID", self._chat_var)
        row = self._add_combo(
            frame, row, "Active provider", self._provider_var, ("client", "bot")
        )

        ram_frame = ttk.Frame(frame)
        ram_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(ram_frame, text="Archive RAM limit (not applied yet)").pack(anchor="w")
        ram_controls = ttk.Frame(ram_frame)
        ram_controls.pack(fill="x", pady=(4, 0))
        self._ram_label = ttk.Label(ram_controls, text=f"{self._ram_var.get()} MB")
        self._ram_label.pack(side="right")
        ttk.Scale(
            ram_controls,
            from_=512,
            to=4096,
            orient="horizontal",
            variable=self._ram_var,
            command=self._on_ram_changed,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        row += 1

        ttk.Label(
            frame,
            text="Client API is required for Restore. Configure credentials on the Client API tab.",
            wraplength=420,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8,  0))
        frame.columnconfigure(1, weight=1)

    def _build_client_tab(self, frame: ttk.Frame) -> None:
        row = 0
        row = self._add_entry(frame, row, "API ID", self._api_id_var)
        row = self._add_entry(frame, row, "API hash", self._api_hash_var, show="*")
        row = self._add_entry(frame, row, "Session file path", self._session_var)

        test_row = ttk.Frame(frame)
        test_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._test_button = ttk.Button(
            test_row,
            text="Test Client API",
            command=self._handle_test_client_api,
        )
        self._test_button.pack(side="left", padx=(0, 8))
        ttk.Button(
            test_row,
            text="Sign in to Telegram…",
            command=lambda: show_login_instructions(self),
        ).pack(side="left")
        row += 1

        ttk.Label(
            frame,
            text=(
                "1. Fill API ID and hash from https://my.telegram.org\n"
                "2. Set backup group ID on the General tab\n"
                "3. Click Save (writes ~/.config/telegram-uploader/.env)\n"
                "4. Sign in to Telegram… (one time — phone + code in terminal)\n"
                "5. Test Client API — uploads a small test file to your group"
            ),
            wraplength=420,
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        frame.columnconfigure(1, weight=1)

    def _build_bot_tab(self, frame: ttk.Frame) -> None:
        row = 0
        row = self._add_entry(frame, row, "Bot token", self._bot_token_var, show="*")
        row = self._add_entry(frame, row, "Bot API URL", self._bot_api_url_var)
        ttk.Label(
            frame,
            text=(
                "Used only when Active provider = bot.\n"
                "Start local Bot API: docker compose --profile bot up -d\n"
                "Bot API backups cannot be restored via the app — use Client API for restore."
            ),
            wraplength=420,
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        frame.columnconfigure(1, weight=1)

    def _current_values(self) -> SettingsValues:
        return SettingsValues(
            encryption_key=self._key_var.get().strip() or None,
            target_chat_id=self._chat_var.get().strip(),
            telegram_provider=self._provider_var.get().strip() or "client",
            telegram_api_id=self._api_id_var.get().strip(),
            telegram_api_hash=self._api_hash_var.get().strip(),
            telegram_session_path=self._session_var.get().strip(),
            telegram_bot_token=self._bot_token_var.get().strip(),
            telegram_bot_api_url=self._bot_api_url_var.get().strip(),
            archive_ram_limit_mb=int(self._ram_var.get()),
        )

    def _handle_test_client_api(self) -> None:
        callback = self._on_test_client_api
        if callback is None or self._test_running:
            return
        settings = self._current_values()
        self._test_running = True
        self._test_button.configure(state="disabled")

        def worker() -> None:
            try:
                result = callback(settings)
            except Exception as error:
                result = TestClientApiDialogResult(
                    ok=False,
                    stage="error",
                    message=str(error),
                )
            self.after(0, lambda: self._show_test_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _show_test_result(self, result: TestClientApiDialogResult) -> None:
        self._test_running = False
        self._test_button.configure(state="normal")
        title = "Client API OK" if result.ok else f"Client API failed ({result.stage})"
        if result.ok:
            messagebox.showinfo(title, result.message, parent=self)
        else:
            messagebox.showerror(title, result.message, parent=self)

    def _add_entry(
        self,
        frame: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        show: str | None = None,
    ) -> int:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=(8, 0))
        if show is None:
            entry = ttk.Entry(frame, textvariable=variable, width=42)
        else:
            entry = ttk.Entry(frame, textvariable=variable, width=42, show=show)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        return row + 1

    def _add_combo(
        self,
        frame: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
    ) -> int:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            frame,
            textvariable=variable,
            values=values,
            state="readonly",
            width=39,
        ).grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        return row + 1

    def _on_ram_changed(self, value: str) -> None:
        mb = int(float(value))
        self._ram_var.set(mb)
        self._ram_label.configure(text=f"{mb} MB")

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()

    def _on_save(self) -> None:
        self._result = self._current_values()
        self.destroy()

    @property
    def values(self) -> SettingsValues | None:
        return self._result
