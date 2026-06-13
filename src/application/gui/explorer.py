"""KeePassXC-style vault: toolbar + folder sidebar + file table."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk
from uuid import UUID

from application.backend_receiver import FolderViewDTO, QueueItemViewDTO, SessionQueueSnapshotDTO
from application.gui.context_menu import prompt_rename, show_file_context_menu
from application.gui.theme import COLORS

ALL_FILES_FOLDER_NAME = "All files"


class ExplorerView(ttk.Frame):
    FAILED_STATUSES = frozenset({"failed", "error"})
    STUCK_STATUSES = frozenset({"processing", "uploading", "archiving", "cleanup"})

    def __init__(
        self,
        parent: tk.Misc,
        folders: tuple[FolderViewDTO, ...],
        database_name: str,
        on_add_file: Callable[[Path, str, UUID | None], None],
        on_create_folder: Callable[[str], None],
        on_start_backup: Callable[[], None],
        on_restore: Callable[[], None],
        on_refresh: Callable[[], None],
        on_lock: Callable[[], None],
        on_settings: Callable[[], None],
        on_folder_selected: Callable[[UUID | None], None],
        on_rename: Callable[[UUID, str], None],
        on_move: Callable[[UUID, UUID], None],
        on_delete: Callable[[UUID], None],
    ) -> None:
        super().__init__(parent)
        self._folders = list(folders)
        self._database_name = database_name
        self._selected_folder_id: UUID | None = folders[0].folder_id if folders else None
        self._on_add_file = on_add_file
        self._on_create_folder = on_create_folder
        self._on_start_backup = on_start_backup
        self._on_restore = on_restore
        self._on_refresh = on_refresh
        self._on_lock = on_lock
        self._on_settings = on_settings
        self._on_folder_selected = on_folder_selected
        self._on_rename = on_rename
        self._on_move = on_move
        self._on_delete = on_delete
        self._queue_snapshot: SessionQueueSnapshotDTO | None = None
        self._items_by_id: dict[str, QueueItemViewDTO] = {}

        toolbar = ttk.Frame(self, padding=(0, 0, 0, 8))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=database_name, style="Title.TLabel").pack(side="left")
        ttk.Label(toolbar, text=" · backup vault", style="Muted.TLabel").pack(
            side="left", padx=(4, 0)
        )

        ttk.Button(toolbar, text="Settings", command=self._on_settings).pack(side="right")
        self._btn_lock = ttk.Button(toolbar, text="Lock", command=self._on_lock)
        self._btn_lock.pack(side="right", padx=(0, 6))
        self._btn_restore = ttk.Button(toolbar, text="Restore", command=self._on_restore)
        self._btn_restore.pack(side="right", padx=(0, 6))
        self._btn_refresh = ttk.Button(toolbar, text="Refresh", command=self._on_refresh)
        self._btn_refresh.pack(side="right", padx=(0, 6))
        self._btn_backup = ttk.Button(toolbar, text="Backup", command=self._on_start_backup)
        self._btn_backup.pack(side="right", padx=(0, 6))
        self._btn_add_file = ttk.Button(toolbar, text="Add file", command=self._handle_add_file)
        self._btn_add_file.pack(side="right", padx=(0, 6))

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        sidebar = ttk.Frame(paned, padding=(0, 0, 8, 0))
        paned.add(sidebar, weight=0)
        ttk.Label(sidebar, text="Folders", style="Muted.TLabel").pack(anchor="w")
        self._folder_list = tk.Listbox(
            sidebar,
            height=18,
            exportselection=False,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            selectbackground=COLORS["selection"],
            selectforeground=COLORS["selection_text"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["border"],
            borderwidth=0,
            activestyle="none",
        )
        self._folder_list.pack(fill="both", expand=True, pady=(6, 0))
        self._folder_list.bind("<<ListboxSelect>>", self._handle_folder_select)
        ttk.Button(sidebar, text="+ New folder", command=self._handle_new_folder).pack(
            fill="x", pady=(8, 0)
        )
        self._render_folder_list()

        main = ttk.Frame(paned, padding=0)
        paned.add(main, weight=1)

        columns = ("display_name", "folder", "size", "modified", "status")
        self._tree = ttk.Treeview(main, columns=columns, show="headings", height=18)
        self._tree.heading("display_name", text="Name")
        self._tree.heading("folder", text="Folder")
        self._tree.heading("size", text="Size")
        self._tree.heading("modified", text="Modified")
        self._tree.heading("status", text="Status")
        self._tree.column("display_name", width=220, stretch=True)
        self._tree.column("folder", width=90, stretch=False)
        self._tree.column("size", width=80, stretch=False)
        self._tree.column("modified", width=130, stretch=False)
        self._tree.column("status", width=120, stretch=False)
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<Double-1>", self._handle_double_click)
        self._tree.bind("<Button-3>", self._handle_context_menu)

        self._tree.tag_configure("failed", foreground="#e57373")
        self._tree.tag_configure("stuck", foreground="#ffb74d")
        self._tree.tag_configure("external", foreground="#ffd54f")

        self._status_var = tk.StringVar(value="No files yet")
        ttk.Label(main, textvariable=self._status_var, style="Muted.TLabel").pack(
            anchor="w", pady=(6, 0)
        )

    def selected_folder_id(self) -> UUID | None:
        return self._selected_folder_id

    def selected_folder_name(self) -> str | None:
        for folder in self._folders:
            if folder.folder_id == self._selected_folder_id:
                return folder.name
        return None

    def is_all_files_selected(self) -> bool:
        return self.selected_folder_name() == ALL_FILES_FOLDER_NAME

    def set_folders(self, folders: tuple[FolderViewDTO, ...]) -> None:
        self._folders = list(folders)
        if self._selected_folder_id is None and folders:
            self._selected_folder_id = folders[0].folder_id
        self._render_folder_list()

    def select_folder(self, folder_id: UUID) -> None:
        self._selected_folder_id = folder_id
        self._render_folder_list()
        if self._queue_snapshot is not None:
            self.render_queue_snapshot(self._queue_snapshot)

    def _render_folder_list(self) -> None:
        self._folder_list.delete(0, "end")
        selected_index = 0
        for index, folder in enumerate(self._folders):
            self._folder_list.insert("end", folder.name)
            if folder.folder_id == self._selected_folder_id:
                selected_index = index
        if self._folders:
            self._folder_list.selection_set(selected_index)

    def _handle_folder_select(self, _event: object) -> None:
        selection: tuple[int, ...] = self._folder_list.curselection()  # type: ignore[no-untyped-call]
        if not selection:
            return
        folder = self._folders[selection[0]]
        self._selected_folder_id = folder.folder_id
        self._on_folder_selected(folder.folder_id)
        if self._queue_snapshot is not None:
            self.render_queue_snapshot(self._queue_snapshot)

    def _handle_new_folder(self) -> None:
        name = simpledialog.askstring(
            "New folder",
            "Folder name:",
            parent=self.winfo_toplevel(),
        )
        if name and name.strip():
            self._on_create_folder(name.strip())

    def _handle_add_file(self) -> None:
        source_path = filedialog.askopenfilename(title="Select file to back up")
        if not source_path:
            return
        path = Path(source_path)
        display_name = simpledialog.askstring(
            "Display name",
            "Enter the name shown in the queue:",
            initialvalue=path.name,
            parent=self.winfo_toplevel(),
        )
        if not display_name or not display_name.strip():
            return
        self._on_add_file(path, display_name.strip(), self._selected_folder_id)

    def _selected_item(self) -> QueueItemViewDTO | None:
        selected = self._tree.selection()
        if not selected:
            return None
        return self._items_by_id.get(selected[0])

    def _handle_double_click(self, _event: object) -> None:
        item = self._selected_item()
        if item is not None:
            prompt_rename(self, item, self._on_rename)

    def _handle_context_menu(self, event: tk.Event[tk.Misc]) -> None:
        row_id = self._tree.identify_row(event.y)
        if not row_id:
            return
        self._tree.selection_set(row_id)
        item = self._items_by_id.get(row_id)
        if item is None:
            return
        show_file_context_menu(
            self.winfo_toplevel(),
            item,
            tuple(self._folders),
            x_root=event.x_root,
            y_root=event.y_root,
            on_rename=self._on_rename,
            on_move=self._on_move,
            on_delete=self._on_delete,
        )

    def render_queue_snapshot(self, snapshot: SessionQueueSnapshotDTO) -> None:
        self._queue_snapshot = snapshot
        self._items_by_id.clear()
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        visible_items = snapshot.items
        folder_name = self.selected_folder_name()
        if self._selected_folder_id is not None and folder_name != ALL_FILES_FOLDER_NAME:
            visible_items = tuple(
                item for item in snapshot.items if item.folder_id == self._selected_folder_id
            )
            hidden_count = len(snapshot.items) - len(visible_items)
        else:
            hidden_count = 0

        for item in visible_items:
            status = item.status.lower()
            tags: tuple[str, ...] = ()
            display_status = item.status
            if status in self.FAILED_STATUSES:
                tags = ("failed",)
                display_status = f"failed · {item.status}"
            elif status in self.STUCK_STATUSES:
                tags = ("stuck",)
                display_status = f"in progress · {item.status}"
            elif status == "completed":
                display_status = "backed up"

            folder_label = item.folder_name or ("Unassigned" if item.folder_id is None else "—")
            row_id = str(item.source_item_id)
            self._items_by_id[row_id] = item
            self._tree.insert(
                "",
                "end",
                iid=row_id,
                values=(
                    item.display_name,
                    folder_label,
                    item.size_label,
                    item.modified_label,
                    display_status,
                ),
                tags=tags,
            )

        if visible_items:
            self._status_var.set(f"{len(visible_items)} file(s) — right-click for actions")
        elif hidden_count > 0:
            self._status_var.set(f"Folder is empty — {hidden_count} file(s) in other folders")
        else:
            self._status_var.set("No files in this folder")

    def set_toolbar_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in (
            self._btn_add_file,
            self._btn_backup,
            self._btn_refresh,
            self._btn_restore,
            self._btn_lock,
        ):
            button.configure(state=state)
