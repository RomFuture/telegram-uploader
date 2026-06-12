from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.restore.download_volume import download_volume_to_dir
from use_cases.restore.refs import restorable_source_item_ids, restore_ref_for_volume
from use_cases.shared.ports.archive_service import ArchiveServicePort
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.types import ArchiveVolume


@dataclass(frozen=True, slots=True)
class RestoreSessionUseCase:
    sessions: SessionRepository
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    archive_service: ArchiveServicePort
    staging_dir: Path
    target_chat_id: str

    def execute(self, session_id: UUID, dest_path: Path) -> list[Path]:
        session = self.sessions.require(session_id)
        volumes = self.archive_volumes.require_for_session(session_id)
        restorable_items = restorable_source_item_ids(volumes, self.target_chat_id)
        if not restorable_items:
            has_legacy_volumes = any(
                volume.status == domain.ArchiveVolumeStatus.UPLOADED
                and volume.provider_download_ref
                and not volume.provider_download_ref.startswith("client:")
                for volume in volumes
            )
            if has_legacy_volumes:
                raise domain.DomainError.legacy_volumes()
            raise domain.DomainError.no_restorable_backups(session_id)

        volumes_to_restore = [
            volume for volume in volumes if volume.source_item_id in restorable_items
        ]

        for volume in volumes_to_restore:
            ref = restore_ref_for_volume(volume, self.target_chat_id)
            if not ref.startswith("client:"):
                raise domain.DomainError.legacy_volumes()

        dest_path.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        by_item: dict[UUID, list[ArchiveVolume]] = defaultdict(list)
        for volume in volumes_to_restore:
            by_item[volume.source_item_id].append(volume)

        extracted_paths: list[Path] = []
        for item_volumes in by_item.values():
            sorted_volumes = sorted(item_volumes, key=lambda volume: volume.part_number)
            downloaded: list[Path] = []
            for volume in sorted_volumes:
                downloaded.append(
                    download_volume_to_dir(
                        volume,
                        self.storage_provider,
                        self.staging_dir,
                        self.target_chat_id,
                    )
                )
            extracted_paths.append(
                self.archive_service.extract(
                    volume_paths=downloaded,
                    dest_dir=dest_path,
                    encryption_key=session.encryption_key,
                )
            )

        return extracted_paths
