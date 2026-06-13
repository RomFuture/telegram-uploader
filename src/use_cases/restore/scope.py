"""Restore scope: All files (whole session) vs a single virtual folder."""

from __future__ import annotations

from uuid import UUID

from use_cases.shared.folders import is_default_folder_name
from use_cases.shared.persistence import SourceItemRecord


def restorable_source_item_ids_for_folder(
    *,
    all_restorable: set[UUID],
    source_items: list[SourceItemRecord],
    folder_id: UUID | None,
    folder_name: str | None,
) -> set[UUID]:
    """Filter restorable items by sidebar folder selection.

    ``All files`` is the aggregate view — restore every restorable item in the session.
    Any other folder restores only items whose ``folder_id`` matches.
    """
    if folder_id is None or is_default_folder_name(folder_name or ""):
        return all_restorable
    return {
        item.id
        for item in source_items
        if item.id in all_restorable and item.folder_id == folder_id
    }
