from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

import domain as domain
from tests.fakes.ports import FakeArchiveService, FakeStorageProvider
from tests.fakes.repositories import InMemoryRepositories
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.session.create_session import CreateSessionUseCase
from use_cases.shared.persistence import ArchiveVolumeRecord, SourceItemRecord


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_restore_downloads_volumes_in_part_order_and_extracts_to_dest(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    session_id = session.id
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
            provider_download_ref="client:-1001:2:9002",
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
            provider_download_ref="client:-1001:1:9001",
            created_at=created_at,
        )
    )

    storage = FakeStorageProvider()
    dest_path = tmp_path / "restored"
    restored = RestoreSessionUseCase(
        sessions=repos.sessions,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        archive_service=FakeArchiveService(),
        staging_dir=tmp_path / "staging",
        target_chat_id="-1001",
    ).execute(session_id, dest_path)

    assert len(storage.downloaded_files) == 2
    assert len(restored) == 1
    assert restored[0].parent == dest_path
    assert restored[0].name == "restored.bin"
    assert restored[0].read_bytes() == b"restored-content"


def test_restore_raises_when_volume_missing_external_file_id(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    session_id = session.id
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

    with pytest.raises(domain.DomainError) as error:
        RestoreSessionUseCase(
            sessions=repos.sessions,
            archive_volumes=repos.archive_volumes,
            storage_provider=FakeStorageProvider(),
            archive_service=FakeArchiveService(),
            staging_dir=tmp_path / "staging",
            target_chat_id="-1001",
        ).execute(session_id, tmp_path / "restored")

    assert error.value.reason == "no_restorable_backups"


def test_restore_prefers_provider_download_ref(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    session_id = session.id
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
        sessions=repos.sessions,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        archive_service=FakeArchiveService(),
        staging_dir=tmp_path / "staging",
        target_chat_id="-1001",
    ).execute(session_id, tmp_path / "restored")

    assert storage.requested_refs == ["client:-1001:42:9001"]


def test_restore_rejects_legacy_bot_api_refs(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    session_id = session.id
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
            external_file_id="bot-file-id",
            external_message_id="msg-1",
            provider_download_ref="bot-unique-id",
            created_at=created_at,
        )
    )

    with pytest.raises(domain.DomainError) as exc_info:
        RestoreSessionUseCase(
            sessions=repos.sessions,
            archive_volumes=repos.archive_volumes,
            storage_provider=FakeStorageProvider(),
            archive_service=FakeArchiveService(),
            staging_dir=tmp_path / "staging",
            target_chat_id="-1001",
        ).execute(session_id, tmp_path / "restored")

    assert exc_info.value.code == "legacy_volumes"


def test_check_restore_ready_reports_legacy_volumes(tmp_path: Path) -> None:
    from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase

    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_item_id = uuid4()
    created_at = _now()
    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session.id,
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
            external_file_id="bot-file-id",
            external_message_id="msg-1",
            provider_download_ref="bot-unique-id",
            created_at=created_at,
        )
    )

    result = CheckRestoreReadyUseCase(
        archive_volumes=repos.archive_volumes,
        storage_provider=FakeStorageProvider(),
        target_chat_id="-1001",
    ).execute(session.id)

    assert result.ready is False
    assert "Re-backup required" in result.message


def test_check_restore_ready_ok_for_client_refs(tmp_path: Path) -> None:
    from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase

    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_item_id = uuid4()
    created_at = _now()
    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session.id,
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
            external_file_id="1",
            external_message_id="42",
            provider_download_ref="client:-1001:42:9001",
            created_at=created_at,
        )
    )

    result = CheckRestoreReadyUseCase(
        archive_volumes=repos.archive_volumes,
        storage_provider=FakeStorageProvider(),
        target_chat_id="-1001",
    ).execute(session.id)

    assert result.ready is True


def test_check_restore_ready_reports_incomplete_upload(tmp_path: Path) -> None:
    from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase

    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_item_id = uuid4()
    created_at = _now()
    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session.id,
            source_path="/tmp/source.bin",
            display_name="source.bin",
            status="uploading",
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
            status="created",
            external_file_id=None,
            external_message_id=None,
            provider_download_ref=None,
            created_at=created_at,
        )
    )

    result = CheckRestoreReadyUseCase(
        archive_volumes=repos.archive_volumes,
        storage_provider=FakeStorageProvider(),
        target_chat_id="-1001",
    ).execute(session.id)

    assert result.ready is False
    assert "did not finish uploading" in result.message
    assert "Start Backup to retry" in result.message


