"""Packaged CLI: one-time Telegram sign-in (telegram-uploader-login)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from application.telegram_sign_in import TelegramSignInConfig, run_interactive_cli_sign_in
from infrastructure.config import load_config


def _show_intro(skip: bool) -> None:
    if skip:
        return
    intro_paths = (
        Path("/usr/share/telegram-uploader/telegram-login-intro.txt"),
        Path(__file__).resolve().parents[2] / "packaging" / "share" / "telegram-login-intro.txt",
    )
    for path in intro_paths:
        if path.is_file():
            print(path.read_text(encoding="utf-8"))
            break
    else:
        print(
            "Telegram Uploader — one-time sign-in\n\n"
            "Your Telegram account uploads backups to your private group.\n"
            "Credentials stay on this computer.\n\n"
            "Fill API ID, hash, and group ID in Settings → Save first."
        )
    print("")
    answer = input("Continue with Telegram sign-in? [Y/n] ").strip()
    if answer and answer.lower() not in {"y", "yes"}:
        print("Cancelled.")
        raise SystemExit(0)
    print("")


def _validate_config() -> TelegramSignInConfig:
    cfg = load_config()
    errors: list[str] = []
    if cfg.telegram_api_id is None:
        errors.append("TELEGRAM_API_ID missing — open the app → Settings → Client API → Save")
    if not cfg.telegram_api_hash:
        errors.append("TELEGRAM_API_HASH missing — Settings → Client API → Save")
    if not cfg.telegram_target_chat_id:
        errors.append("TELEGRAM_TARGET_CHAT_ID missing — Settings → General → Save")
    if errors:
        print("error: cannot sign in yet:", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Config: ~/.config/telegram-uploader/.env", file=sys.stderr)
        raise SystemExit(1)
    assert cfg.telegram_api_id is not None
    session_path = cfg.telegram_session_path
    return TelegramSignInConfig(
        api_id=cfg.telegram_api_id,
        api_hash=cfg.telegram_api_hash,
        session_path=session_path,
        target_chat_id=cfg.telegram_target_chat_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-time Telegram Client API sign-in (phone + code)."
    )
    parser.add_argument(
        "--no-intro",
        action="store_true",
        help="Skip privacy intro (used when launched from GUI terminal fallback)",
    )
    args = parser.parse_args()
    _show_intro(args.no_intro)
    config = _validate_config()
    print("Connecting to Telegram…")
    print("Enter phone number and code when asked (data goes to Telegram only).")
    print("")
    try:
        run_interactive_cli_sign_in(config)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Login OK — session saved to {config.session_path}")
    print("You can close this window and use Test Client API or Start Backup in the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
