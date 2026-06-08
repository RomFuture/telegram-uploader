from pathlib import Path

from infrastructure.facade import BackupFacade
from tests.fakes.ports import FakeArchiveService, FakeStorageProvider, FakeTaskQueue
from tests.fakes.repositories import InMemoryRepositories
from use_cases.backup.cleanup_volume import CleanupVolumeUseCase
from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.backup.process_archive_volume import ProcessArchiveVolumeUseCase
from use_cases.backup.process_upload_volume import ProcessUploadVolumeUseCase
from use_cases.backup.start_backup_pipeline import StartBackupPipelineUseCase
from use_cases.ports.archive_service import ArchiveVolumePart
from use_cases.restore.process_restore_volume import ProcessRestoreVolumeUseCase
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.session.create_session import CreateSessionUseCase


def _facade(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    *,
    archive_service: FakeArchiveService | None = None,
    tmp_path: Path | None = None,
) -> BackupFacade:
    cache_dir = (tmp_path or Path("/tmp")) / "cache"
    restore_dir = (tmp_path or Path("/tmp")) / "restore"
    storage = FakeStorageProvider()
    return BackupFacade(
        repos=repos,
        create_session=CreateSessionUseCase(repos.sessions),
        enqueue_source_item=EnqueueSourceItemUseCase(repos.source_items, task_queue),
        start_backup_pipeline=StartBackupPipelineUseCase(repos, task_queue),
        process_archive=ProcessArchiveVolumeUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            archive_service=archive_service or FakeArchiveService(),
            task_queue=task_queue,
            archive_cache_dir=cache_dir,
        ),
        process_upload=ProcessUploadVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            task_queue=task_queue,
            remote_target="-1001",
        ),
        process_cleanup=CleanupVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
        ),
        restore_volume=ProcessRestoreVolumeUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            staging_dir=restore_dir,
        ),
        restore_session=RestoreSessionUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            staging_dir=restore_dir,
        ),
    )


def test_start_session_returns_view_dto() -> None:
    repos = InMemoryRepositories()
    facade = _facade(repos, FakeTaskQueue())

    view = facade.start_session("default", "secret-key")

    assert view.profile_name == "default"
    assert view.status == "created"
    stored = repos.sessions.get(view.id)
    assert stored is not None
    assert stored.profile_name == "default"


def test_enqueue_file_returns_view_dto_not_domain_entity(
    tmp_path: Path,
) -> None:
    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    facade = _facade(repos, task_queue, tmp_path=tmp_path)
    session = facade.start_session("default", "secret-key")

    source_file = tmp_path / "real-name.bin"
    source_file.write_bytes(b"x")
    result = facade.enqueue_file(session.id, source_file, "User facing title")

    assert result.display_name == "User facing title"
    assert result.display_name != source_file.name
    assert result.status == "queued"
    assert task_queue.archive_ids == [result.source_item_id]


def test_get_session_progress_reads_display_name_from_db(
    tmp_path: Path,
) -> None:
    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    facade = _facade(repos, task_queue, tmp_path=tmp_path)
    session = facade.start_session("default", "secret-key")

    source_file = tmp_path / "ignored.bin"
    source_file.write_bytes(b"x")
    facade.enqueue_file(session.id, source_file, "Shown in UI")

    progress = facade.get_session_progress(session.id)

    assert len(progress.items) == 1
    assert progress.items[0].display_name == "Shown in UI"
    assert progress.items[0].display_name != source_file.name


def test_process_archive_volume_delegates_to_use_case(
    tmp_path: Path,
) -> None:
    repos = InMemoryRepositories()
    task_queue = FakeTaskQueue()
    part_one = tmp_path / "part001.7z"
    part_one.write_bytes(b"one")
    archive_service = FakeArchiveService(
        volumes=[ArchiveVolumePart(1, part_one, "hashed.7z.001")],
    )
    facade = _facade(repos, task_queue, archive_service=archive_service, tmp_path=tmp_path)
    session = facade.start_session("default", "secret-key")

    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    result = facade.enqueue_file(session.id, source_file, "Payload")

    facade.process_archive_volume(result.source_item_id)

    assert archive_service.last_display_name == "Payload"
    assert len(task_queue.upload_ids) == 1
