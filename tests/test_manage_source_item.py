from pathlib import Path
from uuid import uuid4

import pytest

import domain as domain
from tests.fakes.repositories import InMemoryRepositories
from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.session.create import CreateDatabaseUseCase, CreateFolderUseCase
from use_cases.session.manage_source_item import (
    DeleteSourceItemUseCase,
    MoveSourceItemUseCase,
    RenameSourceItemUseCase,
)


def test_rename_move_delete_source_item(tmp_path: Path) -> None:
    repos = InMemoryRepositories()
    session = CreateDatabaseUseCase(repos.sessions, repos.folders).execute("vault", "secret")
    folder_b = CreateFolderUseCase(repos.folders).execute(session.id, "other")
    source_file = tmp_path / "payload.bin"
    source_file.write_bytes(b"x")
    item = EnqueueSourceItemUseCase(repos.source_items, repos.folders).execute(
        session.id,
        source_file,
        "Original name",
    )

    RenameSourceItemUseCase(repos.source_items).execute(item.id, "Renamed")
    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.display_name == "Renamed"

    MoveSourceItemUseCase(repos.source_items, repos.folders).execute(item.id, folder_b.id)
    stored = repos.source_items.get(item.id)
    assert stored is not None
    assert stored.folder_id == folder_b.id

    DeleteSourceItemUseCase(repos.source_items, repos.archive_volumes).execute(item.id)
    assert repos.source_items.get(item.id) is None


def test_rename_rejects_empty_name() -> None:
    repos = InMemoryRepositories()
    with pytest.raises(domain.DomainError) as exc:
        RenameSourceItemUseCase(repos.source_items).execute(uuid4(), "   ")
    assert exc.value.code == "invalid_input"
