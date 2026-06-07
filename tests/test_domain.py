import ast
from pathlib import Path
from uuid import UUID

import pytest

from domain.errors import InvalidStatusTransition
from domain.models import (
    ArchiveVolume,
    ArchiveVolumeStatus,
    Session,
    SessionStatus,
    SourceItem,
    SourceItemStatus,
)


def test_session_create_sets_created_status_and_uuid() -> None:
    session = Session.create("default", "secret-key")
    assert isinstance(session.id, UUID)
    assert session.status == SessionStatus.CREATED
    assert session.profile_name == "default"
    assert session.encryption_key == "secret-key"


def test_source_item_create_requires_display_name() -> None:
    session_id = Session.create("default", "secret-key").id
    item = SourceItem.create(session_id, Path("/tmp/real-name.mov"), "Holiday clip")
    assert item.display_name == "Holiday clip"
    assert item.source_path == Path("/tmp/real-name.mov")
    assert item.display_name != item.source_path.name


def test_archive_volume_create_sets_defaults() -> None:
    volume = ArchiveVolume.create(
        source_item_id=Session.create("default", "secret-key").id,
        file_name="abc.7z.001",
        local_path=Path("/tmp/outgoing/abc.7z.001"),
        part_number=1,
    )
    assert volume.status == ArchiveVolumeStatus.CREATED
    assert volume.external_file_id is None
    assert volume.external_message_id is None
    assert volume.provider_download_ref is None


@pytest.mark.parametrize(
    "enum_cls",
    [SessionStatus, SourceItemStatus, ArchiveVolumeStatus],
)
def test_status_enums_are_str_subclasses(enum_cls: type) -> None:
    assert issubclass(enum_cls, str)
    for member in enum_cls:
        assert isinstance(member.value, str)


def test_invalid_status_transition_carries_entity_context() -> None:
    error = InvalidStatusTransition.create("SourceItem", "queued", "uploading")
    assert error.entity == "SourceItem"
    assert error.from_status == "queued"
    assert error.to_status == "uploading"
    assert "SourceItem" in str(error)


def test_domain_has_no_outward_layer_imports() -> None:
    forbidden_roots = {"use_cases", "infrastructure", "application", "observation"}
    forbidden_third_party = {"sqlalchemy", "celery", "urllib", "redis", "psycopg"}
    root = Path("src/domain")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in forbidden_roots, f"{path}: {alias.name}"
                    assert top not in forbidden_third_party, f"{path}: {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden_roots, f"{path}: {node.module}"
                assert top not in forbidden_third_party, f"{path}: {node.module}"
