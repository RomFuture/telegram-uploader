"""Launch interactive Telegram Client API login (terminal)."""

from __future__ import annotations

import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox

LOGIN_COMMAND = "telegram-uploader-login"

PRIVACY_MESSAGE = """Telegram sign-in (one time)

Telegram Uploader uses your Telegram account — not a bot — to upload
backups to your private group.

You will enter your phone number and the code from the Telegram app
(in this computer's terminal). Optional: 2FA password if you use one.

Your credentials stay on this computer:
  • Session file on disk (path in Settings)
  • API id/hash in ~/.config/telegram-uploader/.env
  • Backups go only to the group ID you set in Settings

We do not collect or share your login with third parties.

Next: a terminal opens. Follow the prompts, then return here and
click Test Client API or start a backup."""


def show_login_instructions(parent: tk.Misc) -> None:
    if not messagebox.askokcancel("Sign in to Telegram", PRIVACY_MESSAGE, parent=parent):
        return
    if _launch_login_terminal():
        messagebox.showinfo(
            "Terminal opened",
            "Complete sign-in in the terminal window.\n\n"
            "When finished, click Test Client API or restart backup workers:\n"
            "  docker compose -f /opt/telegram-uploader/docker-compose.yml restart",
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

    if shutil.which("gnome-terminal"):
        subprocess.Popen(["gnome-terminal", "--", LOGIN_COMMAND], start_new_session=True)
        return True
    if shutil.which("konsole"):
        subprocess.Popen(["konsole", "-e", LOGIN_COMMAND], start_new_session=True)
        return True
    if shutil.which("xfce4-terminal"):
        subprocess.Popen(["xfce4-terminal", "-e", LOGIN_COMMAND], start_new_session=True)
        return True
    if shutil.which("x-terminal-emulator"):
        subprocess.Popen(["x-terminal-emulator", "-e", LOGIN_COMMAND], start_new_session=True)
        return True
    if shutil.which("xterm"):
        subprocess.Popen(["xterm", "-e", LOGIN_COMMAND], start_new_session=True)
        return True
    return False
