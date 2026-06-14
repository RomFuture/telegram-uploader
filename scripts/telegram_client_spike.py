#!/usr/bin/env python3
"""Spike: Telegram Client API login and optional upload/download round-trip.

Usage (from repo root, with .env configured):

  # Login only (phone + code) — no test file needed:
  PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only

  # Full round-trip with a real local file:
  # PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py \\
  #   /tmp/telegram_uploader/spike-test.bin

Requires TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_PATH, TELEGRAM_TARGET_CHAT_ID.
First run may prompt for phone/code interactively via Telethon.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from infrastructure.config import AppConfig, load_config  # noqa: E402
from infrastructure.providers.telegram_client_provider import (  # noqa: E402
    TelegramClientProvider,
)


def _load_provider() -> tuple[AppConfig, TelegramClientProvider]:
    cfg = load_config()
    if cfg.telegram_api_id is None or not cfg.telegram_api_hash:
        print(
            "error: set TELEGRAM_API_ID and TELEGRAM_API_HASH in Settings → Save,\n"
            "  or in ~/.config/telegram-uploader/.env",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not cfg.telegram_target_chat_id:
        print(
            "error: set TELEGRAM_TARGET_CHAT_ID in Settings → General → Save",
            file=sys.stderr,
        )
        raise SystemExit(1)

    cfg.telegram_session_path.parent.mkdir(parents=True, exist_ok=True)
    provider = TelegramClientProvider(
        api_id=cfg.telegram_api_id,
        api_hash=cfg.telegram_api_hash,
        session_path=cfg.telegram_session_path,
        remote_target=cfg.telegram_target_chat_id,
    )
    return cfg, provider


def _run_login_only(cfg: AppConfig, provider: TelegramClientProvider) -> int:
    print("Connecting to Telegram (enter phone and code if asked)...", flush=True)
    if not provider.healthcheck():
        print(
            "error: login or healthcheck failed — check .env, group membership, and chat id",
            file=sys.stderr,
        )
        return 1
    print(f"Login OK — session saved to {cfg.telegram_session_path}")
    print("You can close this window and use Test Client API or Start Backup in the app.")
    return 0


def _run_round_trip(cfg: AppConfig, provider: TelegramClientProvider, file_path: Path) -> int:
    if not file_path.is_file():
        if "path/to" in file_path.as_posix():
            print(f"error: not a real file: {file_path}", file=sys.stderr)
            print(
                "  Docs use /path/to/... as an example. Either create a real file, or run:\n"
                "  PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only",
                file=sys.stderr,
            )
        else:
            print(f"error: file not found: {file_path}", file=sys.stderr)
        return 1

    print("healthcheck...", flush=True)
    if not provider.healthcheck():
        print("error: healthcheck failed — check session auth and group access", file=sys.stderr)
        return 1

    print(f"uploading {file_path.name}...", flush=True)
    upload = provider.upload_file(
        file_path,
        file_path.name,
    )
    print(f"  message_id={upload.external_message_id} ref={upload.provider_download_ref}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest = Path(tmp_dir) / file_path.name
        info = provider.get_file_info(upload.provider_download_ref)
        print(f"downloading to {dest}...", flush=True)
        provider.download_file(info, dest)
        if file_path.read_bytes() != dest.read_bytes():
            print("error: downloaded bytes do not match original", file=sys.stderr)
            return 1

    print("round-trip OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram Client API login / round-trip spike")
    parser.add_argument(
        "file_path",
        type=Path,
        nargs="?",
        help="Local file for upload+download test (optional with --login-only)",
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Authenticate and save session only (no test upload)",
    )
    args = parser.parse_args()

    if not args.login_only and args.file_path is None:
        parser.print_help()
        print(
            "\nQuick start:\n"
            "  telegram-uploader-login\n"
            "  # or: PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only",
            file=sys.stderr,
        )
        return 1

    cfg, provider = _load_provider()
    if args.login_only:
        return _run_login_only(cfg, provider)
    assert args.file_path is not None
    return _run_round_trip(cfg, provider, args.file_path)


if __name__ == "__main__":
    raise SystemExit(main())
