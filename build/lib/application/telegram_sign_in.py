"""Telegram Client API sign-in (Telethon) — shared by CLI and GUI."""

from __future__ import annotations

import asyncio
import getpass
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from application.debug_log import agent_debug, path_diagnostics


class TelegramSignInError(Exception):
    pass


class TelegramPasswordRequired(TelegramSignInError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramSignInConfig:
    api_id: int
    api_hash: str
    session_path: Path
    target_chat_id: str


def _build_client(config: TelegramSignInConfig) -> Any:
    from telethon import TelegramClient

    config.session_path.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(config.session_path), config.api_id, config.api_hash)


async def send_login_code(config: TelegramSignInConfig, phone: str) -> str | None:
    """Request login code. Returns phone_code_hash for the follow-up sign_in step."""
    # region agent log
    agent_debug(
        "A",
        "telegram_sign_in.py:send_login_code:entry",
        "send_login_code start",
        {
            **path_diagnostics(config.session_path),
            "thread": threading.current_thread().name,
            "uid": os.getuid(),
            "phone_len": len(phone),
        },
    )
    # endregion

    client = _build_client(config)
    try:
        await client.connect()
        if await client.is_user_authorized():
            # region agent log
            agent_debug(
                "D",
                "telegram_sign_in.py:send_login_code:done",
                "already authorized",
                {"authorized": True},
            )
            # endregion
            return None
        sent = await client.send_code_request(phone)
        phone_code_hash = str(sent.phone_code_hash)
        # region agent log
        agent_debug(
            "D",
            "telegram_sign_in.py:send_login_code:done",
            "send_code_request ok",
            {"authorized": False, "has_phone_code_hash": bool(phone_code_hash)},
        )
        # endregion
        return phone_code_hash
    except Exception as error:
        # region agent log
        agent_debug(
            "C",
            "telegram_sign_in.py:send_login_code:telethon",
            "telethon failed",
            {
                **path_diagnostics(config.session_path),
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        # endregion
        raise
    finally:
        await client.disconnect()


async def complete_login(
    config: TelegramSignInConfig,
    phone: str,
    code: str,
    phone_code_hash: str | None,
    password: str | None = None,
) -> None:
    from telethon.errors import SessionPasswordNeededError

    client = _build_client(config)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            if not phone_code_hash:
                raise TelegramSignInError(
                    "Login session expired — click Send code again, then enter the new code."
                )
            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError as error:
                if not password:
                    raise TelegramPasswordRequired(str(error)) from error
                await client.sign_in(password=password)
        if not await client.is_user_authorized():
            raise TelegramSignInError("Sign-in did not complete — try Send code again.")
        # region agent log
        agent_debug(
            "D",
            "telegram_sign_in.py:complete_login:done",
            "sign_in ok",
            {"session_path": str(config.session_path)},
        )
        # endregion
    finally:
        await client.disconnect()


async def interactive_cli_sign_in(config: TelegramSignInConfig) -> None:
    client = _build_client(config)
    try:
        await client.start(
            phone=lambda: input("Phone number (international, e.g. +79001234567): "),
            code_callback=lambda: input("Code from Telegram: "),
            password=lambda: getpass.getpass("Two-step verification password: "),
        )
        await client.get_entity(int(config.target_chat_id))
    finally:
        await client.disconnect()


def run_send_login_code(config: TelegramSignInConfig, phone: str) -> str | None:
    return asyncio.run(send_login_code(config, phone))


def run_complete_login(
    config: TelegramSignInConfig,
    phone: str,
    code: str,
    phone_code_hash: str | None,
    password: str | None = None,
) -> None:
    asyncio.run(complete_login(config, phone, code, phone_code_hash, password))


def run_interactive_cli_sign_in(config: TelegramSignInConfig) -> None:
    asyncio.run(interactive_cli_sign_in(config))
