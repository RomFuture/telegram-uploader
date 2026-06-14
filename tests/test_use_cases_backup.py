from dataclasses import replace
from pathlib import Path

import pytest

import domain as domain
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
from use_cases.session.create import CreateSessionUseCase
from use_cases.shared.mappers import (
    domain_to_archive_volume_record,
    domain_to_session_record,
    source_item_record_to_domain,
)
from use_cases.shared.ports.archive_service import ArchiveVolumePart


@pytest.fixture
def repos() -> InMemoryRepositories:
    return InMemoryRepositories()


@pytest.fixture
def task_queue() -> FakeTaskQueue:
    return FakeTaskQueue()


def test_enqueue_persists_display_name_not_path_name(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "real-file-name.bin"
    source_file.write_bytes(b"x")

    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "User facing title",
    )

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.display_name == "User facing title"
    assert stored.display_name != source_file.name
    assert task_queue.archive_ids == []


def test_start_backup_enqueues_queued_items(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "file.bin"
    source_file.write_bytes(b"x")

    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Title",
    )
    assert task_queue.archive_ids == []

    enqueued = StartBackupPipelineUseCase(repos, task_queue).execute(session.id)
    assert enqueued == 1
    assert task_queue.archive_ids == [item.id]


def test_backup_happy_path_with_fakes(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    running = domain.mark_session(session, status=domain.SessionStatus.RUNNING)
    repos.sessions.update(domain_to_session_record(running))

    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        running.id,
        source_file,
        "Payload",
    )

    part_one = tmp_path / "part001.7z"
    part_two = tmp_path / "part002.7z"
    part_one.write_bytes(b"one")
    part_two.write_bytes(b"two")
    archive_service = FakeArchiveService(
        volumes=[
            ArchiveVolumePart(1, part_one, "hashed.7z.001"),
            ArchiveVolumePart(2, part_two, "hashed.7z.002"),
        ]
    )

    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=archive_service,
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    assert archive_service.last_display_name == "Payload"
    assert len(task_queue.upload_ids) == 2

    storage = FakeStorageProvider()
    for volume_id in task_queue.upload_ids:
        ProcessUploadVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            storage_provider=storage,
            task_queue=task_queue,
        ).execute(volume_id)

    assert len(task_queue.cleanup_ids) == 2
    uploaded = repos.archive_volumes.get(task_queue.upload_ids[0])
    assert uploaded is not None
    assert uploaded.external_file_id is not None
    assert uploaded.provider_download_ref is not None

    for volume_id in task_queue.cleanup_ids:
        CleanupVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
        ).execute(volume_id)

    final_item = repos.source_items.get(item.id)
    assert final_item is not None
    assert domain.is_source_item(
        source_item_record_to_domain(final_item),
        status=domain.SourceItemStatus.COMPLETED,
    )


def test_start_backup_pipeline_transitions_created_to_running(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "queued.bin"
    source_file.write_bytes(b"q")
    EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Queued item",
    )
    task_queue.archive_ids.clear()

    enqueued = StartBackupPipelineUseCase(repos, task_queue).execute(session.id)

    assert enqueued == 1
    stored = repos.sessions.get(session.id)
    assert stored is not None
    assert stored.status == domain.SessionStatus.RUNNING.value


def test_start_backup_pipeline_enqueues_only_queued_items(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    running = domain.mark_session(session, status=domain.SessionStatus.RUNNING)
    repos.sessions.update(domain_to_session_record(running))

    queued_file = tmp_path / "queued.bin"
    queued_file.write_bytes(b"q")
    queued_item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        running.id,
        queued_file,
        "Queued item",
    )

    completed_file = tmp_path / "done.bin"
    completed_file.write_bytes(b"d")
    completed_item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        running.id,
        completed_file,
        "Done item",
    )
    completed_record = repos.source_items.get(completed_item.id)
    assert completed_record is not None
    repos.source_items.update(
        replace(completed_record, status=domain.SourceItemStatus.COMPLETED.value),
    )

    task_queue.archive_ids.clear()
    enqueued = StartBackupPipelineUseCase(repos, task_queue).execute(running.id)

    assert enqueued == 1
    assert task_queue.archive_ids == [queued_item.id]


def test_start_backup_resumes_stuck_uploading_items(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from use_cases.shared.persistence import ArchiveVolumeRecord, SourceItemRecord

    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    running = domain.mark_session(session, status=domain.SessionStatus.RUNNING)
    repos.sessions.update(domain_to_session_record(running))

    source_item_id = uuid4()
    created_at = datetime.now(tz=UTC)
    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=running.id,
            source_path=str(tmp_path / "stale.bin"),
            display_name="stale.bin",
            status=domain.SourceItemStatus.UPLOADING.value,
            created_at=created_at,
        )
    )
    volume_id = uuid4()
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=volume_id,
            source_item_id=source_item_id,
            file_name="stale.7z.001",
            local_path=str(tmp_path / "stale.7z.001"),
            part_number=1,
            status=domain.ArchiveVolumeStatus.CREATED.value,
            external_file_id=None,
            external_message_id=None,
            provider_download_ref=None,
            created_at=created_at,
        )
    )

    enqueued = StartBackupPipelineUseCase(repos, task_queue).execute(running.id)

    assert enqueued == 1
    assert task_queue.upload_ids == [volume_id]


