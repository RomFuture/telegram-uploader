"""User-facing copy for restore preflight checks."""

from __future__ import annotations

from application.restore_preflight_scope import RestorePreflightScope
from use_cases.public.results import RestorePreflightReason, RestorePreflightResult

_STALE_BACKUP_MESSAGE = (
    "No restorable backups yet.\n\n"
    "{count} file(s) from a previous session did not finish uploading to Telegram.\n"
    "Click Start Backup to retry them.\n\n"
    "If upload keeps failing, check TELEGRAM_SESSION_DIR, chat id, and "
    "Settings → Client API → Test Client API."
)

_INCOMPLETE_UPLOAD_MESSAGE = (
    "Archive exists but Telegram upload did not finish.\n\n"
    "Check:\n"
    "1) Session file is shared with Docker (TELEGRAM_SESSION_DIR in .env)\n"
    "2) TELEGRAM_TARGET_CHAT_ID is correct\n"
    "3) Settings → Client API → Test Client API\n\n"
    "Worker logs: docker compose logs celery-worker-upload"
)

_HEALTHCHECK_FAIL_MESSAGE = (
    "Telegram Client API is not ready on this machine.\n\n"
    "Settings → Client API → Sign in to Telegram… (one time),\n"
    "then Test Client API.\n"
    "Or in a terminal: telegram-uploader-login"
)


def _scope_label(scope: RestorePreflightScope) -> str:
    if scope.restore_entire_session:
        return "all files"
    folder_name = scope.folder_name or "this folder"
    return f"folder {folder_name!r}"


def _legacy_skip_note(result: RestorePreflightResult, scope: RestorePreflightScope) -> str:
    count = result.legacy_volume_count
    scope_label = _scope_label(scope)
    return (
        f"{count} legacy Bot API backup volume(s) in {scope_label} will be skipped.\n"
        "Re-backup with TELEGRAM_PROVIDER=client to restore them."
    )


def format_restore_preflight_message(
    result: RestorePreflightResult,
    scope: RestorePreflightScope,
) -> str:
    """Map a use-case preflight result to English GUI copy."""
    match result.reason:
        case RestorePreflightReason.NO_VOLUMES:
            return "No backup volumes found for this database. Run Start Backup first."
        case RestorePreflightReason.EMPTY_FOLDER:
            folder_name = scope.folder_name or "this folder"
            return (
                f"No completed backups in {folder_name}.\n\n"
                "Select All files or a folder with backed-up files."
            )
        case RestorePreflightReason.LEGACY_VOLUMES:
            scope_label = _scope_label(scope)
            return (
                f"Nothing to restore in {scope_label}.\n\n"
                f"{result.legacy_volume_count} legacy Bot API backup volume(s) skipped.\n"
                "Re-backup with TELEGRAM_PROVIDER=client to restore them."
            )
        case RestorePreflightReason.STALE_BACKUP:
            return _STALE_BACKUP_MESSAGE.format(count=result.incomplete_volume_count)
        case RestorePreflightReason.INCOMPLETE_UPLOAD:
            return _INCOMPLETE_UPLOAD_MESSAGE
        case RestorePreflightReason.HEALTHCHECK_FAILED:
            return _HEALTHCHECK_FAIL_MESSAGE
        case RestorePreflightReason.READY:
            scope_label = _scope_label(scope)
            lines = [f"Ready to restore {result.restorable_count} file(s) from {scope_label}."]
            if result.legacy_volume_count > 0:
                lines.append("")
                lines.append(_legacy_skip_note(result, scope))
            if result.incomplete_volume_count > 0:
                lines.append("")
                lines.append(
                    f"{result.incomplete_volume_count} unfinished archive part(s) from older "
                    "failed backups will be skipped.\n"
                    "Click Start Backup to retry those files."
                )
            return "\n".join(lines)
        case _:
            return "Restore check failed. Check logs or try again."
