from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.ports.storage_provider import StorageProviderPort
from use_cases.repositories.archive_volume import ArchiveVolumeRepository


@dataclass(frozen=True, slots=True)
class ProcessRestoreVolumeUseCase:
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    staging_dir: Path

    def execute(self, archive_volume_id: UUID) -> Path:
        volume = self.archive_volumes.require(archive_volume_id)
        external_file_id = domain.external_file_id_for_restore(volume)
        file_info = self.storage_provider.get_file_info(external_file_id)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        target = self.staging_dir / volume.file_name
        self.storage_provider.download_file(file_info, target)
        return target
