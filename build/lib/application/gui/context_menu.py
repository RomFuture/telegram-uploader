"""Context menu for file row actions (KeePassXC-style)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, simpledialog
from uuid import UUID

from application.backend_receiver import FolderViewDTO, QueueItemViewDTO
from application.gui.theme import menu_colors


def show_file_context_menu(
    parent: tk.Misc,
    item: QueueItemViewDTO,
    folders: tuple[FolderViewDTO, ...],
    *,
    x_root: int,
    y_root: int,
    on_rename: Callable[[UUID, str], None],
    on_move: Callable[[UUID, UUID], None],
    on_delete: Callable[[UUID], None],
) -> None:
    colors = menu_colors()
    menu = tk.Menu(
        parent,
        tearoff=0,
        bg=colors["bg"],
        fg=colors["fg"],
        activebackground=colors["activebackground"],
        activeforeground=colors["activeforeground"],
        disabledforeground=colors["disabledforeground"],
    )

    menu.add_command(
        label="Rename",
        command=lambda: _rename(parent, item, on_rename),
    )

    move_menu = tk.Menu(
        menu,
        tearoff=0,
        bg=colors["bg"],
        fg=colors["fg"],
        activebackground=colors["activebackground"],
        activeforeground=colors["activeforeground"],
        disabledforeground=colors["disabledforeground"],
    )
    if folders:
        for folder in folders:
            folder_id = folder.folder_id

            def move_to(folder_id: UUID = folder_id) -> None:
                _move(parent, item, folder_id, on_move)

            move_menu.add_command(label=folder.name, command=move_to)
    else:
        move_menu.add_command(label="(no folders)", state="disabled")
    menu.add_cascade(label="Move to folder", menu=move_menu)

    menu.add_separator()
    menu.add_command(
        label="Delete",
        command=lambda: _delete(parent, item, on_delete),
    )

    try:
        menu.tk_popup(x_root, y_root)
    finally:
        menu.grab_release()


def prompt_rename(
    parent: tk.Misc,
    item: QueueItemViewDTO,
    on_rename: Callable[[UUID, str], None],
) -> None:
    _rename(parent, item, on_rename)


def _rename(
    parent: tk.Misc,
    item: QueueItemViewDTO,
    on_rename: Callable[[UUID, str], None],
) -> None:
    new_name = simpledialog.askstring(
        "Rename",
        "New display name:",
        initialvalue=item.display_name,
        parent=parent.winfo_toplevel(),
    )
    if not new_name or not new_name.strip():
        return
    try:
        on_rename(item.source_item_id, new_name.strip())
    except Exception as error:
        messagebox.showerror("Rename failed", str(error), parent=parent.winfo_toplevel())


def _move(
    parent: tk.Misc,
    item: QueueItemViewDTO,
    folder_id: UUID,
    on_move: Callable[[UUID, UUID], None],
) -> None:
    try:
        on_move(item.source_item_id, folder_id)
    except Exception as error:
        messagebox.showerror("Move failed", str(error), parent=parent.winfo_toplevel())


def _delete(
    parent: tk.Misc,
    item: QueueItemViewDTO,
    on_delete: Callable[[UUID], None],
) -> None:
    if not messagebox.askyesno(
        "Delete file",
        f"Remove '{item.display_name}' from this database?\n"
        "This does not delete files in Telegram.",
        parent=parent.winfo_toplevel(),
    ):
        return
    try:
        on_delete(item.source_item_id)
    except Exception as error:
        messagebox.showerror("Delete failed", str(error), parent=parent.winfo_toplevel())
