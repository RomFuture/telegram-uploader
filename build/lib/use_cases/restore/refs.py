"""Restore download reference selection for provider calls."""

from collections import defaultdict
from uuid import UUID

import domain as domain
from use_cases.shared.types import ArchiveVolume


def restore_ref_for_volume(volume: ArchiveVolume, target_chat_id: str) -> str:
    """Which provider ref to use for restore download (Client API ref preferred)."""
    if volume.provider_download_ref:
        return volume.provider_download_ref
    if volume.external_message_id is not None:
        return f"message:{target_chat_id}:{volume.external_message_id}"
    if volume.external_file_id is not None:
        return volume.external_file_id
    raise domain.DomainError.missing_external_file_id(volume.id)


def restore_download_ref(volume: ArchiveVolume) -> str:
    """Legacy alias without chat context; falls back to external_file_id only."""
    if volume.provider_download_ref:
        return volume.provider_download_ref
    if volume.external_file_id is None:
        raise domain.DomainError.missing_external_file_id(volume.id)
    return volume.external_file_id


def external_file_id_for_restore(volume: ArchiveVolume) -> str:
    """Legacy alias; prefer restore_ref_for_volume."""
    return restore_download_ref(volume)


def is_volume_restorable(volume: ArchiveVolume, target_chat_id: str) -> bool:
    """Volume was uploaded to Telegram with a Client API download ref."""
    if volume.status != domain.ArchiveVolumeStatus.UPLOADED:
        return False
    try:
        ref = restore_ref_for_volume(volume, target_chat_id)
    except domain.DomainError:
        return False
    return ref.startswith("client:")


def restorable_source_item_ids(
    volumes: list[ArchiveVolume],
    target_chat_id: str,
) -> set[UUID]:
    """Source items whose archive volumes are all uploaded and restorable."""
    by_item: dict[UUID, list[ArchiveVolume]] = defaultdict(list)
    for volume in volumes:
        by_item[volume.source_item_id].append(volume)

    restorable: set[UUID] = set()
    for item_id, item_volumes in by_item.items():
        if item_volumes and all(
            is_volume_restorable(volume, target_chat_id) for volume in item_volumes
        ):
            restorable.add(item_id)
    return restorable
