import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from observation.restore_download_progress import make_download_progress_callback
from observation.restore_session_log import (
    log_download_finished,
    log_download_starting,
    log_extract_complete,
    log_extract_starting,
    log_restore_complete,
    log_restore_started,
)
from use_cases.restore.download_volume import download_volume_to_dir
from use_cases.restore.refs import source_item_ids_restorable_in_session
from use_cases.restore.scope import filter_restorable_ids_by_folder, is_session_wide_restore_scope
from use_cases.shared.ports.archive_service import ArchiveServicePort
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.repositories.source_item import SourceItemRepository
from use_cases.shared.types import ArchiveVolume

_WRITE_PROBE_NAME = ".telegram-uploader-write-probe"


def validate_restore_dest_path(dest_path: Path) -> None:
    """Raise DomainError when the process cannot create or overwrite files in dest_path."""
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise domain.DomainError.restore_destination_not_writable(dest_path, str(error)) from error

    if not os.access(dest_path, os.W_OK | os.X_OK):
        raise domain.DomainError.restore_destination_not_writable(
            dest_path,
            "The folder is not writable by your user account.",
        )

    probe = dest_path / _WRITE_PROBE_NAME
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as error:
        raise domain.DomainError.restore_destination_not_writable(dest_path, str(error)) from error


@dataclass(frozen=True, slots=True)
class RestoreSessionUseCase:
    sessions: SessionRepository
    source_items: SourceItemRepository
    folders: FolderRepository
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    archive_service: ArchiveServicePort
    staging_dir: Path

    def execute(
        self,
        session_id: UUID,
        dest_path: Path,
        *,
        folder_id: UUID | None = None,
    ) -> list[Path]:
        session = self.sessions.require(session_id)
        volumes = self.archive_volumes.require_for_session(session_id)
        restorable_ids_in_session = source_item_ids_restorable_in_session(
            volumes, self.storage_provider
        )
        if not restorable_ids_in_session:
            raise domain.DomainError.no_restorable_backups(session_id)

        folder_name = self._folder_name(folder_id)
        source_item_records = self.source_items.list_by_session(session_id)
        restorable_ids_in_scope = filter_restorable_ids_by_folder(
            restorable_ids_in_session=restorable_ids_in_session,
            source_items=source_item_records,
            folder_id=folder_id,
            folder_name=folder_name,
        )
        if not restorable_ids_in_scope:
            scope = folder_name or "selected folder"
            raise domain.DomainError.no_restorable_backups_in_folder(scope)

        volumes_to_restore = [
            volume for volume in volumes if volume.source_item_id in restorable_ids_in_scope
        ]

        validate_restore_dest_path(dest_path)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        scope_label = (
            "all files in session"
            if is_session_wide_restore_scope(folder_id, folder_name)
            else f"folder {folder_name!r}"
        )
        log_restore_started(
            session_id,
            dest_path,
            scope_label,
            item_count=len(restorable_ids_in_scope),
            volume_count=len(volumes_to_restore),
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
                log_download_starting(label)
                progress = make_download_progress_callback(label=label)
                downloaded.append(
                    download_volume_to_dir(
                        volume,
                        self.storage_provider,
                        self.staging_dir,
                        on_progress=progress,
                    )
                )
                log_download_finished(label, downloaded[-1])
            log_extract_starting(
                item_index,
                total_items,
                part_count=len(sorted_volumes),
                dest_path=dest_path,
            )
            extracted_paths.append(
                self.archive_service.extract(
                    volume_paths=downloaded,
                    dest_dir=dest_path,
                    encryption_key=session.encryption_key,
                )
            )
            log_extract_complete(item_index, total_items, extracted_paths[-1])

        log_restore_complete(session_id, scope_label, extracted_count=len(extracted_paths))
        return extracted_paths

    def _folder_name(self, folder_id: UUID | None) -> str | None:
        if folder_id is None:
            return None
        folder = self.folders.get(folder_id)
        return folder.name if folder is not None else None
