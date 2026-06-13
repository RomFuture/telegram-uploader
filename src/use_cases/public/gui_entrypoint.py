"""Entry point for GUI adapter: commands in, results out."""

from dataclasses import dataclass
from uuid import UUID

from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.backup.start_backup_pipeline import StartBackupPipelineUseCase
from use_cases.public.commands import (
    CreateDatabaseCommand,
    CreateFolderCommand,
    DeleteSourceItemCommand,
    EnqueueFileCommand,
    MoveSourceItemCommand,
    RenameSourceItemCommand,
    RestoreSessionCommand,
    StartSessionCommand,
    UnlockSessionCommand,
)
from use_cases.public.results import (
    FolderResult,
    QueueItemResult,
    QueueItemSnapshotResult,
    RestoreResult,
    SessionQueueSnapshotResult,
    SessionResult,
)
from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase, RestoreReadyResult
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.session.create import (
    CreateDatabaseUseCase,
    CreateFolderUseCase,
    CreateSessionUseCase,
)
from use_cases.session.get_session_queue_snapshot import GetSessionQueueSnapshotUseCase
from use_cases.session.list import ListFoldersUseCase, ListSessionProfilesUseCase
from use_cases.session.manage_source_item import (
    DeleteSourceItemUseCase,
    MoveSourceItemUseCase,
    RenameSourceItemUseCase,
)
from use_cases.session.unlock_session import UnlockSessionUseCase
from use_cases.telegram.verify_storage_provider import (
    VerifyStorageProviderResult,
    VerifyStorageProviderUseCase,
)


def _session_result(
    session: object,
    *,
    generated_encryption_key: str | None = None,
) -> SessionResult:
    from use_cases.shared.types import Session

    assert isinstance(session, Session)
    return SessionResult(
        session_id=session.id,
        profile_name=session.profile_name,
        status=session.status.value,
        generated_encryption_key=generated_encryption_key,
    )


@dataclass(frozen=True, slots=True)
class GuiEntrypoint:
    create_session: CreateSessionUseCase
    create_database_uc: CreateDatabaseUseCase
    unlock_session_uc: UnlockSessionUseCase
    list_session_profiles: ListSessionProfilesUseCase
    list_folders_uc: ListFoldersUseCase
    create_folder_uc: CreateFolderUseCase
    get_session_queue_snapshot: GetSessionQueueSnapshotUseCase
    enqueue_source_item: EnqueueSourceItemUseCase
    start_backup_pipeline: StartBackupPipelineUseCase
    restore_session_uc: RestoreSessionUseCase
    check_restore_ready_uc: CheckRestoreReadyUseCase
    verify_storage_provider_uc: VerifyStorageProviderUseCase
    rename_source_item_uc: RenameSourceItemUseCase
    move_source_item_uc: MoveSourceItemUseCase
    delete_source_item_uc: DeleteSourceItemUseCase

    def start_session(self, command: StartSessionCommand) -> SessionResult:
        outcome = self.create_session.execute(command.profile_name, command.encryption_key)
        return _session_result(
            outcome.session,
            generated_encryption_key=outcome.generated_encryption_key,
        )

    def unlock_session(self, command: UnlockSessionCommand) -> SessionResult:
        session = self.unlock_session_uc.execute(command.profile_name, command.encryption_key)
        return _session_result(session)

    def create_database(self, command: CreateDatabaseCommand) -> SessionResult:
        session = self.create_database_uc.execute(command.profile_name, command.encryption_key)
        return _session_result(session)

    def list_profiles(self) -> tuple[str, ...]:
        return self.list_session_profiles.execute()

    def list_folders(self, session_id: UUID) -> tuple[FolderResult, ...]:
        folders = self.list_folders_uc.execute(session_id)
        return tuple(FolderResult(folder_id=folder.id, name=folder.name) for folder in folders)

    def create_folder(self, command: CreateFolderCommand) -> FolderResult:
        folder = self.create_folder_uc.execute(command.session_id, command.name)
        return FolderResult(folder_id=folder.id, name=folder.name)

    def enqueue_file(self, command: EnqueueFileCommand) -> QueueItemResult:
        item = self.enqueue_source_item.execute(
            command.session_id,
            command.source_path,
            command.display_name,
            command.folder_id,
        )
        return QueueItemResult(
            source_item_id=item.id,
            display_name=item.display_name,
            status=item.status.value,
        )

    def start_backup(self, session_id: UUID) -> int:
        return self.start_backup_pipeline.execute(session_id)

    def get_queue_snapshot(self, session_id: UUID) -> SessionQueueSnapshotResult:
        snapshot = self.get_session_queue_snapshot.execute(session_id)
        return SessionQueueSnapshotResult(
            session_id=snapshot.session_id,
            items=tuple(
                QueueItemSnapshotResult(
                    source_item_id=item.source_item_id,
                    display_name=item.display_name,
                    status=item.status,
                    folder_id=item.folder_id,
                    folder_name=item.folder_name,
                    size_label=item.size_label,
                    modified_label=item.modified_label,
                )
                for item in snapshot.items
            ),
        )

    def restore_session(self, command: RestoreSessionCommand) -> RestoreResult:
        paths = self.restore_session_uc.execute(
            command.session_id,
            command.dest_path,
            folder_id=command.folder_id,
        )
        return RestoreResult(
            session_id=command.session_id,
            downloaded_paths=tuple(str(path) for path in paths),
        )

    def check_restore_ready(
        self,
        session_id: UUID,
        *,
        folder_id: UUID | None = None,
    ) -> RestoreReadyResult:
        return self.check_restore_ready_uc.execute(session_id, folder_id=folder_id)

    def verify_storage_provider(
        self,
        provider: object,
        target_chat_id: str,
    ) -> VerifyStorageProviderResult:
        from use_cases.shared.ports.storage_provider import StorageProviderPort

        assert isinstance(provider, StorageProviderPort)
        return self.verify_storage_provider_uc.execute(provider, target_chat_id)

    def rename_source_item(self, command: RenameSourceItemCommand) -> None:
        self.rename_source_item_uc.execute(command.source_item_id, command.display_name)

    def move_source_item(self, command: MoveSourceItemCommand) -> None:
        self.move_source_item_uc.execute(command.source_item_id, command.folder_id)

    def delete_source_item(self, command: DeleteSourceItemCommand) -> None:
        self.delete_source_item_uc.execute(command.source_item_id)
