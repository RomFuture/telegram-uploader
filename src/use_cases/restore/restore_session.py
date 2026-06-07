from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from use_cases.domain.errors import ArchiveVolumeNotFound
from use_cases.ports.storage_provider import StorageProviderPort
from use_cases.repositories.archive_volume import ArchiveVolumeRepository


@dataclass(frozen=True, slots=True)
class RestoreSessionUseCase:
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    staging_dir: Path

    def execute(self, session_id: UUID, dest_path: Path) -> list[Path]:
        volumes = self.archive_volumes.list_by_session(session_id)
        if not volumes:
            raise ArchiveVolumeNotFound

        dest_path.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        downloaded: list[Path] = []
        for volume in volumes:
            if volume.external_file_id is None:
                raise ArchiveVolumeNotFound
            file_info = self.storage_provider.get_file_info(volume.external_file_id)
            target = self.staging_dir / volume.file_name
            self.storage_provider.download_file(file_info, target)
            downloaded.append(target)

        return downloaded
