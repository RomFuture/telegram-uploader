from pathlib import Path
from uuid import uuid4

import pytest

import domain as domain
from domain.models import ArchiveVolume
from use_cases.restore.refs import (
    has_legacy_bot_volumes,
    is_client_restore_ref,
    is_volume_restorable,
    restorable_source_item_ids,
    restore_ref_for_volume,
)


def _uploaded_volume(
    *,
    provider_download_ref: str | None = None,
    part_number: int = 1,
) -> ArchiveVolume:
    session = domain.create_session("default", "secret")
    volume = domain.create_archive_volume(
        source_item_id=session.id,
        file_name=f"abc.7z.{part_number:03d}",
        local_path=Path(f"/tmp/outgoing/abc.7z.{part_number:03d}"),
        part_number=part_number,
    )
    return domain.mark_archive_volume_uploaded(
        volume,
        external_file_id="9001",
        external_message_id="42",
        provider_download_ref=provider_download_ref,
    )


def test_is_client_restore_ref() -> None:
    assert is_client_restore_ref("client:-1001:42:9001") is True
    assert is_client_restore_ref("bot-unique-id") is False
    assert is_client_restore_ref("message:-1001:42") is False


def test_restore_ref_for_volume_returns_client_ref() -> None:
    volume = _uploaded_volume(provider_download_ref="client:-1001:99:1")
    assert restore_ref_for_volume(volume, "-1001") == "client:-1001:99:1"


def test_restore_ref_for_volume_raises_for_legacy_bot_ref() -> None:
    volume = _uploaded_volume(provider_download_ref="bot-unique-id")
    with pytest.raises(domain.DomainError) as exc_info:
        restore_ref_for_volume(volume, "-1001")
    assert exc_info.value.code == "legacy_volumes"


def test_restore_ref_for_volume_raises_when_no_client_ref() -> None:
    volume = _uploaded_volume(provider_download_ref=None)
    with pytest.raises(domain.DomainError) as exc_info:
        restore_ref_for_volume(volume, "-1001")
    assert exc_info.value.reason == "missing_external_file_id"


def test_is_volume_restorable_requires_client_ref() -> None:
    client_volume = _uploaded_volume(provider_download_ref="client:-1001:99:1")
    legacy_volume = _uploaded_volume(provider_download_ref="bot-unique-id")
    message_only = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=uuid4(),
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="",
        external_message_id="99",
        provider_download_ref="",
    )

    assert is_volume_restorable(client_volume, "-1001") is True
    assert is_volume_restorable(legacy_volume, "-1001") is False
    assert is_volume_restorable(message_only, "-1001") is False


def test_has_legacy_bot_volumes() -> None:
    client_volume = _uploaded_volume(provider_download_ref="client:-1001:99:1")
    legacy_volume = _uploaded_volume(provider_download_ref="bot-unique-id")
    assert has_legacy_bot_volumes([client_volume]) is False
    assert has_legacy_bot_volumes([legacy_volume]) is True


def test_restorable_source_item_ids_requires_all_parts_client() -> None:
    item_id = uuid4()
    part_one = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=item_id,
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="9001",
        external_message_id="1",
        provider_download_ref="client:-1001:1:9001",
    )
    part_two = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=item_id,
            file_name="abc.7z.002",
            local_path=Path("/tmp/outgoing/abc.7z.002"),
            part_number=2,
        ),
        external_file_id="9002",
        external_message_id="2",
        provider_download_ref="client:-1001:2:9002",
    )
    legacy_part = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=item_id,
            file_name="abc.7z.003",
            local_path=Path("/tmp/outgoing/abc.7z.003"),
            part_number=3,
        ),
        external_file_id="9003",
        external_message_id="3",
        provider_download_ref="bot-legacy",
    )

    assert restorable_source_item_ids([part_one, part_two], "-1001") == {item_id}
    assert restorable_source_item_ids([part_one, part_two, legacy_part], "-1001") == set()
