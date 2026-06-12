"""In-app Telegram Client API sign-in (Settings → Sign in to Telegram…)."""

from __future__ import annotations

import shutil
import subprocess
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk
from typing import cast

from application.env_store import save_settings_env
from application.gui.theme import style_toplevel
from application.settings_values import SettingsValues
from application.telegram_sign_in import (
    TelegramPasswordRequired,
    TelegramSignInConfig,
    TelegramSignInError,
    run_complete_login,
    run_send_login_code,
)
from infrastructure.paths import default_session_path

PRIVACY_MESSAGE = """Telegram sign-in (one time)

Telegram Uploader uses your Telegram account — not a bot — to upload
backups to your private group.

You will enter your phone number and the code from the Telegram app.
Optional: 2FA password if you use one.

Your credentials stay on this computer:
  • Session file on disk (path in Settings)
  • API id/hash in ~/.config/telegram-uploader/.env
  • Backups go only to the group ID you set in Settings

We do not collect or share your login with third parties.

Click OK to continue sign-in in this window."""

LOGIN_COMMAND = "telegram-uploader-login"


def show_login_instructions(parent: tk.Misc, settings: SettingsValues) -> None:
    missing = _missing_fields(settings)
    if missing:
        messagebox.showerror(
            "Cannot sign in yet",
            "Fill in and Save first:\n\n" + "\n".join(f"• {line}" for line in missing),
            parent=parent,
        )
        return
    if not messagebox.askokcancel("Sign in to Telegram", PRIVACY_MESSAGE, parent=parent):
        return
    try:
        env_path = save_settings_env(settings)
    except OSError as error:
        messagebox.showerror(
            "Settings not saved",
            f"Could not write config before sign-in:\n{error}",
            parent=parent,
        )
        return
    dialog = TelegramSignInDialog(parent, settings, env_path=env_path)
    parent.wait_window(dialog)


def _missing_fields(settings: SettingsValues) -> list[str]:
    missing: list[str] = []
    if not settings.telegram_api_id.strip().isdigit():
        missing.append("API ID (Client API tab)")
    if not settings.telegram_api_hash.strip():
        missing.append("API hash (Client API tab)")
    if not settings.target_chat_id.strip():
        missing.append("Target chat ID (General tab)")
    return missing


def _sign_in_config(settings: SettingsValues) -> TelegramSignInConfig:
    session_raw = settings.telegram_session_path.strip()
    session_path = Path(session_raw) if session_raw else default_session_path()
    return TelegramSignInConfig(
        api_id=int(settings.telegram_api_id.strip()),
        api_hash=settings.telegram_api_hash.strip(),
        session_path=session_path,
        target_chat_id=settings.target_chat_id.strip(),
    )


class TelegramSignInDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        settings: SettingsValues,
        *,
        env_path: Path,
    ) -> None:
        super().__init__(parent)
        self.title("Sign in to Telegram")
        self.resizable(False, False)
        style_toplevel(self)
        self.transient(cast(tk.Wm, parent))
        self.grab_set()

        self._settings = settings
        self._config = _sign_in_config(settings)
        self._env_path = env_path
        self._busy = False
        self._needs_password = False

        self._phone_var = tk.StringVar()
        self._code_var = tk.StringVar()
        self._password_var = tk.StringVar()
        self._status_var = tk.StringVar(value="Enter your phone number (international format).")

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, textvariable=self._status_var, wraplength=360).pack(anchor="w")

        self._phone_frame = ttk.Frame(outer)
        self._phone_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(self._phone_frame, text="Phone").pack(anchor="w")
        self._phone_entry = ttk.Entry(self._phone_frame, textvariable=self._phone_var, width=42)
        self._phone_entry.pack(fill="x", pady=(4, 0))

        self._code_frame = ttk.Frame(outer)
        ttk.Label(self._code_frame, text="Code from Telegram").pack(anchor="w")
        self._code_entry = ttk.Entry(self._code_frame, textvariable=self._code_var, width=42)
        self._code_entry.pack(fill="x", pady=(4, 0))

        self._password_frame = ttk.Frame(outer)
        ttk.Label(self._password_frame, text="Two-step verification password").pack(anchor="w")
        self._password_entry = ttk.Entry(
            self._password_frame,
            textvariable=self._password_var,
            width=42,
            show="*",
        )
        self._password_entry.pack(fill="x", pady=(4, 0))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(16, 0))
        ttk.Button(buttons, text="Cancel", command=self._on_cancel).pack(side="right")
        self._action_button = ttk.Button(buttons, text="Send code", command=self._on_action)
        self._action_button.pack(side="right", padx=(0, 8))

        self._phone_frame.pack(fill="x", pady=(12, 0))
        self._phone_entry.focus_set()
        self.bind("<Return>", lambda _event: self._on_action())
        self.bind("<Escape>", lambda _event: self._on_cancel())

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._action_button.configure(state=state)

    def _on_cancel(self) -> None:
        if self._busy:
            return
        self.destroy()

    def _on_action(self) -> None:
        if self._busy:
            return
        if self._needs_password:
            self._submit_password()
        elif self._code_frame.winfo_ismapped():
            self._submit_code()
        else:
            self._send_code()

    def _send_code(self) -> None:
        phone = self._phone_var.get().strip()
        if not phone.startswith("+") or len(phone) < 8:
            messagebox.showerror(
                "Invalid phone",
                "Use international format, e.g. +79001234567",
                parent=self,
            )
            return
        self._set_busy(True)
        self._status_var.set("Sending code to Telegram…")

        def worker() -> None:
            try:
                run_send_login_code(self._config, phone)
            except Exception as exc:
                self.after(0, self._make_send_code_failed_callback(exc))
                return
            self.after(0, self._on_send_code_ok)

        threading.Thread(target=worker, daemon=True).start()

    def _make_send_code_failed_callback(self, error: Exception) -> Callable[[], None]:
        return lambda: self._on_send_code_failed(error)

    def _make_sign_in_failed_callback(self, error: Exception) -> Callable[[], None]:
        return lambda: self._on_sign_in_failed(error)

    def _on_send_code_ok(self) -> None:
        self._set_busy(False)
        self._phone_frame.pack_forget()
        self._code_frame.pack(fill="x", pady=(12, 0))
        self._action_button.configure(text="Sign in")
        self._status_var.set("Enter the code from the Telegram app.")
        self._code_entry.focus_set()

    def _on_send_code_failed(self, error: Exception) -> None:
        self._set_busy(False)
        messagebox.showerror("Sign-in failed", str(error), parent=self)

    def _submit_code(self) -> None:
        code = self._code_var.get().strip()
        if not code:
            messagebox.showerror("Code required", "Enter the code from Telegram.", parent=self)
            return
        phone = self._phone_var.get().strip()
        self._set_busy(True)
        self._status_var.set("Signing in…")

        def worker() -> None:
            try:
                run_complete_login(self._config, phone, code)
            except TelegramPasswordRequired:
                self.after(0, self._on_password_required)
                return
            except Exception as exc:
                self.after(0, self._make_sign_in_failed_callback(exc))
                return
            self.after(0, self._on_sign_in_ok)

        threading.Thread(target=worker, daemon=True).start()

    def _on_password_required(self) -> None:
        self._set_busy(False)
        self._needs_password = True
        self._code_frame.pack_forget()
        self._password_frame.pack(fill="x", pady=(12, 0))
        self._action_button.configure(text="Sign in")
        self._status_var.set("Two-step verification is enabled — enter your Telegram password.")
        self._password_entry.focus_set()

    def _submit_password(self) -> None:
        password = self._password_var.get()
        if not password:
            messagebox.showerror("Password required", "Enter your 2FA password.", parent=self)
            return
        phone = self._phone_var.get().strip()
        code = self._code_var.get().strip()
        self._set_busy(True)
        self._status_var.set("Signing in…")

        def worker() -> None:
            try:
                run_complete_login(self._config, phone, code, password)
            except Exception as exc:
                self.after(0, self._make_sign_in_failed_callback(exc))
                return
            self.after(0, self._on_sign_in_ok)

        threading.Thread(target=worker, daemon=True).start()

    def _on_sign_in_failed(self, error: Exception) -> None:
        self._set_busy(False)
        if isinstance(error, TelegramSignInError):
            message = str(error)
        else:
            message = str(error) or error.__class__.__name__
        messagebox.showerror("Sign-in failed", message, parent=self)

    def _on_sign_in_ok(self) -> None:
        self._set_busy(False)
        messagebox.showinfo(
            "Signed in",
            f"Session saved to:\n{self._config.session_path}\n\n"
            f"Config: {self._env_path}\n\n"
            "Click Test Client API to verify upload to your group.",
            parent=self,
        )
        self.destroy()


def launch_login_terminal_fallback(parent: tk.Misc) -> None:
    """Fallback when GUI sign-in is unavailable (headless / tests)."""
    if _launch_login_terminal():
        messagebox.showinfo(
            "Terminal opened",
            f"Complete sign-in in the terminal window, then Test Client API.\n\n"
            f"Or run: {LOGIN_COMMAND}",
            parent=parent,
        )
    else:
        messagebox.showinfo(
            "Sign in manually",
            f"Open a terminal and run:\n\n  {LOGIN_COMMAND}\n",
            parent=parent,
        )


def _launch_login_terminal() -> bool:
    login = shutil.which(LOGIN_COMMAND)
    if login is None:
        return False
    for terminal, args in (
        ("gnome-terminal", ["gnome-terminal", "--", LOGIN_COMMAND, "--no-intro"]),
        ("konsole", ["konsole", "-e", LOGIN_COMMAND, "--no-intro"]),
        ("xfce4-terminal", ["xfce4-terminal", "-e", f"{LOGIN_COMMAND} --no-intro"]),
        ("x-terminal-emulator", ["x-terminal-emulator", "-e", LOGIN_COMMAND, "--no-intro"]),
        ("xterm", ["xterm", "-e", LOGIN_COMMAND, "--no-intro"]),
    ):
        if shutil.which(terminal):
            subprocess.Popen(args, start_new_session=True)
            return True
    return False
