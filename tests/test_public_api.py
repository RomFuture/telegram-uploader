from pathlib import Path

from tests.fakes.ports import FakeArchiveService, FakeStorageProvider, FakeTaskQueue
from tests.fakes.repositories import InMemoryRepositories
from use_cases.backup.cleanup_volume import CleanupVolumeUseCase
from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.backup.process_archive_volume import ProcessArchiveVolumeUseCase
from use_cases.backup.process_upload_volume import ProcessUploadVolumeUseCase
from use_cases.backup.report_failure import (
    ReportArchiveFailureUseCase,
    ReportCleanupFailureUseCase,
    ReportUploadFailureUseCase,
)
from use_cases.backup.start_backup_pipeline import StartBackupPipelineUseCase
from use_cases.public import (
    CeleryEntrypoint,
    EnqueueFileCommand,
    GuiEntrypoint,
    StartSessionCommand,
)
from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase
from use_cases.restore.process_restore_volume import ProcessRestoreVolumeUseCase
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
from use_cases.telegram.verify_storage_provider import VerifyStorageProviderUseCase

_SECRET_SESSION = StartSessionCommand(profile_name="default", encryption_key="secret")


def _gui_entrypoint(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    *,
    tmp_path: Path | None = None,
) -> GuiEntrypoint:
    restore_dir = (tmp_path or Path("/tmp")) / "restore"
    storage = FakeStorageProvider()
    archive_service = FakeArchiveService()
    return GuiEntrypoint(
        create_session=CreateSessionUseCase(repos.sessions),
        create_database_uc=CreateDatabaseUseCase(repos.sessions, repos.folders),
        unlock_session_uc=UnlockSessionUseCase(repos.sessions),
        list_session_profiles=ListSessionProfilesUseCase(repos.sessions),
        list_folders_uc=ListFoldersUseCase(repos.folders),
        create_folder_uc=CreateFolderUseCase(repos.folders),
        get_session_queue_snapshot=GetSessionQueueSnapshotUseCase(
            repos.source_items, repos.folders
        ),
        enqueue_source_item=EnqueueSourceItemUseCase(repos.source_items, repos.folders),
        start_backup_pipeline=StartBackupPipelineUseCase(repos, task_queue),
        restore_session_uc=RestoreSessionUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            folders=repos.folders,
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            archive_service=archive_service,
            staging_dir=restore_dir,
        ),
        check_restore_ready_uc=CheckRestoreReadyUseCase(
            archive_volumes=repos.archive_volumes,
            source_items=repos.source_items,
            folders=repos.folders,
            storage_provider=storage,
        ),
        verify_storage_provider_uc=VerifyStorageProviderUseCase(
            test_file_path=Path(__file__).resolve().parents[1]
            / "src/infrastructure/data/client_api_test.md",
        ),
        rename_source_item_uc=RenameSourceItemUseCase(repos.source_items),
        move_source_item_uc=MoveSourceItemUseCase(repos.source_items, repos.folders),
        delete_source_item_uc=DeleteSourceItemUseCase(
            repos.source_items,
            repos.archive_volumes,
        ),
    )


def _celery_entrypoint(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    *,
    archive_service: FakeArchiveService | None = None,
    tmp_path: Path | None = None,
) -> CeleryEntrypoint:
    cache_dir = (tmp_path or Path("/tmp")) / "cache"
    restore_dir = (tmp_path or Path("/tmp")) / "restore"
    storage = FakeStorageProvider()
    return CeleryEntrypoint(
        process_archive_uc=ProcessArchiveVolumeUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            archive_service=archive_service or FakeArchiveService(),
            task_queue=task_queue,
            archive_cache_dir=cache_dir,
        ),
        process_upload_uc=ProcessUploadVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            task_queue=task_queue,
        ),
        process_cleanup_uc=CleanupVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
        ),
        process_restore_volume_uc=ProcessRestoreVolumeUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            staging_dir=restore_dir,
        ),
        report_archive_failure_uc=ReportArchiveFailureUseCase(repos.source_items),
        report_upload_failure_uc=ReportUploadFailureUseCase(
            repos.source_items,
            repos.archive_volumes,
        ),
        report_cleanup_failure_uc=ReportCleanupFailureUseCase(repos.source_items),
    )


def test_start_session_returns_result_without_domain_entity() -> None:
    repos = InMemoryRepositories()
    api = _gui_entrypoint(repos, FakeTaskQueue())

    result = api.start_session(StartSessionCommand(profile_name="default", encryption_key="secret"))

    assert result.profile_name == "default"
    assert result.status == "created"
    assert result.generated_encryption_key is None
    stored = repos.sessions.get(result.session_id)
    assert stored is not None


def test_start_session_auto_generates_encryption_key() -> None:
    repos = InMemoryRepositories()
    api = _gui_entrypoint(repos, FakeTaskQueue())

    result = api.start_session(StartSessionCommand(profile_name="default"))

    assert result.generated_encryption_key is not None
    stored = repos.sessions.get(result.session_id)
    assert stored is not None
    assert stored.encryption_key == result.generated_encryption_key


def test_enqueue_file_returns_queue_item_result(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    api = _gui_entrypoint(repos, task_queue, tmp_path=tmp_path)
    session = api.start_session(_SECRET_SESSION)

    source_file = tmp_path / "real-name.bin"
    source_file.write_bytes(b"x")
    result = api.enqueue_file(
        EnqueueFileCommand(
            session_id=session.session_id,
            source_path=source_file,
            display_name="User facing title",
        )
    )

    assert result.display_name == "User facing title"
    assert result.status == "queued"
    assert task_queue.archive_ids == []


def test_get_queue_snapshot_reads_display_name(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    api = _gui_entrypoint(repos, task_queue, tmp_path=tmp_path)
    session = api.start_session(_SECRET_SESSION)

    source_file = tmp_path / "ignored.bin"
    source_file.write_bytes(b"x")
    api.enqueue_file(
        EnqueueFileCommand(
            session_id=session.session_id,
            source_path=source_file,
            display_name="Shown in UI",
        )
    )

    snapshot = api.get_queue_snapshot(session.session_id)

    assert len(snapshot.items) == 1
    assert snapshot.items[0].display_name == "Shown in UI"


def test_celery_entrypoint_process_archive_delegates(tmp_path: Path) -> None:
    from use_cases.shared.ports.archive_service import ArchiveVolumePart

    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    backup = _gui_entrypoint(repos, task_queue, tmp_path=tmp_path)
    part_one = tmp_path / "part001.7z"
    part_one.write_bytes(b"one")
    worker = _celery_entrypoint(
        repos,
        task_queue,
        archive_service=FakeArchiveService(
            volumes=[ArchiveVolumePart(1, part_one, "hashed.7z.001")],
        ),
        tmp_path=tmp_path,
    )
    session = backup.start_session(_SECRET_SESSION)
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = backup.enqueue_file(
        EnqueueFileCommand(
            session_id=session.session_id,
            source_path=source_file,
            display_name="Payload",
        )
    )

    worker.process_archive(item.source_item_id)

    assert len(task_queue.upload_ids) == 1


def test_celery_entrypoint_report_failures_delegate() -> None:
    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    worker = _celery_entrypoint(repos, task_queue)
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase

    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        Path("/tmp/source.bin"),
        "file",
    )

    worker.report_archive_failure(item.id)
    updated = repos.source_items.require(item.id)
    assert updated.status.value == "failed"
