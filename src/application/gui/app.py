"""Tkinter GUI: Unlock → explorer → progress drawer (PROJECT §12)."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from uuid import UUID

from application.backend_receiver import (
    BackendReceiver,
    FolderViewDTO,
    RestoreResultDTO,
    SessionQueueSnapshotDTO,
    SessionViewDTO,
)
from application.env_store import save_settings_env
from application.gui.drawer import ProgressDrawer
from application.gui.errors import format_user_error
from application.gui.explorer import ExplorerView
from application.gui.restore_dest import (
    default_restore_dir,
    is_under_install_root,
    readonly_existing_files,
)
from application.gui.settings import SettingsDialog, TestClientApiDialogResult
from application.gui.theme import apply_theme
from application.gui.unlock import UnlockScreen
from application.settings_values import SettingsValues


class BackupApp:
    def __init__(self, receiver: BackendReceiver, initial_settings: SettingsValues) -> None:
        self._receiver = receiver
        self._settings = initial_settings
        self._session: SessionViewDTO | None = None

        self._root = tk.Tk()
        self._root.title("Telegram Uploader")
        self._root.minsize(900, 620)
        apply_theme(self._root)

        self._container = ttk.Frame(self._root)
        self._container.pack(fill="both", expand=True)

        self._unlock: UnlockScreen | None = None
        self._main_frame: ttk.Frame | None = None
        self._explorer: ExplorerView | None = None
        self._drawer: ProgressDrawer | None = None
        self._session_label: ttk.Label | None = None
        self._restore_running = False
        self._restore_tick_job: str | None = None
        self._restore_tick_start: float | None = None
        self._restore_dest: Path | None = None

        self._show_unlock()

    def run(self) -> None:
        self._root.mainloop()

    def _clear_container(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()
        self._unlock = None
        self._main_frame = None
        self._explorer = None
        self._drawer = None
        self._session_label = None

    def _show_unlock(self) -> None:
        self._clear_container()
        profiles = self._receiver.list_profiles()
        self._unlock = UnlockScreen(
            self._container,
            profile_names=profiles,
            on_unlock=self._on_unlock,
            on_create_database=self._on_create_database,
            on_open_settings=self._open_settings,
            on_refresh_profiles=self._receiver.list_profiles,
        )
        self._unlock.pack(fill="both", expand=True)

    def _show_main(self) -> None:
        self._clear_container()
        self._main_frame = ttk.Frame(self._container, padding=8)
        self._main_frame.pack(fill="both", expand=True)

        database_name = self._session.profile_name if self._session is not None else "vault"

        def rename(source_item_id: UUID, display_name: str) -> None:
            self._receiver.rename_source_item(source_item_id, display_name)
            self._refresh_queue()

        def move(source_item_id: UUID, folder_id: UUID) -> None:
            self._receiver.move_source_item(source_item_id, folder_id)
            self._refresh_queue()

        def delete(source_item_id: UUID) -> None:
            self._receiver.delete_source_item(source_item_id)
            self._refresh_queue()

        self._explorer = ExplorerView(
            self._main_frame,
            folders=self._load_folders(),
            database_name=database_name,
            on_add_file=self._on_add_file,
            on_create_folder=self._on_create_folder,
            on_start_backup=self._on_start_backup,
            on_restore=self._on_restore,
            on_refresh=self._refresh_queue,
            on_lock=self._lock_session,
            on_settings=self._open_settings,
            on_folder_selected=lambda _folder_id: None,
            on_rename=rename,
            on_move=move,
            on_delete=delete,
        )
        self._explorer.pack(fill="both", expand=True)

        self._drawer = ProgressDrawer(self._main_frame)
        self._drawer.pack(fill="x")
        self._drawer.show_idle()

        self._refresh_queue()

    def _open_settings(self) -> None:
        def run_test(values: SettingsValues) -> TestClientApiDialogResult:
            result = self._receiver.test_client_api(values)
            return TestClientApiDialogResult(
                ok=result.ok,
                stage=result.stage,
                message=result.message,
            )

        dialog = SettingsDialog(
            self._root,
            self._settings,
            on_test_client_api=run_test,
        )
        if dialog.values is not None:
            self._settings = dialog.values
            try:
                env_path = save_settings_env(self._settings)
            except OSError as error:
                messagebox.showerror(
                    "Settings not saved",
                    f"Could not write config file:\n{error}",
                    parent=self._root,
                )
                return
            messagebox.showinfo(
                "Settings saved",
                f"Config written to:\n{env_path}\n\n"
                "Next: click Sign in to Telegram… on the Client API tab "
                "(one-time phone login), then Test Client API.",
                parent=self._root,
            )

    def _lock_session(self) -> None:
        self._session = None
        self._show_unlock()

    def _on_unlock(self, profile_name: str, encryption_key: str) -> None:
        try:
            self._session = self._receiver.unlock_session(profile_name, encryption_key)
        except Exception as error:
            message = format_user_error("Unlock", error)
            error_code = getattr(error, "code", "")
            if "Wrong encryption key" in str(error) or error_code == "wrong_encryption_key":
                message = "Wrong encryption key."
            messagebox.showerror("Unlock failed", message, parent=self._root)
            return
        self._show_main()

    def _on_create_database(self, profile_name: str, encryption_key: str) -> None:
        try:
            self._session = self._receiver.create_database(profile_name, encryption_key)
        except Exception as error:
            message = format_user_error("Create database", error)
            if getattr(error, "code", "") == "profile_already_exists":
                message = f"Database already exists: {profile_name}"
            messagebox.showerror("Create database failed", message, parent=self._root)
            return
        messagebox.showinfo(
            "Database created",
            f"Database '{profile_name}' was created.\n\n"
            "Your encryption key unlocks this database and decrypts archives.",
            parent=self._root,
        )
        self._show_main()

    def _require_session(self) -> UUID | None:
        if self._session is None:
            messagebox.showwarning(
                "No session",
                "Unlock a session before continuing.",
                parent=self._root,
            )
            return None
        return self._session.session_id

    def _load_folders(self) -> tuple[FolderViewDTO, ...]:
        session_id = self._require_session()
        if session_id is None:
            return ()
        return self._receiver.list_folders(session_id)

    def _on_create_folder(self, name: str) -> None:
        session_id = self._require_session()
        if session_id is None or self._explorer is None:
            return
        try:
            folder = self._receiver.create_folder(session_id, name)
        except Exception as error:
            messagebox.showerror(
                "Create folder failed",
                format_user_error("Create folder", error),
                parent=self._root,
            )
            return
        self._explorer.set_folders(self._load_folders())
        self._explorer.select_folder(folder.folder_id)

    def _on_add_file(self, source_path: Path, display_name: str, folder_id: UUID | None) -> None:
        session_id = self._require_session()
        if session_id is None or self._drawer is None:
            return

        try:
            self._receiver.enqueue_file(session_id, source_path, display_name, folder_id)
        except Exception as error:
            self._drawer.show_result("Add failed", format_user_error("Enqueue", error))
            messagebox.showerror(
                "Enqueue failed",
                format_user_error("Enqueue", error),
                parent=self._root,
            )
            return

        self._drawer.show_result(
            "File queued",
            f"{display_name} — click Start Backup when ready.",
        )
        self._refresh_queue()

    def _on_start_backup(self) -> None:
        session_id = self._require_session()
        if session_id is None or self._drawer is None:
            return

        self._drawer.show_working("Starting backup", "Sending queued items to workers")
        try:
            snapshot = self._receiver.get_session_queue_snapshot(session_id)
            enqueued = self._receiver.start_backup(session_id)
        except Exception as error:
            self._drawer.show_result("Backup failed", format_user_error("Backup", error))
            messagebox.showerror(
                "Backup failed",
                format_user_error("Backup", error),
                parent=self._root,
            )
            return

        if enqueued == 0:
            status_lines = _format_item_status_summary(snapshot)
            detail = (
                "No queued files were sent to workers.\n\n"
                f"{status_lines}\n\n"
                "Stuck items from a previous session (uploading/failed) are retried "
                "automatically when possible — if you still see this, add the file again "
                "or check Settings → Client API → Test Client API."
            )
            self._drawer.show_result("Nothing to enqueue", detail)
            messagebox.showwarning("Nothing to enqueue", detail, parent=self._root)
        else:
            detail = f"Enqueued {enqueued} item(s) for processing."
            self._drawer.show_result("Backup started", detail)
            messagebox.showinfo("Backup started", detail, parent=self._root)
        self._refresh_queue()

    def _on_restore(self) -> None:
        if self._restore_running:
            return

        session_id = self._require_session()
        if session_id is None or self._drawer is None:
            return

        dest = self._pick_restore_destination()
        if dest is None:
            return

        folder_id = self._explorer.selected_folder_id() if self._explorer is not None else None
        self._begin_restore_ui(dest)

        def worker() -> None:
            try:
                preflight = self._receiver.check_restore_ready(session_id, folder_id=folder_id)
            except Exception as error:
                detail = format_user_error("Restore check", error)
                self._root.after(0, lambda: self._finish_restore_failed(detail))
                return
            if not preflight.ready:
                self._root.after(
                    0,
                    lambda: self._finish_restore_failed(preflight.message, warning=True),
                )
                return
            try:
                result = self._receiver.request_restore(
                    session_id,
                    dest,
                    folder_id=folder_id,
                )
            except Exception as error:
                detail = format_user_error("Restore", error)
                self._root.after(0, lambda: self._finish_restore_failed(detail))
                return
            self._root.after(0, lambda: self._finish_restore_success(result, dest))

        threading.Thread(target=worker, daemon=True).start()

    def _begin_restore_ui(self, dest: Path) -> None:
        self._restore_running = True
        self._restore_dest = dest
        self._restore_tick_start = time.monotonic()
        if self._explorer is not None:
            self._explorer.set_toolbar_enabled(False)
        self._update_restore_progress()
        self._root.update_idletasks()

    def _update_restore_progress(self) -> None:
        if not self._restore_running or self._drawer is None or self._restore_dest is None:
            return
        elapsed = int(time.monotonic() - (self._restore_tick_start or time.monotonic()))
        self._drawer.show_restoring(
            "Downloading volumes from Telegram and extracting with 7z.\n"
            f"Elapsed: {elapsed}s — large files may take several minutes.\n"
            f"Destination: {self._restore_dest.resolve()}"
        )
        self._restore_tick_job = self._root.after(1000, self._update_restore_progress)

    def _end_restore_ui(self) -> None:
        self._restore_running = False
        self._restore_dest = None
        self._restore_tick_start = None
        if self._restore_tick_job is not None:
            self._root.after_cancel(self._restore_tick_job)
            self._restore_tick_job = None
        if self._explorer is not None:
            self._explorer.set_toolbar_enabled(True)

    def _pick_restore_destination(self) -> Path | None:
        initial_dir = default_restore_dir()
        dest_path = filedialog.askdirectory(
            title="Select restore destination",
            initialdir=str(initial_dir),
        )
        if not dest_path:
            return None

        dest = Path(dest_path)
        if is_under_install_root(dest):
            proceed = messagebox.askyesno(
                "Install directory selected",
                (
                    f"{dest.resolve()} is under the application install path.\n\n"
                    "This folder is often not writable after a .deb install.\n"
                    "Use a folder in your home directory (for example ~/Restored/).\n\n"
                    "Continue anyway?"
                ),
                parent=self._root,
            )
            if not proceed:
                return None

        existing_files: list[Path] = []
        if dest.is_dir():
            existing_files = [path for path in dest.iterdir() if path.is_file()]
        blocked = readonly_existing_files(dest)
        if blocked:
            proceed = messagebox.askyesno(
                "Read-only files in destination",
                (
                    f"{len(blocked)} file(s) in {dest} are read-only and may block restore:\n"
                    f"• {blocked[0].name}"
                    f"{f' … and {len(blocked) - 1} more' if len(blocked) > 1 else ''}\n\n"
                    "Choose an empty writable folder or remove those files.\n\n"
                    "Continue anyway?"
                ),
                parent=self._root,
            )
            if not proceed:
                return None
        elif existing_files:
            proceed = messagebox.askyesno(
                "Restore destination not empty",
                (
                    f"{dest} already contains {len(existing_files)} file(s).\n\n"
                    "Restore will add extracted files here. "
                    "Choose an empty folder to avoid confusion.\n\n"
                    "Continue anyway?"
                ),
                parent=self._root,
            )
            if not proceed:
                return None

        return dest

    def _finish_restore_failed(self, detail: str, *, warning: bool = False) -> None:
        self._end_restore_ui()
        if self._drawer is not None:
            title = "Restore unavailable" if warning else "Restore failed"
            self._drawer.show_result(title, detail)
        if warning:
            messagebox.showwarning("Restore unavailable", detail, parent=self._root)
        else:
            messagebox.showerror("Restore failed", detail, parent=self._root)

    def _finish_restore_success(self, result: RestoreResultDTO, dest: Path) -> None:
        self._end_restore_ui()
        if result.downloaded_paths:
            files_list = "\n".join(
                f"• {Path(path).resolve()}" for path in result.downloaded_paths[:10]
            )
            if len(result.downloaded_paths) > 10:
                files_list += f"\n• … and {len(result.downloaded_paths) - 10} more"
            detail = (
                f"Restored to {dest.resolve()}\n\n"
                f"Extracted {len(result.downloaded_paths)} file(s):\n{files_list}"
            )
        else:
            detail = (
                f"No files were restored to {dest.resolve()}. "
                "Check session volumes and encryption key."
            )
        if self._drawer is not None:
            self._drawer.show_result("Restore complete", detail)
        messagebox.showinfo("Restore complete", detail, parent=self._root)

    def _refresh_queue(self) -> None:
        session_id = self._require_session()
        if session_id is None or self._explorer is None:
            return

        try:
            snapshot = self._receiver.get_session_queue_snapshot(session_id)
        except Exception as error:
            messagebox.showerror(
                "Queue refresh failed",
                format_user_error("Queue refresh", error),
                parent=self._root,
            )
            return

        self._explorer.render_queue_snapshot(snapshot)


def _format_item_status_summary(snapshot: SessionQueueSnapshotDTO) -> str:
    if not snapshot.items:
        return "The queue is empty — use Add File first."
    counts: dict[str, int] = {}
    for item in snapshot.items:
        key = item.status.lower()
        counts[key] = counts.get(key, 0) + 1
    parts = [f"  • {status}: {count}" for status, count in sorted(counts.items())]
    return "Current items in this database:\n" + "\n".join(parts)
