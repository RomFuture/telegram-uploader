from pathlib import Path
from uuid import UUID, uuid4

import pytest

import domain as domain
from domain.errors import DomainError
from domain.models import (
    ArchiveVolumeStatus,
    SessionStatus,
    SourceItemStatus,
)


def test_create_session_sets_created_status_and_uuid() -> None:
    session = domain.create_session("default", "secret-key")
    assert isinstance(session.id, UUID)
    assert session.status == SessionStatus.CREATED
    assert session.profile_name == "default"
    assert session.encryption_key == "secret-key"


def test_create_source_item_requires_display_name() -> None:
    session_id = domain.create_session("default", "secret-key").id
    item = domain.create_source_item(session_id, Path("/tmp/real-name.mov"), "Holiday clip")
    assert item.display_name == "Holiday clip"
    assert item.source_path == Path("/tmp/real-name.mov")
    assert item.display_name != item.source_path.name


def test_create_archive_volume_sets_defaults() -> None:
    volume = domain.create_archive_volume(
        source_item_id=domain.create_session("default", "secret-key").id,
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
    error = DomainError.invalid_status_transition("SourceItem", "queued", "uploading")
    assert error.entity == "SourceItem"
    assert error.from_status == "queued"
    assert error.to_status == "uploading"
    assert error.code == "invalid_status_transition"
    assert "SourceItem" in error.message


def test_not_found_errors_carry_ids() -> None:
    session_id = uuid4()
    item_id = uuid4()
    volume_id = uuid4()

    session_error = DomainError.session_not_found(session_id)
    assert session_error.entity_id == session_id
    assert session_error.code == "session_not_found"
    assert str(session_id) in session_error.message

    item_error = DomainError.source_item_not_found(item_id)
    assert item_error.entity_id == item_id
    assert item_error.code == "source_item_not_found"
    assert str(item_id) in item_error.message

    volume_error = DomainError.archive_volume_not_found(volume_id)
    assert volume_error.entity_id == volume_id
    assert volume_error.code == "archive_volume_not_found"
    assert str(volume_id) in volume_error.message


def test_required_sets_invalid_input_code_and_message() -> None:
    error = DomainError.required("Folder name")
    assert error.code == "invalid_input"
    assert error.message == "Folder name is required"


def test_folder_already_exists_carries_reason() -> None:
    error = DomainError.folder_already_exists("Work")
    assert error.code == "folder_already_exists"
    assert error.message == "Folder already exists: Work"
    assert error.reason == "Work"


def test_folder_not_found_carries_entity_id() -> None:
    folder_id = uuid4()
    error = DomainError.folder_not_found(folder_id)
    assert error.code == "folder_not_found"
    assert error.entity_id == folder_id
    assert str(folder_id) in error.message


def test_verify_source_item_queued_raises_domain_error() -> None:
    session_id = domain.create_session("default", "secret").id
    item = domain.mark_source_item(
        domain.create_source_item(session_id, Path("/tmp/a.bin"), "A"),
        status=domain.SourceItemStatus.ARCHIVING,
    )
    with pytest.raises(domain.DomainError) as exc_info:
        domain.verify_source_item(item, status=domain.SourceItemStatus.QUEUED)
    assert exc_info.value.code == "invalid_status_transition"


def test_public_api_exports_status_enums() -> None:
    assert set(domain.__all__) == {
        "ArchiveVolumeStatus",
        "DomainError",
        "SessionStatus",
        "SourceItemStatus",
        "create_archive_volume",
        "create_session",
        "create_source_item",
        "verify_archive_volume",
        "verify_session",
        "verify_source_item",
        "is_source_item",
        "mark_archive_volume",
        "mark_archive_volume_uploaded",
        "mark_session",
        "mark_source_item",
    }
