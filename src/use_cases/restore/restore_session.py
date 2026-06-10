from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from use_cases.ports.storage_provider import StorageProviderPort
from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.restore.download_volume import download_volume_to_dir


@dataclass(frozen=True, slots=True)
class RestoreSessionUseCase:
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    staging_dir: Path

    def execute(self, session_id: UUID, dest_path: Path) -> list[Path]:
        volumes = self.archive_volumes.require_for_session(session_id)

        dest_path.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        downloaded: list[Path] = []
        for volume in volumes:
            target = download_volume_to_dir(volume, self.storage_provider, self.staging_dir)
            downloaded.append(target)

        return downloaded
