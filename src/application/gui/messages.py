"""User-facing message copy for GUI dialogs (no Tkinter)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

BACKUP_IN_PROGRESS_STATUSES = frozenset(
    {"queued", "archiving", "uploading", "cleanup", "processing"}
)


def format_restore_saved_message(dest: Path, paths: tuple[str, ...] | list[str]) -> str:
    """Folder-first copy for restore success."""
    folder = dest.resolve()
    header = f"Your file(s) were saved to this folder:\n\n{folder}"
    if not paths:
        return (
            f"{header}\n\n"
            "Nothing was extracted. Check session volumes and encryption key."
        )
    files_list = "\n".join(f"• {Path(path).resolve()}" for path in paths[:10])
    if len(paths) > 10:
        files_list += f"\n• … and {len(paths) - 10} more"
    return f"{header}\n\nExtracted {len(paths)} file(s):\n{files_list}"


def is_backup_pipeline_idle(statuses: Iterable[str]) -> bool:
    """True when the queue has items and none are still in the backup pipeline."""
    normalized = [status.lower() for status in statuses]
    if not normalized:
        return False
    return all(status not in BACKUP_IN_PROGRESS_STATUSES for status in normalized)


def count_backup_outcomes(statuses: Iterable[str]) -> tuple[int, int]:
    completed = 0
    failed = 0
    for status in statuses:
        normalized = status.lower()
        if normalized == "completed":
            completed += 1
        elif normalized in {"failed", "error"}:
            failed += 1
    return completed, failed


def format_backup_complete_message(completed: int, failed: int) -> str:
    lines = ["Backup complete.", ""]
    if completed:
        lines.append(f"{completed} file(s) uploaded to your Telegram backup group.")
    if failed:
        lines.append(f"{failed} file(s) failed.")
    if not completed and not failed:
        lines.append("No files were processed.")
    return "\n".join(lines)
