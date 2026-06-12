"""Optional live Telethon integration tests (opt-in via env)."""

import os
from pathlib import Path

import pytest

from infrastructure.config import load_config
from infrastructure.providers.telegram_client_provider import TelegramClientProvider


@pytest.mark.integration
def test_live_client_healthcheck() -> None:
    if os.environ.get("TELEGRAM_INTEGRATION") != "1":
        pytest.skip("Set TELEGRAM_INTEGRATION=1 to run live Client API tests")

    config = load_config()
    if config.telegram_api_id is None or not config.telegram_api_hash:
        pytest.skip("TELEGRAM_API_ID and TELEGRAM_API_HASH required")

    if not config.telegram_session_path.exists():
        pytest.skip(
            f"Session file missing: {config.telegram_session_path} "
            "(run scripts/telegram_client_spike.py first)"
        )

    provider = TelegramClientProvider(
        api_id=config.telegram_api_id,
        api_hash=config.telegram_api_hash,
        session_path=Path(config.telegram_session_path),
    )
    assert provider.healthcheck(config.telegram_target_chat_id)
