"""Restore preflight scope from GUI sidebar selection."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RestorePreflightScope:
    folder_name: str | None
    restore_entire_session: bool


def scope_from_folder(
    folder_id: UUID | None,
    folder_name: str | None,
    *,
    restore_entire_session: bool,
) -> RestorePreflightScope:
    """Build scope for preflight copy from explorer selection."""
    _ = folder_id
    return RestorePreflightScope(
        folder_name=folder_name,
        restore_entire_session=restore_entire_session,
    )
