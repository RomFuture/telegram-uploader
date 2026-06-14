from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.providers.telegram_client_provider import (
    TelegramClientProvider,
    TelegramClientProviderError,
    build_client_download_ref,
    parse_client_download_ref,
)
from use_cases.shared.dto import ProviderErrorCategory, RestoreRefCapability
from use_cases.shared.ports.storage_provider import StorageProviderPort

TEST_SESSION = Path("/tmp/x.session")


def _provider() -> TelegramClientProvider:
    return TelegramClientProvider(
        api_id=1,
        api_hash="hash",
        session_path=TEST_SESSION,
        remote_target="-1001",
    )


def test_build_and_parse_client_download_ref() -> None:
    ref = build_client_download_ref("-100123", 42, 99)
    assert ref == "client:-100123:42:99"
    assert parse_client_download_ref(ref) == ("-100123", 42, 99)


def test_parse_client_download_ref_rejects_invalid() -> None:
    with pytest.raises(TelegramClientProviderError):
        parse_client_download_ref("bot:file-id")


def test_client_provider_matches_storage_provider_port() -> None:
    provider = _provider()
    assert isinstance(provider, StorageProviderPort)


def test_client_provider_assess_and_resolve_restore_ref() -> None:
    provider = _provider()
    ref = build_client_download_ref("-100123", 42, 99)
    assert provider.assess_restore_ref(ref) == RestoreRefCapability.RESTORABLE
    assert provider.resolve_restore_ref(ref) == ref
    assert provider.assess_restore_ref("bot-file-id") == RestoreRefCapability.UNSUPPORTED_LEGACY
    assert provider.assess_restore_ref("") == RestoreRefCapability.UNSUPPORTED


def test_classify_error_maps_flood() -> None:
    provider = _provider()
    classified = provider.classify_error(Exception("FloodWaitError: wait 30"))
    assert classified.category == ProviderErrorCategory.RATE_LIMITED


@patch("infrastructure.providers.telegram_client_provider._run_async")
def test_get_file_info_parses_client_ref_without_network(mock_run: MagicMock) -> None:
    provider = _provider()
    ref = build_client_download_ref("-1001", 7, 3)
    info = provider.get_file_info(ref)
    assert info.provider_download_ref == ref
    assert info.external_file_id == "3"
    mock_run.assert_not_called()


@patch("infrastructure.providers.telegram_client_provider._run_async")
def test_upload_file_delegates_to_async(mock_run: MagicMock, tmp_path: Path) -> None:
    source = tmp_path / "vol.7z.001"
    source.write_bytes(b"data")
    ref = build_client_download_ref("-1001", 1, 2)
    mock_run.return_value = MagicMock(
        provider_name="telegram_client",
        external_file_id="2",
        external_message_id="1",
        provider_download_ref=ref,
        provider_file_name="vol.7z.001",
    )
    provider = _provider()
    result = provider.upload_file(source, "vol.7z.001")
    assert result.provider_download_ref == ref
    mock_run.assert_called_once()


@patch("infrastructure.providers.telegram_client_provider._run_async")
def test_healthcheck_returns_false_on_error(mock_run: MagicMock) -> None:
    mock_run.side_effect = RuntimeError("not authorized")
    provider = _provider()
    assert provider.healthcheck() is False


@patch("infrastructure.providers.telegram_client_provider._run_async")
def test_download_file_delegates_to_async(mock_run: MagicMock, tmp_path: Path) -> None:
    ref = build_client_download_ref("-1001", 7, 3)
    destination = tmp_path / "vol.7z.001"
    mock_run.return_value = destination
    provider = _provider()
    file_info = provider.get_file_info(ref)
    result = provider.download_file(file_info, destination)
    assert result == destination
    mock_run.assert_called_once()


@patch("infrastructure.providers.telegram_client_provider._run_async")
def test_healthcheck_returns_true_when_authorized(mock_run: MagicMock) -> None:
    mock_run.return_value = True
    provider = _provider()
    assert provider.healthcheck() is True
