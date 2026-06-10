from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from use_cases.ports.storage_provider import StorageProviderPort
from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.restore.download_volume import download_volume_to_dir


@dataclass(frozen=True, slots=True)
class ProcessRestoreVolumeUseCase:
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    staging_dir: Path

    def execute(self, archive_volume_id: UUID) -> Path:
        volume = self.archive_volumes.require(archive_volume_id)
        return download_volume_to_dir(volume, self.storage_provider, self.staging_dir)
