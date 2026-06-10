from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

import domain as domain
from tests.fakes.ports import FakeStorageProvider
from tests.fakes.repositories import InMemoryRepositories
from use_cases.persistence import ArchiveVolumeRecord, SourceItemRecord
from use_cases.restore.restore_session import RestoreSessionUseCase


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_restore_downloads_volumes_in_part_order(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session_id = uuid4()
    source_item_id = uuid4()
    created_at = _now()

    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session_id,
            source_path="/tmp/source.bin",
            display_name="source.bin",
            status="completed",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name="vol.7z.002",
            local_path="/tmp/vol.7z.002",
            part_number=2,
            status="uploaded",
            external_file_id="file-2",
            external_message_id="msg-2",
            provider_download_ref="ref-2",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name="vol.7z.001",
            local_path="/tmp/vol.7z.001",
            part_number=1,
            status="uploaded",
            external_file_id="file-1",
            external_message_id="msg-1",
            provider_download_ref="ref-1",
            created_at=created_at,
        )
    )

    storage = FakeStorageProvider()
    downloaded = RestoreSessionUseCase(
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        staging_dir=tmp_path / "staging",
    ).execute(session_id, tmp_path / "restored")

    assert [path.name for path in downloaded] == ["vol.7z.001", "vol.7z.002"]
    assert len(storage.downloaded_files) == 2


def test_restore_raises_when_volume_missing_external_file_id(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session_id = uuid4()
    source_item_id = uuid4()
    created_at = _now()

    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session_id,
            source_path="/tmp/source.bin",
            display_name="source.bin",
            status="completed",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name="vol.7z.001",
            local_path="/tmp/vol.7z.001",
            part_number=1,
            status="uploaded",
            external_file_id=None,
            external_message_id=None,
            provider_download_ref=None,
            created_at=created_at,
        )
    )

    with pytest.raises(domain.DomainError):
        RestoreSessionUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=FakeStorageProvider(),
            staging_dir=tmp_path / "staging",
        ).execute(session_id, tmp_path / "restored")


def test_restore_prefers_provider_download_ref(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session_id = uuid4()
    source_item_id = uuid4()
    created_at = _now()

    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session_id,
            source_path="/tmp/source.bin",
            display_name="source.bin",
            status="completed",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name="vol.7z.001",
            local_path="/tmp/vol.7z.001",
            part_number=1,
            status="uploaded",
            external_file_id="legacy-file-id",
            external_message_id="msg-1",
            provider_download_ref="client:-1001:42:9001",
            created_at=created_at,
        )
    )

    storage = FakeStorageProvider()
    RestoreSessionUseCase(
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        staging_dir=tmp_path / "staging",
    ).execute(session_id, tmp_path / "restored")

    assert storage.requested_refs == ["client:-1001:42:9001"]


def test_restore_raises_when_no_volumes(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    with pytest.raises(domain.DomainError):
        RestoreSessionUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=FakeStorageProvider(),
            staging_dir=tmp_path / "staging",
        ).execute(uuid4(), tmp_path / "restored")
