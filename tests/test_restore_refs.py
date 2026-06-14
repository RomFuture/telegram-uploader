from pathlib import Path
from uuid import uuid4

import pytest

import domain as domain
from domain.models import ArchiveVolume
from tests.fakes.ports import FakeStorageProvider
from use_cases.restore.refs import (
    count_incomplete_volumes,
    count_legacy_volumes,
    is_legacy_volume,
    is_volume_restorable,
    restore_ref_for_volume,
    source_item_ids_restorable_in_session,
)
from use_cases.shared.dto import RestoreRefCapability


def _provider() -> FakeStorageProvider:
    return FakeStorageProvider()


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


def test_fake_provider_assess_restore_ref() -> None:
    provider = _provider()
    assert provider.assess_restore_ref("client:-1001:42:9001") == RestoreRefCapability.RESTORABLE
    assert provider.assess_restore_ref("bot-unique-id") == RestoreRefCapability.UNSUPPORTED_LEGACY
    assert provider.assess_restore_ref("") == RestoreRefCapability.UNSUPPORTED


def test_restore_ref_for_volume_returns_client_ref() -> None:
    volume = _uploaded_volume(provider_download_ref="client:-1001:99:1")
    assert restore_ref_for_volume(volume, _provider()) == "client:-1001:99:1"


def test_restore_ref_for_volume_raises_for_legacy_bot_ref() -> None:
    volume = _uploaded_volume(provider_download_ref="bot-unique-id")
    with pytest.raises(domain.DomainError) as exc_info:
        restore_ref_for_volume(volume, _provider())
    assert exc_info.value.code == "legacy_volumes"


def test_restore_ref_for_volume_raises_when_no_client_ref() -> None:
    volume = _uploaded_volume(provider_download_ref=None)
    with pytest.raises(domain.DomainError) as exc_info:
        restore_ref_for_volume(volume, _provider())
    assert exc_info.value.reason == "missing_external_file_id"


def test_is_volume_restorable_requires_provider_supported_ref() -> None:
    provider = _provider()
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

    assert is_volume_restorable(client_volume, provider) is True
    assert is_volume_restorable(legacy_volume, provider) is False
    assert is_volume_restorable(message_only, provider) is False


def test_count_legacy_volumes() -> None:
    provider = _provider()
    client_volume = _uploaded_volume(provider_download_ref="client:-1001:99:1")
    legacy_volume = _uploaded_volume(provider_download_ref="bot-unique-id")
    item_id = legacy_volume.source_item_id
    assert count_legacy_volumes([client_volume], provider) == 0
    assert count_legacy_volumes([legacy_volume], provider) == 1
    assert (
        count_legacy_volumes([legacy_volume], provider, source_item_ids={item_id}) == 1
    )
    assert (
        count_legacy_volumes([legacy_volume], provider, source_item_ids={uuid4()}) == 0
    )


def test_count_incomplete_volumes_excludes_legacy() -> None:
    provider = _provider()
    item_id = uuid4()
    legacy_volume = domain.mark_archive_volume_uploaded(
        domain.create_archive_volume(
            source_item_id=item_id,
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="9001",
        external_message_id="42",
        provider_download_ref="bot-unique-id",
    )
    incomplete_volume = domain.create_archive_volume(
        source_item_id=item_id,
        file_name="abc.7z.002",
        local_path=Path("/tmp/outgoing/abc.7z.002"),
        part_number=2,
    )
    assert is_legacy_volume(legacy_volume, provider) is True
    assert (
        count_incomplete_volumes(
            [legacy_volume, incomplete_volume],
            provider,
            source_item_ids={item_id},
        )
        == 1
    )
    assert (
        count_legacy_volumes(
            [legacy_volume, incomplete_volume],
            provider,
            source_item_ids={item_id},
        )
        == 1
    )


def test_source_item_ids_restorable_in_session_requires_all_parts() -> None:
    provider = _provider()
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

    assert source_item_ids_restorable_in_session([part_one, part_two], provider) == {item_id}
    assert (
        source_item_ids_restorable_in_session([part_one, part_two, legacy_part], provider)
        == set()
    )
