"""Restore download reference selection for provider calls."""

from collections import defaultdict
from uuid import UUID

import domain as domain
from use_cases.shared.types import ArchiveVolume

CLIENT_RESTORE_REF_PREFIX = "client:"


def is_client_restore_ref(ref: str) -> bool:
    """True when ref is a Client API download ref stored at upload time."""
    return ref.startswith(CLIENT_RESTORE_REF_PREFIX)


def has_legacy_bot_volumes(volumes: list[ArchiveVolume]) -> bool:
    """Uploaded volumes that predate Client API refs (Bot API backups)."""
    return any(
        volume.status == domain.ArchiveVolumeStatus.UPLOADED
        and volume.provider_download_ref
        and not is_client_restore_ref(volume.provider_download_ref)
        for volume in volumes
    )


def restore_ref_for_volume(volume: ArchiveVolume, target_chat_id: str) -> str:
    """Client API download ref required for restore (v1 policy)."""
    _ = target_chat_id
    ref = volume.provider_download_ref
    if ref and is_client_restore_ref(ref):
        return ref
    if ref and not is_client_restore_ref(ref):
        raise domain.DomainError.legacy_volumes()
    raise domain.DomainError.missing_external_file_id(volume.id)


def is_volume_restorable(volume: ArchiveVolume, target_chat_id: str) -> bool:
    """Volume was uploaded to Telegram with a Client API download ref."""
    _ = target_chat_id
    if volume.status != domain.ArchiveVolumeStatus.UPLOADED:
        return False
    ref = volume.provider_download_ref
    return ref is not None and is_client_restore_ref(ref)


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
