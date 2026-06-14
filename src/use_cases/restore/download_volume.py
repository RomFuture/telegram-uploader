"""Shared restore download step for session- and volume-scoped use cases."""

from collections.abc import Callable
from pathlib import Path

from use_cases.restore.refs import restore_ref_for_volume
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.types import ArchiveVolume


def download_volume_to_dir(
    volume: ArchiveVolume,
    storage_provider: StorageProviderPort,
    destination_dir: Path,
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Resolve ref, fetch metadata, and download one archive volume to destination_dir.

    Shared by RestoreSessionUseCase (GUI in-process restore loop) and
    ProcessRestoreVolumeUseCase (Celery worker hook; staging only, no extract).

    Typical callers: ``RestoreSessionUseCase``, ``ProcessRestoreVolumeUseCase``.
    Raises via ``restore_ref_for_volume`` when the ref is missing or legacy.
    """
    download_ref = restore_ref_for_volume(volume, storage_provider)
    file_info = storage_provider.get_file_info(download_ref)
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / volume.file_name
    return storage_provider.download_file(file_info, target, on_progress=on_progress)
