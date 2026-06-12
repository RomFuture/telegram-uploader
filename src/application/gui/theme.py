"""KeePassXC-inspired dark theme for Tkinter GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

COLORS = {
    "bg": "#2b2b2b",
    "surface": "#363636",
    "surface_alt": "#404040",
    "border": "#4a4a4a",
    "text": "#e0e0e0",
    "muted": "#9aa3b2",
    "selection": "#4a7c59",
    "selection_text": "#ffffff",
    "accent": "#4a7c59",
    "accent_hover": "#5a9468",
    "danger": "#c45c5c",
    "warning": "#c9a227",
}


def style_toplevel(window: tk.Tk | tk.Toplevel) -> None:
    """Apply background to dialogs and popups."""
    window.configure(bg=COLORS["bg"])


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=COLORS["bg"])

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure(
        "Title.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=("Segoe UI", 12, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        font=("Segoe UI", 10),
    )

    style.configure(
        "TButton",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=(10, 6),
    )
    style.map(
        "TButton",
        background=[("active", COLORS["surface"]), ("pressed", COLORS["bg"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["selection_text"],
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface_alt"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface_alt"],
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["text"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["surface_alt"])],
        foreground=[("readonly", COLORS["text"])],
    )

    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        rowheight=26,
        bordercolor=COLORS["border"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["selection"])],
        foreground=[("selected", COLORS["selection_text"])],
    )

    style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("TPanedwindow", background=COLORS["bg"])
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        padding=(12, 6),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["surface_alt"])],
        foreground=[("selected", COLORS["text"])],
    )

    style.configure(
        "Horizontal.TScale",
        background=COLORS["bg"],
        troughcolor=COLORS["surface_alt"],
    )
    style.configure(
        "Horizontal.TProgressbar",
        background=COLORS["accent"],
        troughcolor=COLORS["surface_alt"],
    )

    _configure_combobox_popup(root)
    return style


def _configure_combobox_popup(root: tk.Misc) -> None:
    root.option_add("*TCombobox*Listbox.background", COLORS["surface_alt"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
    root.option_add("*TCombobox*Listbox.selectForeground", COLORS["selection_text"])


def menu_colors() -> dict[str, str]:
    return {
        "bg": COLORS["surface_alt"],
        "fg": COLORS["text"],
        "activebackground": COLORS["selection"],
        "activeforeground": COLORS["selection_text"],
        "disabledforeground": COLORS["muted"],
    }
