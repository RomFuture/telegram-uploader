"""Public API for application and worker entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from use_cases.backup.cleanup_volume import CleanupVolumeUseCase
from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.backup.process_archive_volume import ProcessArchiveVolumeUseCase
from use_cases.backup.process_upload_volume import ProcessUploadVolumeUseCase
from use_cases.backup.start_backup_pipeline import StartBackupPipelineUseCase
from use_cases.repositories import Repositories
from use_cases.restore.process_restore_volume import ProcessRestoreVolumeUseCase
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.session.create_session import CreateSessionUseCase
from use_cases.types import Session, SourceItem


@dataclass(frozen=True, slots=True)
class SessionView:
    id: UUID
    profile_name: str
    status: str


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    source_item_id: UUID
    display_name: str
    status: str


@dataclass(frozen=True, slots=True)
class SourceItemProgressView:
    source_item_id: UUID
    display_name: str
    status: str


@dataclass(frozen=True, slots=True)
class SessionProgressView:
    session_id: UUID
    items: tuple[SourceItemProgressView, ...]


@dataclass(frozen=True, slots=True)
class BackupFacade:
    """Thin delegation layer: wiring only, no business rules."""

    repos: Repositories
    create_session: CreateSessionUseCase
    enqueue_source_item: EnqueueSourceItemUseCase
    start_backup_pipeline: StartBackupPipelineUseCase
    process_archive: ProcessArchiveVolumeUseCase
    process_upload: ProcessUploadVolumeUseCase
    process_cleanup: CleanupVolumeUseCase
    restore_volume: ProcessRestoreVolumeUseCase
    restore_session: RestoreSessionUseCase

    def start_session(self, profile_name: str, encryption_key: str) -> SessionView:
        session = self.create_session.execute(profile_name, encryption_key)
        return _session_view(session)

    def enqueue_file(
        self,
        session_id: UUID,
        source_path: Path,
        display_name: str,
    ) -> EnqueueResult:
        item = self.enqueue_source_item.execute(session_id, source_path, display_name)
        return _enqueue_result(item)

    def start_backup(self, session_id: UUID) -> int:
        return self.start_backup_pipeline.execute(session_id)

    def get_session_progress(self, session_id: UUID) -> SessionProgressView:
        items = self.repos.source_items.list_by_session(session_id)
        return SessionProgressView(
            session_id=session_id,
            items=tuple(
                SourceItemProgressView(
                    source_item_id=item.id,
                    display_name=item.display_name,
                    status=item.status,
                )
                for item in items
            ),
        )

    def request_restore(self, session_id: UUID, dest_path: Path) -> list[Path]:
        return self.restore_session.execute(session_id, dest_path)

    def process_archive_volume(self, source_item_id: UUID) -> None:
        self.process_archive.execute(source_item_id)

    def process_upload_volume(self, archive_volume_id: UUID) -> None:
        self.process_upload.execute(archive_volume_id)

    def process_cleanup_volume(self, archive_volume_id: UUID) -> None:
        self.process_cleanup.execute(archive_volume_id)

    def process_restore_volume(self, archive_volume_id: UUID) -> Path:
        return self.restore_volume.execute(archive_volume_id)


def _session_view(session: Session) -> SessionView:
    return SessionView(
        id=session.id,
        profile_name=session.profile_name,
        status=session.status.value,
    )


def _enqueue_result(item: SourceItem) -> EnqueueResult:
    return EnqueueResult(
        source_item_id=item.id,
        display_name=item.display_name,
        status=item.status.value,
    )
