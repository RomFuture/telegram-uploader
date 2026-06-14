from collections.abc import Callable
from pathlib import Path

import pytest

import domain as domain_module
from infrastructure.providers.telegram_client_provider import (
    TelegramClientProvider,
    build_client_download_ref,
    parse_client_download_ref,
)
from infrastructure.providers.telegram_provider import TelegramProviderV1
from use_cases.restore.refs import is_volume_restorable, restore_ref_for_volume
from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    RestoreRefCapability,
    UploadResult,
)
from use_cases.shared.ports.storage_provider import StorageProviderPort

TEST_SESSION = Path("/tmp/provider-contract.session")


class DummyProvider:
    remote_target = "-1001"

    def healthcheck(self) -> bool:
        return bool(self.remote_target)

    def upload_file(self, local_path: Path, display_name: str) -> UploadResult:
        return UploadResult(
            provider_name="dummy",
            external_file_id="file-id",
            external_message_id="msg-id",
            provider_download_ref="download-ref",
            provider_file_name=display_name,
        )

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        return ProviderFileInfo(
            provider_name="dummy",
            external_file_id=external_file_id,
            provider_download_ref="download-ref",
            provider_file_name="archive.001",
            size_bytes=123,
        )

    def download_file(
        self,
        file_info: ProviderFileInfo,
        destination_path: Path,
        resume: bool = False,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> Path:
        return destination_path

    def assess_restore_ref(self, provider_download_ref: str) -> RestoreRefCapability:
        if provider_download_ref == "download-ref":
            return RestoreRefCapability.RESTORABLE
        return RestoreRefCapability.UNSUPPORTED

    def resolve_restore_ref(self, provider_download_ref: str) -> str:
        return provider_download_ref

    def classify_error(self, error: Exception) -> ClassifiedProviderError:
        return ClassifiedProviderError(category=ProviderErrorCategory.UNKNOWN, reason=str(error))

    def provider_limits(self) -> ProviderLimits:
        return ProviderLimits(
            max_upload_size_bytes=2_000_000_000,
            supports_resume_download=True,
            rate_limit_window_seconds=None,
            rate_limit_max_requests=None,
        )


def _client_provider() -> TelegramClientProvider:
    return TelegramClientProvider(
        api_id=1,
        api_hash="hash",
        session_path=TEST_SESSION,
        remote_target="-1001",
    )


def test_dummy_provider_matches_storage_provider_port() -> None:
    provider = DummyProvider()
    assert isinstance(provider, StorageProviderPort)


def test_telegram_bot_provider_matches_storage_provider_port() -> None:
    provider = TelegramProviderV1(
        bot_token="token",
        base_url="http://localhost:8081",
        remote_target="-1001",
    )
    assert isinstance(provider, StorageProviderPort)


def test_client_provider_assess_restore_ref() -> None:
    provider = _client_provider()
    client_ref = build_client_download_ref("-1001", 42, 9001)
    assert provider.assess_restore_ref(client_ref) == RestoreRefCapability.RESTORABLE
    assert provider.assess_restore_ref("bot-unique-id") == RestoreRefCapability.UNSUPPORTED_LEGACY
    assert provider.assess_restore_ref("") == RestoreRefCapability.UNSUPPORTED


def test_bot_provider_assess_restore_ref_is_legacy() -> None:
    provider = TelegramProviderV1(
        bot_token="token",
        base_url="http://localhost:8081",
        remote_target="-1001",
    )
    assert provider.assess_restore_ref("AgACAgIAAxk") == RestoreRefCapability.UNSUPPORTED_LEGACY


def test_restore_ref_for_volume_accepts_client_provider_ref() -> None:
    provider = _client_provider()
    session = domain_module.create_session("default", "secret")
    client_ref = build_client_download_ref("-1001", 42, 9001)
    volume = domain_module.mark_archive_volume_uploaded(
        domain_module.create_archive_volume(
            source_item_id=session.id,
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="9001",
        external_message_id="42",
        provider_download_ref=client_ref,
    )
    ref = restore_ref_for_volume(volume, provider)
    assert ref == client_ref
    assert parse_client_download_ref(ref) == ("-1001", 42, 9001)
    assert is_volume_restorable(volume, provider)


def test_restore_ref_for_volume_raises_legacy_with_client_provider() -> None:
    provider = _client_provider()
    session = domain_module.create_session("default", "secret")
    volume = domain_module.mark_archive_volume_uploaded(
        domain_module.create_archive_volume(
            source_item_id=session.id,
            file_name="abc.7z.001",
            local_path=Path("/tmp/outgoing/abc.7z.001"),
            part_number=1,
        ),
        external_file_id="9001",
        external_message_id="42",
        provider_download_ref="bot-unique-id",
    )
    with pytest.raises(domain_module.DomainError) as exc_info:
        restore_ref_for_volume(volume, provider)
    assert exc_info.value.code == "legacy_volumes"


def test_client_upload_ref_matches_restore_policy() -> None:
    client_ref = build_client_download_ref("-100123", 7, 555)
    provider = _client_provider()
    assert provider.assess_restore_ref(client_ref) == RestoreRefCapability.RESTORABLE
    assert parse_client_download_ref(client_ref) == ("-100123", 7, 555)
