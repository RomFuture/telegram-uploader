"""Restore download reference selection for provider calls."""

import domain as domain
from use_cases.types import ArchiveVolume


def restore_download_ref(volume: ArchiveVolume) -> str:
    """Which provider ref to use for restore download (Client API ref preferred)."""
    if volume.provider_download_ref:
        return volume.provider_download_ref
    if volume.external_file_id is None:
        raise domain.DomainError.missing_external_file_id(volume.id)
    return volume.external_file_id


def external_file_id_for_restore(volume: ArchiveVolume) -> str:
    """Legacy alias; prefer restore_download_ref."""
    return restore_download_ref(volume)
