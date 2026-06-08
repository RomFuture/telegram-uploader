"""Translator between GUI and infrastructure facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from infrastructure.facade import BackupFacade


@dataclass(frozen=True, slots=True)
class SessionViewDTO:
    session_id: UUID
    profile_name: str
    status: str


@dataclass(frozen=True, slots=True)
class QueueItemViewDTO:
    source_item_id: UUID
    display_name: str
    status: str


@dataclass(frozen=True, slots=True)
class ProgressDTO:
    session_id: UUID
    items: tuple[QueueItemViewDTO, ...]


@dataclass(frozen=True, slots=True)
class RestoreResultDTO:
    session_id: UUID
    downloaded_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BackendReceiver:
    facade: BackupFacade

    def start_session(self, profile_name: str, encryption_key: str) -> SessionViewDTO:
        view = self.facade.start_session(profile_name, encryption_key)
        return SessionViewDTO(
            session_id=view.id,
            profile_name=view.profile_name,
            status=view.status,
        )

    def enqueue_file(
        self,
        session_id: UUID,
        source_path: Path,
        display_name: str,
    ) -> QueueItemViewDTO:
        result = self.facade.enqueue_file(session_id, source_path, display_name)
        return QueueItemViewDTO(
            source_item_id=result.source_item_id,
            display_name=result.display_name,
            status=result.status,
        )

    def start_backup(self, session_id: UUID) -> int:
        return self.facade.start_backup(session_id)

    def get_session_progress(self, session_id: UUID) -> ProgressDTO:
        progress = self.facade.get_session_progress(session_id)
        return ProgressDTO(
            session_id=progress.session_id,
            items=tuple(
                QueueItemViewDTO(
                    source_item_id=item.source_item_id,
                    display_name=item.display_name,
                    status=item.status,
                )
                for item in progress.items
            ),
        )

    def request_restore(self, session_id: UUID, dest_path: Path) -> RestoreResultDTO:
        paths = self.facade.request_restore(session_id, dest_path)
        return RestoreResultDTO(
            session_id=session_id,
            downloaded_paths=tuple(str(path) for path in paths),
        )
