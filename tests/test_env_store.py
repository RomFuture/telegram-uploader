from pathlib import Path

from application.env_store import merge_env_file, save_settings_env, settings_to_env_updates
from application.settings_values import SettingsValues


def test_save_settings_env_writes_telegram_keys(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / "telegram-uploader" / ".env"
    monkeypatch.setattr("application.env_store.user_env_path", lambda: env_path)

    save_settings_env(
        SettingsValues(
            encryption_key=None,
            target_chat_id="-100123",
            telegram_provider="client",
            telegram_api_id="36040005",
            telegram_api_hash="abc123",
            telegram_session_path="/tmp/telegram_uploader/session.session",
            telegram_bot_token="",
            telegram_bot_api_url="http://localhost:8081",
            archive_ram_limit_mb=1024,
        )
    )

    text = env_path.read_text()
    assert "TELEGRAM_API_ID=36040005" in text
    assert "TELEGRAM_API_HASH=abc123" in text
    assert "TELEGRAM_TARGET_CHAT_ID=-100123" in text
    assert "TELEGRAM_SESSION_PATH=" in text
    assert "/.config/telegram-uploader/session.session" in text
    assert "TELEGRAM_SESSION_DIR=" in text
    assert "/.config/telegram-uploader" in text


def test_merge_env_file_preserves_unknown_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("CUSTOM=value\nTELEGRAM_API_ID=old\n")
    merge_env_file(
        env_path,
        settings_to_env_updates(
            SettingsValues(
                encryption_key=None,
                target_chat_id="-1",
                telegram_provider="client",
                telegram_api_id="99",
                telegram_api_hash="hash",
                telegram_session_path="/tmp/s.session",
                telegram_bot_token="",
                telegram_bot_api_url="http://localhost:8081",
                archive_ram_limit_mb=1024,
            )
        ),
    )
    text = env_path.read_text()
    assert "CUSTOM=value" in text
    assert "TELEGRAM_API_ID=99" in text
