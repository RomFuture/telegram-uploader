"""Restore destination folder checks (writable by the current process)."""

import os
from pathlib import Path

import domain as domain

_WRITE_PROBE_NAME = ".telegram-uploader-write-probe"


def validate_restore_dest_path(dest_path: Path) -> None:
    """Raise DomainError when the process cannot create or overwrite files in dest_path."""
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise domain.DomainError.restore_destination_not_writable(dest_path, str(error)) from error

    if not os.access(dest_path, os.W_OK | os.X_OK):
        raise domain.DomainError.restore_destination_not_writable(
            dest_path,
            "The folder is not writable by your user account.",
        )

    probe = dest_path / _WRITE_PROBE_NAME
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as error:
        raise domain.DomainError.restore_destination_not_writable(dest_path, str(error)) from error
