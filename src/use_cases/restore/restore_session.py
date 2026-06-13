import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.restore.dest_path import validate_restore_dest_path
from use_cases.restore.download_progress import make_download_progress_callback
from use_cases.restore.download_volume import download_volume_to_dir
from use_cases.restore.refs import has_legacy_bot_volumes, restorable_source_item_ids
from use_cases.restore.scope import restorable_source_item_ids_for_folder
from use_cases.shared.folders import is_default_folder_name
from use_cases.shared.ports.archive_service import ArchiveServicePort
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.repositories.source_item import SourceItemRepository
from use_cases.shared.types import ArchiveVolume

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RestoreSessionUseCase:
    sessions: SessionRepository
    source_items: SourceItemRepository
    folders: FolderRepository
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    archive_service: ArchiveServicePort
    staging_dir: Path
    target_chat_id: str

    def execute(
        self,
        session_id: UUID,
        dest_path: Path,
        *,
        folder_id: UUID | None = None,
    ) -> list[Path]:
        session = self.sessions.require(session_id)
        volumes = self.archive_volumes.require_for_session(session_id)
        all_restorable = restorable_source_item_ids(volumes, self.target_chat_id)
        if not all_restorable:
            if has_legacy_bot_volumes(volumes):
                raise domain.DomainError.legacy_volumes()
            raise domain.DomainError.no_restorable_backups(session_id)

        folder_name = self._folder_name(folder_id)
        source_item_records = self.source_items.list_by_session(session_id)
        restorable_items = restorable_source_item_ids_for_folder(
            all_restorable=all_restorable,
            source_items=source_item_records,
            folder_id=folder_id,
            folder_name=folder_name,
        )
        if not restorable_items:
            scope = folder_name or "selected folder"
            raise domain.DomainError.no_restorable_backups_in_folder(scope)

        volumes_to_restore = [
            volume for volume in volumes if volume.source_item_id in restorable_items
        ]

        validate_restore_dest_path(dest_path)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        scope_label = (
            "all files in session"
            if folder_id is None or is_default_folder_name(folder_name or "")
            else f"folder {folder_name!r}"
        )
        logger.info(
            "restore started session_id=%s dest=%s scope=%s items=%d volumes=%d",
            session_id,
            dest_path,
            scope_label,
            len(restorable_items),
            len(volumes_to_restore),
        )

        by_item: dict[UUID, list[ArchiveVolume]] = defaultdict(list)
        for volume in volumes_to_restore:
            by_item[volume.source_item_id].append(volume)

        extracted_paths: list[Path] = []
        item_index = 0
        total_items = len(by_item)
        for item_volumes in by_item.values():
            item_index += 1
            sorted_volumes = sorted(item_volumes, key=lambda volume: volume.part_number)
            downloaded: list[Path] = []
            for part_index, volume in enumerate(sorted_volumes, start=1):
                label = (
                    f"{volume.file_name} item {item_index}/{total_items} "
                    f"part {part_index}/{len(sorted_volumes)}"
                )
                logger.info("download starting %s", label)
                progress = make_download_progress_callback(label=label)
                downloaded.append(
                    download_volume_to_dir(
                        volume,
                        self.storage_provider,
                        self.staging_dir,
                        self.target_chat_id,
                        on_progress=progress,
                    )
                )
                logger.info("download finished %s -> %s", label, downloaded[-1])
            logger.info(
                "extract starting item %d/%d parts=%d dest=%s",
                item_index,
                total_items,
                len(sorted_volumes),
                dest_path,
            )
            extracted_paths.append(
                self.archive_service.extract(
                    volume_paths=downloaded,
                    dest_dir=dest_path,
                    encryption_key=session.encryption_key,
                )
            )
            logger.info(
                "extract complete item %d/%d -> %s",
                item_index,
                total_items,
                extracted_paths[-1],
            )

        logger.info(
            "restore complete session_id=%s scope=%s extracted=%d path(s)",
            session_id,
            scope_label,
            len(extracted_paths),
        )
        return extracted_paths

    def _folder_name(self, folder_id: UUID | None) -> str | None:
        if folder_id is None:
            return None
        folder = self.folders.get(folder_id)
        return folder.name if folder is not None else None
