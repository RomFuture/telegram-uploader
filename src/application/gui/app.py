"""Tkinter MVP: session setup, queue, progress, restore."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from uuid import UUID

from application.backend_receiver import BackendReceiver, ProgressDTO, SessionViewDTO


class BackupApp:
    def __init__(self, receiver: BackendReceiver) -> None:
        self._receiver = receiver
        self._session: SessionViewDTO | None = None

        self._root = tk.Tk()
        self._root.title("Telegram Uploader")
        self._root.minsize(640, 480)

        self._profile_var = tk.StringVar(value="default")
        self._key_var = tk.StringVar(value="")
        self._session_status_var = tk.StringVar(value="No active session")
        self._queue_status_var = tk.StringVar(value="Queue is empty")

        self._build_layout()

    def run(self) -> None:
        self._root.mainloop()

    def _build_layout(self) -> None:
        session_frame = ttk.LabelFrame(self._root, text="Session", padding=8)
        session_frame.pack(fill="x", padx=8, pady=8)

        ttk.Label(session_frame, text="Profile name").grid(row=0, column=0, sticky="w")
        ttk.Entry(session_frame, textvariable=self._profile_var, width=40).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        ttk.Label(session_frame, text="Encryption key").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Entry(session_frame, textvariable=self._key_var, width=40, show="*").grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0)
        )

        ttk.Button(session_frame, text="Start Session", command=self._on_start_session).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0)
        )
        ttk.Label(session_frame, textvariable=self._session_status_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        session_frame.columnconfigure(1, weight=1)

        queue_frame = ttk.LabelFrame(self._root, text="Queue", padding=8)
        queue_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columns = ("display_name", "status")
        self._tree = ttk.Treeview(queue_frame, columns=columns, show="headings", height=12)
        self._tree.heading("display_name", text="Display name")
        self._tree.heading("status", text="Status")
        self._tree.column("display_name", width=360)
        self._tree.column("status", width=120)
        self._tree.pack(fill="both", expand=True)

        buttons = ttk.Frame(queue_frame)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Add File", command=self._on_add_file).pack(side="left")
        ttk.Button(buttons, text="Start Backup", command=self._on_start_backup).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="Refresh Progress", command=self._on_refresh_progress).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(buttons, text="Restore Session", command=self._on_restore).pack(side="right")

        ttk.Label(self._root, textvariable=self._queue_status_var).pack(
            anchor="w", padx=8, pady=(0, 8)
        )

    def _require_session(self) -> UUID | None:
        if self._session is None:
            messagebox.showwarning("No session", "Start a session before continuing.")
            return None
        return self._session.session_id

    def _on_start_session(self) -> None:
        profile_name = self._profile_var.get().strip()
        if not profile_name:
            messagebox.showerror("Invalid input", "Profile name is required.")
            return

        encryption_key = self._key_var.get().strip()
        if not encryption_key:
            encryption_key = "auto-generated-key"

        try:
            self._session = self._receiver.start_session(profile_name, encryption_key)
        except Exception as error:
            messagebox.showerror("Session failed", str(error))
            return

        self._session_status_var.set(
            f"Session {self._session.session_id} ({self._session.status})"
        )
        self._refresh_queue()

    def _on_add_file(self) -> None:
        session_id = self._require_session()
        if session_id is None:
            return

        source_path = filedialog.askopenfilename(title="Select file to back up")
        if not source_path:
            return

        path = Path(source_path)
        display_name = simpledialog.askstring(
            "Display name",
            "Enter the name shown in the queue:",
            initialvalue=path.name,
            parent=self._root,
        )
        if not display_name or not display_name.strip():
            messagebox.showerror("Invalid input", "Display name is required.")
            return

        try:
            self._receiver.enqueue_file(session_id, path, display_name.strip())
        except Exception as error:
            messagebox.showerror("Enqueue failed", str(error))
            return

        self._refresh_queue()

    def _on_start_backup(self) -> None:
        session_id = self._require_session()
        if session_id is None:
            return

        try:
            enqueued = self._receiver.start_backup(session_id)
        except Exception as error:
            messagebox.showerror("Backup failed", str(error))
            return

        messagebox.showinfo("Backup started", f"Enqueued {enqueued} item(s) for processing.")
        self._refresh_queue()

    def _on_refresh_progress(self) -> None:
        self._refresh_queue()

    def _on_restore(self) -> None:
        session_id = self._require_session()
        if session_id is None:
            return

        dest_path = filedialog.askdirectory(title="Select restore destination")
        if not dest_path:
            return

        try:
            result = self._receiver.request_restore(session_id, Path(dest_path))
        except Exception as error:
            messagebox.showerror("Restore failed", str(error))
            return

        messagebox.showinfo(
            "Restore complete",
            f"Downloaded {len(result.downloaded_paths)} file(s) to {dest_path}.",
        )

    def _refresh_queue(self) -> None:
        session_id = self._require_session()
        if session_id is None:
            return

        try:
            progress = self._receiver.get_session_progress(session_id)
        except Exception as error:
            messagebox.showerror("Progress failed", str(error))
            return

        self._render_progress(progress)

    def _render_progress(self, progress: ProgressDTO) -> None:
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        for item in progress.items:
            self._tree.insert(
                "",
                "end",
                values=(item.display_name, item.status),
            )

        if progress.items:
            self._queue_status_var.set(f"{len(progress.items)} item(s) in queue")
        else:
            self._queue_status_var.set("Queue is empty")
