"""Telegram Client API sign-in (Telethon) — shared by CLI and GUI."""

from __future__ import annotations

import asyncio
import getpass
import os
import threading
from dataclasses import dataclass
from pathlib import Path

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


async def send_login_code(config: TelegramSignInConfig, phone: str) -> None:
    from telethon import TelegramClient

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
            "has_dollar_home": "${HOME}" in str(config.session_path),
            "has_tilde": str(config.session_path).startswith("~"),
        },
    )
    # endregion

    try:
        config.session_path.parent.mkdir(parents=True, exist_ok=True)
        # region agent log
        agent_debug(
            "B",
            "telegram_sign_in.py:send_login_code:mkdir",
            "mkdir succeeded",
            path_diagnostics(config.session_path),
        )
        # endregion
    except OSError as error:
        # region agent log
        agent_debug(
            "B",
            "telegram_sign_in.py:send_login_code:mkdir",
            "mkdir failed",
            {**path_diagnostics(config.session_path), "error": str(error)},
        )
        # endregion
        raise

    client = TelegramClient(str(config.session_path), config.api_id, config.api_hash)
    try:
        async with client:
            await client.connect()
            if await client.is_user_authorized():
                return
            await client.send_code_request(phone)
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


async def complete_login(
    config: TelegramSignInConfig,
    phone: str,
    code: str,
    password: str | None = None,
) -> None:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

    config.session_path.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(config.session_path), config.api_id, config.api_hash)
    async with client:
        await client.connect()
        if not await client.is_user_authorized():
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError as error:
                if not password:
                    raise TelegramPasswordRequired(str(error)) from error
                await client.sign_in(password=password)
        await client.get_entity(int(config.target_chat_id))


async def interactive_cli_sign_in(config: TelegramSignInConfig) -> None:
    from telethon import TelegramClient

    config.session_path.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(config.session_path), config.api_id, config.api_hash)
    async with client:
        await client.start(
            phone=lambda: input("Phone number (international, e.g. +79001234567): "),
            code_callback=lambda: input("Code from Telegram: "),
            password=lambda: getpass.getpass("Two-step verification password: "),
        )
        await client.get_entity(int(config.target_chat_id))


def run_send_login_code(config: TelegramSignInConfig, phone: str) -> None:
    asyncio.run(send_login_code(config, phone))


def run_complete_login(
    config: TelegramSignInConfig,
    phone: str,
    code: str,
    password: str | None = None,
) -> None:
    asyncio.run(complete_login(config, phone, code, password))


def run_interactive_cli_sign_in(config: TelegramSignInConfig) -> None:
    asyncio.run(interactive_cli_sign_in(config))
