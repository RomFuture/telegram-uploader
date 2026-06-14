"""Tests for restore folder scope and download progress logging."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

import domain as domain
from observation.restore_download_progress import make_download_progress_callback
from tests.fakes.ports import FakeArchiveService, FakeStorageProvider
from tests.fakes.repositories import InMemoryRepositories
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.restore.scope import filter_restorable_ids_by_folder, is_session_wide_restore_scope
from use_cases.session.create import CreateDatabaseUseCase, CreateFolderUseCase
from use_cases.shared.folders import DEFAULT_FOLDER_NAME
from use_cases.shared.persistence import ArchiveVolumeRecord, SourceItemRecord


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _add_restorable_item(
    repos: InMemoryRepositories,
    *,
    session_id,
    display_name: str,
    folder_id,
    chat_ref_suffix: str,
) -> None:
    source_item_id = uuid4()
    repos.source_items.add(
        SourceItemRecord(
            id=source_item_id,
            session_id=session_id,
            source_path=f"/tmp/{display_name}",
            display_name=display_name,
            status="completed",
            created_at=_now(),
            folder_id=folder_id,
        )
    )
    repos.archive_volumes.add(
        ArchiveVolumeRecord(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name=f"{display_name}.7z.001",
            local_path=f"/tmp/{display_name}.7z.001",
            part_number=1,
            status="uploaded",
            external_file_id=chat_ref_suffix,
            external_message_id=chat_ref_suffix,
            provider_download_ref=f"client:-1001:{chat_ref_suffix}:900{chat_ref_suffix}",
            created_at=_now(),
        )
    )


def test_is_session_wide_restore_scope() -> None:
    assert is_session_wide_restore_scope(None, None) is True
    assert is_session_wide_restore_scope(uuid4(), DEFAULT_FOLDER_NAME) is True
    assert is_session_wide_restore_scope(uuid4(), "Work") is False


def test_restorable_scope_all_files_includes_every_folder() -> None:
    id_a = uuid4()
    id_b = uuid4()
    all_ids = {id_a, id_b}
    items = [
        SourceItemRecord(
            id=id_a,
            session_id=uuid4(),
            source_path="/a",
            display_name="a",
            status="completed",
            created_at=_now(),
            folder_id=uuid4(),
        ),
        SourceItemRecord(
            id=id_b,
            session_id=uuid4(),
            source_path="/b",
            display_name="b",
            status="completed",
            created_at=_now(),
            folder_id=uuid4(),
        ),
    ]
    result = filter_restorable_ids_by_folder(
        restorable_ids_in_session=all_ids,
        source_items=items,
        folder_id=uuid4(),
        folder_name=DEFAULT_FOLDER_NAME,
    )
    assert result == all_ids


def test_restorable_scope_filters_single_folder() -> None:
    folder_a = uuid4()
    folder_b = uuid4()
    item_a = uuid4()
    item_b = uuid4()
    items = [
        SourceItemRecord(
            id=item_a,
            session_id=uuid4(),
            source_path="/a",
            display_name="a",
            status="completed",
            created_at=_now(),
            folder_id=folder_a,
        ),
        SourceItemRecord(
            id=item_b,
            session_id=uuid4(),
            source_path="/b",
            display_name="b",
            status="completed",
            created_at=_now(),
            folder_id=folder_b,
        ),
    ]
    result = filter_restorable_ids_by_folder(
        restorable_ids_in_session={item_a, item_b},
        source_items=items,
        folder_id=folder_b,
        folder_name="TEST",
    )
    assert result == {item_b}


def test_restore_from_folder_downloads_only_that_folder(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateDatabaseUseCase(repos.sessions, repos.folders).execute("default", "secret")
    all_files = repos.folders.list_by_session(session.id)[0]
    test_folder = CreateFolderUseCase(repos.folders).execute(session.id, "TEST")

    _add_restorable_item(
        repos,
        session_id=session.id,
        display_name="keep-in-all.bin",
        folder_id=all_files.id,
        chat_ref_suffix="1",
    )
    _add_restorable_item(
        repos,
        session_id=session.id,
        display_name="only-test.bin",
        folder_id=test_folder.id,
        chat_ref_suffix="2",
    )

    storage = FakeStorageProvider()
    RestoreSessionUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        folders=repos.folders,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        archive_service=FakeArchiveService(),
        staging_dir=tmp_path / "staging",
    ).execute(session.id, tmp_path / "restored", folder_id=test_folder.id)

    assert len(storage.downloaded_files) == 1
    assert storage.downloaded_files[0].name == "only-test.bin.7z.001"


def test_restore_from_all_files_downloads_whole_session(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateDatabaseUseCase(repos.sessions, repos.folders).execute("default", "secret")
    all_files = repos.folders.list_by_session(session.id)[0]
    test_folder = CreateFolderUseCase(repos.folders).execute(session.id, "TEST")

    _add_restorable_item(
        repos,
        session_id=session.id,
        display_name="alpha.bin",
        folder_id=all_files.id,
        chat_ref_suffix="1",
    )
    _add_restorable_item(
        repos,
        session_id=session.id,
        display_name="beta.bin",
        folder_id=test_folder.id,
        chat_ref_suffix="2",
    )

    storage = FakeStorageProvider()
    RestoreSessionUseCase(
        sessions=repos.sessions,
        source_items=repos.source_items,
        folders=repos.folders,
        archive_volumes=repos.archive_volumes,
        storage_provider=storage,
        archive_service=FakeArchiveService(),
        staging_dir=tmp_path / "staging",
    ).execute(session.id, tmp_path / "restored", folder_id=all_files.id)

    assert len(storage.downloaded_files) == 2


def test_restore_empty_folder_raises(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateDatabaseUseCase(repos.sessions, repos.folders).execute("default", "secret")
    all_files = repos.folders.list_by_session(session.id)[0]
    empty_folder = CreateFolderUseCase(repos.folders).execute(session.id, "Empty")
    _add_restorable_item(
        repos,
        session_id=session.id,
        display_name="only-all.bin",
        folder_id=all_files.id,
        chat_ref_suffix="1",
    )

    with pytest.raises(domain.DomainError) as error:
        RestoreSessionUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            folders=repos.folders,
            archive_volumes=repos.archive_volumes,
            storage_provider=FakeStorageProvider(),
            archive_service=FakeArchiveService(),
            staging_dir=tmp_path / "staging",
        ).execute(session.id, tmp_path / "restored", folder_id=empty_folder.id)

    assert error.value.code == "no_restorable_backups_in_folder"


def test_download_progress_callback_logs_percent_and_heartbeat(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="observation.restore.download")
    callback = make_download_progress_callback(label="vol.7z.001", heartbeat_seconds=0.0)
    callback(0, 100)
    callback(25, 100)
    callback(50, 100)
    callback(100, 100)

    messages = [record.message for record in caplog.records]
    assert any("download progress vol.7z.001 25%" in message for message in messages)
    assert any("download progress vol.7z.001 100%" in message for message in messages)
