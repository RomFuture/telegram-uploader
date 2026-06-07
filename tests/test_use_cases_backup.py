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
from use_cases.mappers import domain_to_session_record, source_item_record_to_domain
from use_cases.ports.archive_service import ArchiveVolumePart
from use_cases.session.create_session import CreateSessionUseCase


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
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret")
    source_file = tmp_path / "real-file-name.bin"
    source_file.write_bytes(b"x")

    item = EnqueueSourceItemUseCase(repos.source_items, task_queue).execute(
        session.id,
        source_file,
        "User facing title",
    )

    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.display_name == "User facing title"
    assert stored.display_name != source_file.name
    assert task_queue.archive_ids == [item.id]


def test_backup_happy_path_with_fakes(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret")
    running = domain.mark_session(session, status=domain.SessionStatus.RUNNING)
    repos.sessions.update(domain_to_session_record(running))

    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, task_queue).execute(
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
            remote_target="-1001",
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


def test_process_archive_raises_on_invalid_status(
    repos: InMemoryRepositories,
    task_queue: FakeTaskQueue,
    tmp_path: Path,
) -> None:
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret")
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"payload")
    item = EnqueueSourceItemUseCase(repos.source_items, task_queue).execute(
        session.id,
        source_file,
        "Payload",
    )

    item_record = repos.source_items.get(item.id)
    assert item_record is not None
    repos.source_items.update(
        replace(item_record, status=domain.SourceItemStatus.ARCHIVING.value),
    )

    with pytest.raises(domain.DomainError):
        ProcessArchiveVolumeUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            archive_service=FakeArchiveService(),
            task_queue=task_queue,
            archive_cache_dir=tmp_path / "cache",
        ).execute(item.id)
