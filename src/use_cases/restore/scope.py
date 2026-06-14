"""Restore scope: All files (whole session) vs a single virtual folder."""

from __future__ import annotations

from uuid import UUID

from use_cases.shared.folders import is_default_folder_name
from use_cases.shared.persistence import SourceItemRecord


def is_session_wide_restore_scope(folder_id: UUID | None, folder_name: str | None) -> bool:
    """True when restore targets the whole session (GUI «All files»), not one folder."""
    return folder_id is None or is_default_folder_name(folder_name or "")


def source_item_ids_in_restore_scope(
    source_items: list[SourceItemRecord],
    folder_id: UUID | None,
    folder_name: str | None,
) -> set[UUID]:
    """Source item IDs included in the current restore scope (session or one folder)."""
    if is_session_wide_restore_scope(folder_id, folder_name):
        return {item.id for item in source_items}
    return {item.id for item in source_items if item.folder_id == folder_id}


def filter_restorable_ids_by_folder(
    *,
    restorable_ids_in_session: set[UUID],
    source_items: list[SourceItemRecord],
    folder_id: UUID | None,
    folder_name: str | None,
) -> set[UUID]:
    """Narrow session-restorable item IDs to the sidebar folder the user selected.

    ``All files`` keeps every restorable item in the session.
    Any other folder keeps only items whose ``folder_id`` matches.
    """
    if is_session_wide_restore_scope(folder_id, folder_name):
        return restorable_ids_in_session
    return {
        item.id
        for item in source_items
        if item.id in restorable_ids_in_session and item.folder_id == folder_id
    }
