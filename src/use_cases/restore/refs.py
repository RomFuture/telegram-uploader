"""Restore download reference selection for provider calls."""

from collections import defaultdict
from uuid import UUID

import domain as domain
from use_cases.shared.dto import RestoreRefCapability
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.types import ArchiveVolume


def is_volume_restorable(volume: ArchiveVolume, provider: StorageProviderPort) -> bool:
    """Volume was uploaded and the current provider can download it."""
    if volume.status != domain.ArchiveVolumeStatus.UPLOADED:
        return False
    ref = volume.provider_download_ref
    if ref is None:
        return False
    return provider.assess_restore_ref(ref) == RestoreRefCapability.RESTORABLE


def is_legacy_volume(volume: ArchiveVolume, provider: StorageProviderPort) -> bool:
    """Uploaded volume with a ref the current provider marks as legacy."""
    if volume.status != domain.ArchiveVolumeStatus.UPLOADED:
        return False
    ref = volume.provider_download_ref
    if not ref:
        return False
    return provider.assess_restore_ref(ref) == RestoreRefCapability.UNSUPPORTED_LEGACY


def count_legacy_volumes(
    volumes: list[ArchiveVolume],
    provider: StorageProviderPort,
    *,
    source_item_ids: set[UUID] | None = None,
) -> int:
    """Count uploaded legacy volumes, optionally limited to given source items."""
    return sum(
        1
        for volume in volumes
        if (source_item_ids is None or volume.source_item_id in source_item_ids)
        and is_legacy_volume(volume, provider)
    )


def count_incomplete_volumes(
    volumes: list[ArchiveVolume],
    provider: StorageProviderPort,
    *,
    source_item_ids: set[UUID],
) -> int:
    """Non-restorable volumes in scope that are not legacy (upload unfinished, etc.)."""
    return sum(
        1
        for volume in volumes
        if volume.source_item_id in source_item_ids
        and not is_volume_restorable(volume, provider)
        and not is_legacy_volume(volume, provider)
    )


def restore_ref_for_volume(volume: ArchiveVolume, provider: StorageProviderPort) -> str:
    """Download ref for the current storage provider."""
    ref = volume.provider_download_ref
    if not ref:
        raise domain.DomainError.missing_external_file_id(volume.id)
    capability = provider.assess_restore_ref(ref)
    if capability == RestoreRefCapability.UNSUPPORTED_LEGACY:
        raise domain.DomainError.legacy_volumes()
    if capability != RestoreRefCapability.RESTORABLE:
        raise domain.DomainError.missing_external_file_id(volume.id)
    return provider.resolve_restore_ref(ref)


def source_item_ids_restorable_in_session(
    volumes: list[ArchiveVolume],
    provider: StorageProviderPort,
) -> set[UUID]:
    """Source item IDs whose archive volumes can be restored by the current provider."""
    by_item: dict[UUID, list[ArchiveVolume]] = defaultdict(list)
    for volume in volumes:
        by_item[volume.source_item_id].append(volume)

    restorable: set[UUID] = set()
    for item_id, item_volumes in by_item.items():
        if item_volumes and all(
            is_volume_restorable(volume, provider) for volume in item_volumes
        ):
            restorable.add(item_id)
    return restorable
