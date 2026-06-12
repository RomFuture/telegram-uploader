"""Shared restore download step for session- and volume-scoped use cases."""

from pathlib import Path

from use_cases.restore.refs import restore_ref_for_volume
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.types import ArchiveVolume


def download_volume_to_dir(
    volume: ArchiveVolume,
    storage_provider: StorageProviderPort,
    destination_dir: Path,
    target_chat_id: str,
) -> Path:
    download_ref = restore_ref_for_volume(volume, target_chat_id)
    file_info = storage_provider.get_file_info(download_ref)
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / volume.file_name
    return storage_provider.download_file(file_info, target)
