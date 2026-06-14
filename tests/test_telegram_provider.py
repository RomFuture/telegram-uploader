from urllib import error

from infrastructure.providers.telegram_provider import TelegramProviderV1
from use_cases.shared.dto import ProviderErrorCategory


def test_telegram_provider_classifies_rate_limit_error() -> None:
    provider = TelegramProviderV1(
        bot_token="token",
        base_url="http://localhost:8081",
        remote_target="-1001",
    )
    classified = provider.classify_error(Exception("Flood control exceeded. Retry after 42"))
    assert classified.category == ProviderErrorCategory.RATE_LIMITED
    assert classified.retry_after_seconds == 42


def test_telegram_provider_classifies_auth_error() -> None:
    provider = TelegramProviderV1(
        bot_token="token",
        base_url="http://localhost:8081",
        remote_target="-1001",
    )
    classified = provider.classify_error(Exception("Unauthorized"))
    assert classified.category == ProviderErrorCategory.AUTH


def test_telegram_provider_classifies_transport_error() -> None:
    provider = TelegramProviderV1(
        bot_token="token",
        base_url="http://localhost:8081",
        remote_target="-1001",
    )
    classified = provider.classify_error(error.URLError("offline"))
    assert classified.category == ProviderErrorCategory.TRANSPORT