def test_restore_raises_when_no_volumes(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    with pytest.raises(domain.DomainError):
        RestoreSessionUseCase(
            sessions=repos.sessions,
            archive_volumes=repos.archive_volumes,
            storage_provider=FakeStorageProvider(),
            archive_service=FakeArchiveService(),
            staging_dir=tmp_path / "staging",
            target_chat_id="-1001",
        ).execute(uuid4(), tmp_path / "restored")


def test_check_restore_ready_ok_when_some_items_restorable(tmp_path: Path) -> None:
    from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase

    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    created_at = _now()

    complete_item_id = uuid4()
    repos.source_items.add(
        SourceItemRecord(
            id=complete_item_id,
            session_id=session.id,
            source_path="/tmp/complete.bin",
            display_name="complete.bin",
            status="completed",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=complete_item_id,
            file_name="complete.7z.001",
            local_path="/tmp/complete.7z.001",
            part_number=1,
            status="uploaded",
            external_file_id="1",
            external_message_id="42",
            provider_download_ref="client:-1001:42:9001",
            created_at=created_at,
        )
    )

    stale_item_id = uuid4()
    repos.source_items.add(
        SourceItemRecord(
            id=stale_item_id,
            session_id=session.id,
            source_path="/tmp/stale.bin",
            display_name="stale.bin",
            status="uploading",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=stale_item_id,
            file_name="stale.7z.001",
            local_path="/tmp/stale.7z.001",
            part_number=1,
            status="created",
            external_file_id=None,
            external_message_id=None,
            provider_download_ref=None,
            created_at=created_at,
        )
    )

    result = CheckRestoreReadyUseCase(
        archive_volumes=repos.archive_volumes,
        storage_provider=FakeStorageProvider(),
        target_chat_id="-1001",
    ).execute(session.id)

    assert result.ready is True
    assert "Ready to restore 1 file(s)" in result.message
    assert "Start Backup to retry" in result.message


def test_restore_skips_incomplete_items_when_some_are_restorable(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    created_at = _now()

    complete_item_id = uuid4()
    repos.source_items.add(
        SourceItemRecord(
            id=complete_item_id,
            session_id=session.id,
            source_path="/tmp/complete.bin",
            display_name="complete.bin",
            status="completed",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=complete_item_id,
            file_name="complete.7z.001",
            local_path="/tmp/complete.7z.001",
            part_number=1,
            status="uploaded",
            external_file_id="1",
            external_message_id="42",
            provider_download_ref="client:-1001:42:9001",
            created_at=created_at,
        )
    )

    stale_item_id = uuid4()
    repos.source_items.add(
        SourceItemRecord(
            id=stale_item_id,
            session_id=session.id,
            source_path="/tmp/stale.bin",
            display_name="stale.bin",
            status="uploading",
            created_at=created_at,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=stale_item_id,
            file_name="stale.7z.001",
            local_path="/tmp/stale.7z.001",
            part_number=1,
            status="created",
            external_file_id=None,
            external_message_id=None,
            provider_download_ref=None,
            created_at=created_at,
        )
    )

    storage = FakeStorageProvider()
    restored = RestoreSessionUseCase(
        sessions=repos.sessions,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        archive_service=FakeArchiveService(),
        staging_dir=tmp_path / "staging",
        target_chat_id="-1001",
    ).execute(session.id, tmp_path / "restored")

    assert len(storage.downloaded_files) == 1
    assert len(restored) == 1


def test_restore_extracts_each_source_item_separately(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    created_at = _now()

    for index, name in enumerate(("alpha.bin", "beta.bin"), start=1):
        source_item_id = uuid4()
        repos.source_items.add(
            SourceItemRecord(
                id=source_item_id,
                session_id=session.id,
                source_path=f"/tmp/{name}",
                display_name=name,
                status="completed",
                created_at=created_at,
            )
        )
        repos.archive_volumes.add(
            ArchiveVolumeRecord(
                id=uuid4(),
                source_item_id=source_item_id,
                file_name=f"{name}.7z.001",
                local_path=f"/tmp/{name}.7z.001",
                part_number=1,
                status="uploaded",
                external_file_id=str(index),
                external_message_id=str(index),
                provider_download_ref=f"client:-1001:{index}:900{index}",
                created_at=created_at,
            )
        )

    class CountingArchiveService(FakeArchiveService):
        def __init__(self) -> None:
            super().__init__()
            self.extract_calls = 0

        def extract(self, volume_paths: list[Path], dest_dir: Path, encryption_key: str) -> Path:
            self.extract_calls += 1
            return super().extract(volume_paths, dest_dir, encryption_key)

    archive_service = CountingArchiveService()
    storage = FakeStorageProvider()
    dest_path = tmp_path / "restored"
    restored = RestoreSessionUseCase(
        sessions=repos.sessions,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        archive_service=archive_service,
        staging_dir=tmp_path / "staging",
        target_chat_id="-1001",
    ).execute(session.id, dest_path)

    assert archive_service.extract_calls == 2
    assert len(storage.downloaded_files) == 2
    assert len(restored) == 2
