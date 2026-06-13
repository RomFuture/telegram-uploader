"""User-facing error formatting for the GUI."""

from __future__ import annotations

_DOMAIN_ERROR_CODES = frozenset(
    {
        "legacy_volumes",
        "restore_destination_not_writable",
        "no_restorable_backups",
        "no_restorable_backups_in_folder",
    }
)


def format_user_error(context: str, error: Exception) -> str:
    """Return a short English message without a raw traceback."""
    code = getattr(error, "code", None)
    if isinstance(code, str) and code in _DOMAIN_ERROR_CODES:
        message = str(error).strip()
        if message:
            return message

    message = str(error).strip()
    if not message:
        return f"{context} failed. Check logs or try again."
    if "permission denied" in message.lower() or "errno=13" in message.lower():
        return message
    first_line = message.splitlines()[0]
    if len(first_line) > 240:
        first_line = first_line[:237] + "..."
    return f"{context} failed: {first_line}"
