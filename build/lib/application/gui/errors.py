"""User-facing error formatting for the GUI."""

from __future__ import annotations


def format_user_error(context: str, error: Exception) -> str:
    """Return a short English message without a raw traceback."""
    message = str(error).strip()
    if not message:
        return f"{context} failed. Check logs or try again."
    first_line = message.splitlines()[0]
    if len(first_line) > 240:
        first_line = first_line[:237] + "..."
    return f"{context} failed: {first_line}"
