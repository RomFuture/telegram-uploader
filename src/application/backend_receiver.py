"""Translator between GUI and use_cases public API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from application.settings_values import SettingsValues
from use_cases.public import BackupApi
from use_cases.public.commands import (
    CreateDatabaseCommand,
    CreateFolderCommand,
    DeleteSourceItemCommand,
    EnqueueFileCommand,
    MoveSourceItemCommand,
    RenameSourceItemCommand,
    RestoreSessionCommand,
    UnlockSessionCommand,
)


@dataclass(frozen=True, slots=True)
class FolderViewDTO:
    folder_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class SessionViewDTO:
    session_id: UUID
    profile_name: str
    status: str
    generated_encryption_key: str | None = None


@dataclass(frozen=True, slots=True)
class QueueItemViewDTO:
    source_item_id: UUID
    display_name: str
    status: str
    folder_id: UUID | None = None
    folder_name: str | None = None
    size_label: str = "—"
    modified_label: str = "—"


@dataclass(frozen=True, slots=True)
class ProgressDTO:
    session_id: UUID
    items: tuple[QueueItemViewDTO, ...]


@dataclass(frozen=True, slots=True)
class RestoreResultDTO:
    session_id: UUID
    downloaded_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RestorePreflightDTO:
    ready: bool
    message: str


@dataclass(frozen=True, slots=True)
class TestClientApiResultDTO:
    ok: bool
    stage: str
    message: str


@dataclass(frozen=True, slots=True)
class BackendReceiver:
    api: BackupApi
    build_client_provider: Callable[..., object] | None = None

    def list_profiles(self) -> tuple[str, ...]:
        return self.api.list_profiles()

    def unlock_session(self, profile_name: str, encryption_key: str) -> SessionViewDTO:
        result = self.api.unlock_session(
            UnlockSessionCommand(profile_name=profile_name, encryption_key=encryption_key)
        )
        return SessionViewDTO(
            session_id=result.session_id,
            profile_name=result.profile_name,
            status=result.status,
        )

    def create_database(self, profile_name: str, encryption_key: str) -> SessionViewDTO:
        result = self.api.create_database(
            CreateDatabaseCommand(profile_name=profile_name, encryption_key=encryption_key)
        )
        return SessionViewDTO(
            session_id=result.session_id,
            profile_name=result.profile_name,
            status=result.status,
        )

    def list_folders(self, session_id: UUID) -> tuple[FolderViewDTO, ...]:
        return tuple(
            FolderViewDTO(folder_id=folder.folder_id, name=folder.name)
            for folder in self.api.list_folders(session_id)
        )

    def create_folder(self, session_id: UUID, name: str) -> FolderViewDTO:
        result = self.api.create_folder(CreateFolderCommand(session_id=session_id, name=name))
        return FolderViewDTO(folder_id=result.folder_id, name=result.name)

    def enqueue_file(
        self,
        session_id: UUID,
        source_path: Path,
        display_name: str,
        folder_id: UUID | None = None,
    ) -> QueueItemViewDTO:
        result = self.api.enqueue_file(
            EnqueueFileCommand(
                session_id=session_id,
                source_path=source_path,
                display_name=display_name,
                folder_id=folder_id,
            )
        )
        return QueueItemViewDTO(
            source_item_id=result.source_item_id,
            display_name=result.display_name,
            status=result.status,
        )

    def start_backup(self, session_id: UUID) -> int:
        return self.api.start_backup(session_id)

    def get_session_progress(self, session_id: UUID) -> ProgressDTO:
        progress = self.api.get_progress(session_id)
        return ProgressDTO(
            session_id=progress.session_id,
            items=tuple(
                QueueItemViewDTO(
                    source_item_id=item.source_item_id,
                    display_name=item.display_name,
                    status=item.status,
                    folder_id=item.folder_id,
                    folder_name=item.folder_name,
                    size_label=item.size_label,
                    modified_label=item.modified_label,
                )
                for item in progress.items
            ),
        )

    def request_restore(self, session_id: UUID, dest_path: Path) -> RestoreResultDTO:
        result = self.api.restore_session(
            RestoreSessionCommand(session_id=session_id, dest_path=dest_path)
        )
        return RestoreResultDTO(
            session_id=result.session_id,
            downloaded_paths=result.downloaded_paths,
        )

    def check_restore_ready(self, session_id: UUID) -> RestorePreflightDTO:
        result = self.api.check_restore_ready(session_id)
        return RestorePreflightDTO(ready=result.ready, message=result.message)

    def test_client_api(self, settings: SettingsValues) -> TestClientApiResultDTO:
        session_path = Path(settings.telegram_session_path)
        if not session_path.is_file():
            return TestClientApiResultDTO(
                ok=False,
                stage="session",
                message=(
                    f"Session file not found: {session_path}\n"
                    "Run scripts/telegram_client_spike.py --login-only first."
                ),
            )

        api_id = settings.telegram_api_id.strip()
        api_hash = settings.telegram_api_hash.strip()
        chat_id = settings.target_chat_id.strip()
        if not api_id.isdigit() or not api_hash:
            return TestClientApiResultDTO(
                ok=False,
                stage="config",
                message="API ID and API hash are required on the Client API tab.",
            )
        if not chat_id:
            return TestClientApiResultDTO(
                ok=False,
                stage="config",
                message="Target chat ID is required on the General tab.",
            )
        if self.build_client_provider is None:
            return TestClientApiResultDTO(
                ok=False,
                stage="config",
                message="Client API test is not configured.",
            )

        provider = self.build_client_provider(
            api_id=int(api_id),
            api_hash=api_hash,
            session_path=session_path,
        )
        result = self.api.test_client_api(provider, chat_id)
        return TestClientApiResultDTO(
            ok=result.ok,
            stage=result.stage,
            message=result.message,
        )

    def rename_source_item(self, source_item_id: UUID, display_name: str) -> None:
        self.api.rename_source_item(
            RenameSourceItemCommand(
                source_item_id=source_item_id,
                display_name=display_name,
            )
        )

    def move_source_item(self, source_item_id: UUID, folder_id: UUID) -> None:
        self.api.move_source_item(
            MoveSourceItemCommand(source_item_id=source_item_id, folder_id=folder_id)
        )

    def delete_source_item(self, source_item_id: UUID) -> None:
        self.api.delete_source_item(DeleteSourceItemCommand(source_item_id=source_item_id))