def test_report_archive_failure_marks_source_item_failed(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    ReportArchiveFailureUseCase(repos.source_items).execute(item.id)

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.status == domain.SourceItemStatus.FAILED.value


def test_report_upload_failure_marks_volume_and_uploading_item_failed(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(
            volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")],
        ),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    volume_id = task_queue.upload_ids[0]
    ReportUploadFailureUseCase(repos.source_items, repos.archive_volumes).execute(volume_id)

    volume = repos.archive_volumes.get(volume_id)
    assert volume is not None
    assert volume.status == domain.ArchiveVolumeStatus.FAILED.value

    stored_item = repos.source_items.get(item.id)
    assert stored_item is not None
    assert stored_item.status == domain.SourceItemStatus.FAILED.value


def test_retry_upload_skips_when_volume_already_uploaded(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")]),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    storage = FakeStorageProvider()
    volume_id = task_queue.upload_ids[0]
    upload_uc = ProcessUploadVolumeUseCase(
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        task_queue=task_queue,
    )
    upload_uc.execute(volume_id)
    task_queue.cleanup_ids.clear()
    upload_uc.execute(volume_id)

    assert len(storage.uploaded_display_names) == 1
    assert volume_id in task_queue.cleanup_ids


def test_retry_archive_skips_when_item_already_uploading(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    archive_service = FakeArchiveService(volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")])
    archive_uc = ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=archive_service,
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    )
    archive_uc.execute(item.id)
    archive_uc.execute(item.id)

    assert archive_service.archive_calls == 1


def test_retry_upload_continues_from_uploading_status(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")]),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    volume_id = task_queue.upload_ids[0]
    volume = repos.archive_volumes.require(volume_id)
    uploading = domain.mark_archive_volume(volume, status=domain.ArchiveVolumeStatus.UPLOADING)
    repos.archive_volumes.update(domain_to_archive_volume_record(uploading))

    storage = FakeStorageProvider()
    ProcessUploadVolumeUseCase(
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        task_queue=task_queue,
    ).execute(volume_id)

    stored = repos.archive_volumes.get(volume_id)
    assert stored is not None
    assert stored.status == domain.ArchiveVolumeStatus.UPLOADED.value


def test_retry_cleanup_skips_when_item_already_completed(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")]),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    storage = FakeStorageProvider()
    volume_id = task_queue.upload_ids[0]
    ProcessUploadVolumeUseCase(
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        task_queue=task_queue,
    ).execute(volume_id)

    cleanup_uc = CleanupVolumeUseCase(repos.source_items, repos.archive_volumes)
    cleanup_uc.execute(volume_id)
    cleanup_uc.execute(volume_id)

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.status == domain.SourceItemStatus.COMPLETED.value


def test_report_upload_failure_is_idempotent(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")]),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    volume_id = task_queue.upload_ids[0]
    report_uc = ReportUploadFailureUseCase(repos.source_items, repos.archive_volumes)
    report_uc.execute(volume_id)
    report_uc.execute(volume_id)

    volume = repos.archive_volumes.get(volume_id)
    assert volume is not None
    assert volume.status == domain.ArchiveVolumeStatus.FAILED.value


def test_report_cleanup_failure_marks_cleanup_item_failed(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    part = tmp_path / "part001.7z"
    part.write_bytes(b"one")
    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(volumes=[ArchiveVolumePart(1, part, "hashed.7z.001")]),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    ProcessUploadVolumeUseCase(
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        storage_provider=FakeStorageProvider(),
        task_queue=task_queue,
    ).execute(task_queue.upload_ids[0])

    ReportCleanupFailureUseCase(repos.source_items).execute(item.id)

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.status == domain.SourceItemStatus.FAILED.value


def test_process_archive_retries_orphaned_archiving_without_volumes(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )

    item_record = repos.source_items.get(item.id)
    assert item_record is not None
    repos.source_items.update(
        replace(item_record, status=domain.SourceItemStatus.ARCHIVING.value),
    )

    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(
            volumes=[ArchiveVolumePart(1, tmp_path / "part.7z.001", "part.7z.001")],
        ),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.status == domain.SourceItemStatus.UPLOADING.value
    assert task_queue.upload_ids


def test_require_item_archivable_rejects_non_queued_without_orphan(
    repos: InMemoryRepositories,
    tmp_path: Path,
) -> None:
    from use_cases.backup.gates import require_item_archivable

    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
    )
    uploading = domain.mark_source_item(item, status=domain.SourceItemStatus.UPLOADING)

    with pytest.raises(domain.DomainError):
        require_item_archivable(uploading, has_volumes=False)


def test_process_archive_preserves_folder_id_on_status_update(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from use_cases.shared.folders import DEFAULT_FOLDER_NAME
    from use_cases.shared.persistence import BackupFolderRecord

    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    folder_id = uuid4()
    repos.folders.add(
        BackupFolderRecord(
            id=folder_id,
            session_id=session.id,
            name=DEFAULT_FOLDER_NAME,
            created_at=datetime.now(tz=UTC),
        )
    )
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Payload",
        folder_id=folder_id,
    )

    ProcessArchiveVolumeUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        archive_volumes=repos.archive_volumes,
        archive_service=FakeArchiveService(
            volumes=[ArchiveVolumePart(1, tmp_path / "part.7z.001", "part.7z.001")],
        ),
        task_queue=task_queue,
        archive_cache_dir=tmp_path / "cache",
    ).execute(item.id)

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.folder_id == folder_id
    assert stored.status == domain.SourceItemStatus.UPLOADING.value
