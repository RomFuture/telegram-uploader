from pathlib import Path

from tests.fakes.repositories import InMemoryRepositories
from use_cases.session.create import CreateDatabaseUseCase, CreateSessionUseCase
from use_cases.session.get_session_queue_snapshot import GetSessionQueueSnapshotUseCase
from use_cases.session.list import ListSessionProfilesUseCase
from use_cases.session.unlock_session import UnlockSessionUseCase


def test_create_session_generates_key_when_empty() -> None:
    repos = InMemoryRepositories()

    outcome = CreateSessionUseCase(repos.sessions).execute("default", None)

    assert outcome.generated_encryption_key is not None
    assert len(outcome.generated_encryption_key) >= 32
    stored = repos.sessions.get(outcome.session.id)
    assert stored is not None
    assert stored.encryption_key == outcome.generated_encryption_key


def test_create_session_uses_provided_key() -> None:
    repos = InMemoryRepositories()

    outcome = CreateSessionUseCase(repos.sessions).execute("default", "user-secret")

    assert outcome.generated_encryption_key is None
    stored = repos.sessions.get(outcome.session.id)
    assert stored is not None
    assert stored.encryption_key == "user-secret"


def test_get_session_queue_snapshot_reads_display_name_from_repository(
    tmp_path: Path,
) -> None:
    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    source_file = tmp_path / "ignored.bin"
    source_file.write_bytes(b"x")
    from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase

    EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Shown in UI",
    )

    snapshot = GetSessionQueueSnapshotUseCase(repos.source_items, repos.folders).execute(session.id)

    assert len(snapshot.items) == 1
    assert snapshot.items[0].display_name == "Shown in UI"
    assert snapshot.items[0].display_name != source_file.name
    assert snapshot.items[0].size_label == "1 B"
    assert snapshot.items[0].modified_label != "—"


def test_get_session_queue_snapshot_missing_file_shows_dashes() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from use_cases.shared.persistence import SourceItemRecord

    repos = InMemoryRepositories()
    session = CreateSessionUseCase(repos.sessions).execute("default", "secret").session
    repos.source_items.add(
        SourceItemRecord(
            id=uuid4(),
            session_id=session.id,
            source_path="/nonexistent/file.bin",
            display_name="ghost.bin",
            status="queued",
            created_at=datetime(2025, 12, 20, 7, 35, tzinfo=UTC),
        )
    )

    snapshot = GetSessionQueueSnapshotUseCase(repos.source_items, repos.folders).execute(session.id)

    assert snapshot.items[0].size_label == "—"
    assert "12/20/25" in snapshot.items[0].modified_label


def test_list_profiles_returns_names() -> None:
    repos = InMemoryRepositories()
    CreateSessionUseCase(repos.sessions).execute("alpha", "k1")
    CreateSessionUseCase(repos.sessions).execute("beta", "k2")

    names = ListSessionProfilesUseCase(repos.sessions).execute()

    assert names == ("alpha", "beta")


def test_unlock_session_with_correct_key() -> None:
    repos = InMemoryRepositories()
    CreateSessionUseCase(repos.sessions).execute("default", "secret")

    session = UnlockSessionUseCase(repos.sessions).execute("default", "secret")

    assert session.profile_name == "default"


def test_unlock_session_wrong_key_raises() -> None:
    import pytest

    import domain as domain

    repos = InMemoryRepositories()
    CreateSessionUseCase(repos.sessions).execute("default", "secret")

    with pytest.raises(domain.DomainError) as exc:
        UnlockSessionUseCase(repos.sessions).execute("default", "wrong")

    assert exc.value.code == "wrong_encryption_key"


def test_create_database_requires_unique_profile() -> None:
    import pytest

    import domain as domain

    repos = InMemoryRepositories()
    CreateDatabaseUseCase(repos.sessions, repos.folders).execute("vault", "key1")

    with pytest.raises(domain.DomainError) as exc:
        CreateDatabaseUseCase(repos.sessions, repos.folders).execute("vault", "key2")

    assert exc.value.code == "profile_already_exists"
