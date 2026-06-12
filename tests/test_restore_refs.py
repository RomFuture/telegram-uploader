from pathlib import Path

import pytest

import domain as domain
from use_cases.restore.refs import (
    external_file_id_for_restore,
    restore_download_ref,
    restore_ref_for_volume,
)


def test_restore_download_ref_raises_when_no_provider_ref_or_file_id() -> None:
    volume = domain.create_archive_volume(
        source_item_id=domain.create_session("default", "secret").id,
        file_name="abc.7z.001",
        local_path=Path("/tmp/outgoing/abc.7z.001"),
        part_number=1,
    )
    with pytest.raises(domain.DomainError) as exc_info:
        restore_download_ref(volume)
    error = exc_info.value
    assert error.code == "archive_volume_not_found"
    assert error.reason == "missing_external_file_id"
    assert error.entity_id == volume.id


def test_restore_ref_for_volume_raises_when_no_refs() -> None:
    volume = domain.create_archive_volume(
        source_item_id=domain.create_session("default", "secret").id,
        file_name="abc.7z.001",
        local_path=Path("/tmp/outgoing/abc.7z.001"),
        part_number=1,
    )
    with pytest.raises(domain.DomainError):
        restore_ref_for_volume(volume, "-1001")


def test_restore_download_ref_prefers_provider_download_ref() -> None:
    volume = domain.create_archive_volume(
        source_item_id=domain.create_session("default", "secret").id,
        file_name="abc.7z.001",
        local_path=Path("/tmp/outgoing/abc.7z.001"),
        part_number=1,
    )
    volume = domain.mark_archive_volume_uploaded(
        volume,
        external_file_id="bot-file-id",
        external_message_id="99",
        provider_download_ref="client:-1001:99:1",
    )
    assert restore_download_ref(volume) == "client:-1001:99:1"
    assert restore_ref_for_volume(volume, "-1001") == "client:-1001:99:1"
    assert external_file_id_for_restore(volume) == "client:-1001:99:1"


def test_restore_download_ref_falls_back_to_external_file_id() -> None:
    volume = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=domain.create_session("default", "secret").id,
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="bot-file-id",
        external_message_id="99",
        provider_download_ref="",
    )
    assert restore_download_ref(volume) == "bot-file-id"


def test_restore_ref_for_volume_falls_back_to_message_id() -> None:
    volume = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=domain.create_session("default", "secret").id,
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="",
        external_message_id="99",
        provider_download_ref="",
    )
    assert restore_ref_for_volume(volume, "-1001") == "message:-1001:99"
