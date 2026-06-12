"""Unlock screen — minimalist dark login card."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, simpledialog, ttk

from application.gui.theme import COLORS


class UnlockScreen(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        profile_names: tuple[str, ...],
        on_unlock: Callable[[str, str], None],
        on_create_database: Callable[[str, str], None],
        on_open_settings: Callable[[], None],
        on_refresh_profiles: Callable[[], tuple[str, ...]],
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self._on_unlock = on_unlock
        self._on_create_database = on_create_database
        self._on_open_settings = on_open_settings
        self._on_refresh_profiles = on_refresh_profiles

        outer = tk.Frame(self, bg=COLORS["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(
            outer,
            bg=COLORS["surface"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=28,
            pady=28,
        )
        card.pack()

        tk.Label(
            card,
            text="🛡",
            bg=COLORS["surface"],
            fg=COLORS["accent"],
            font=("Segoe UI", 28),
        ).pack()
        tk.Label(
            card,
            text="Telegram Uploader",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(8, 4))
        tk.Label(
            card,
            text="Encrypted backup vault — unlock with your database key",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=320,
            justify="center",
        ).pack(pady=(0, 20))

        self._profile_var = tk.StringVar(value=profile_names[0] if profile_names else "")
        self._key_var = tk.StringVar(value="")
        self._show_key = tk.BooleanVar(value=False)

        tk.Label(card, text="Database", bg=COLORS["surface"], fg=COLORS["muted"], anchor="w").pack(
            fill="x"
        )
        profile_row = tk.Frame(card, bg=COLORS["surface"])
        profile_row.pack(fill="x", pady=(4, 12))
        self._profile_combo = ttk.Combobox(
            profile_row,
            textvariable=self._profile_var,
            values=profile_names,
            width=28,
        )
        self._profile_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(profile_row, text="↻", width=3, command=self._refresh_profiles_ui).pack(
            side="left", padx=(8, 0)
        )

        tk.Label(
            card,
            text="Encryption key",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            anchor="w",
        ).pack(fill="x")
        key_row = tk.Frame(card, bg=COLORS["surface"])
        key_row.pack(fill="x", pady=(4, 16))
        self._key_entry = ttk.Entry(key_row, textvariable=self._key_var, show="*", width=30)
        self._key_entry.pack(side="left", fill="x", expand=True)
        ttk.Checkbutton(
            key_row,
            text="Show",
            variable=self._show_key,
            command=self._toggle_key_visibility,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            card,
            text="Unlock",
            style="Accent.TButton",
            command=self._handle_unlock,
        ).pack(fill="x")

        footer = tk.Frame(card, bg=COLORS["surface"])
        footer.pack(fill="x", pady=(16, 0))
        tk.Label(
            footer,
            text="No database yet?",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack()
        links = tk.Frame(footer, bg=COLORS["surface"])
        links.pack(pady=(4, 0))
        tk.Button(
            links,
            text="Create database",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface_alt"],
            activeforeground=COLORS["text"],
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            command=self._handle_create_db,
        ).pack(side="left")
        tk.Label(links, text=" · ", bg=COLORS["surface"], fg=COLORS["muted"]).pack(side="left")
        tk.Button(
            links,
            text="Settings",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface_alt"],
            activeforeground=COLORS["text"],
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            command=self._on_open_settings,
        ).pack(side="left")

        self._key_entry.bind("<Return>", lambda _event: self._handle_unlock())

    def _toggle_key_visibility(self) -> None:
        self._key_entry.configure(show="" if self._show_key.get() else "*")

    def _refresh_profiles_ui(self) -> None:
        names = self._on_refresh_profiles()
        self._profile_combo.configure(values=names)
        if names and not self._profile_var.get().strip():
            self._profile_var.set(names[0])

    def _handle_unlock(self) -> None:
        profile = self._profile_var.get().strip()
        key = self._key_var.get()
        if not profile:
            messagebox.showerror("Invalid input", "Database name is required.", parent=self)
            return
        if not key.strip():
            messagebox.showerror("Invalid input", "Encryption key is required.", parent=self)
            return
        self._on_unlock(profile, key)

    def _handle_create_db(self) -> None:
        profile = simpledialog.askstring(
            "Create database",
            "Enter a name for the new database:",
            parent=self.winfo_toplevel(),
        )
        if not profile or not profile.strip():
            return
        key = simpledialog.askstring(
            "Encryption key",
            "Choose an encryption key for archives in this database.\n"
            "Store it safely — you need it to unlock later.",
            show="*",
            parent=self.winfo_toplevel(),
        )
        if not key or not key.strip():
            messagebox.showerror(
                "Invalid input",
                "Encryption key is required.",
                parent=self.winfo_toplevel(),
            )
            return
        self._on_create_database(profile.strip(), key.strip())
