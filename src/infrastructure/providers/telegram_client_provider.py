"""Telegram Client API (MTProto) storage provider via Telethon."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib import error

from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)

CLIENT_REF_PREFIX = "client"


class TelegramClientProviderError(Exception):
    pass


def build_client_download_ref(chat_id: str, message_id: int, document_id: int) -> str:
    return f"{CLIENT_REF_PREFIX}:{chat_id}:{message_id}:{document_id}"


def parse_client_download_ref(ref: str) -> tuple[str, int, int]:
    parts = ref.split(":")
    if len(parts) != 4 or parts[0] != CLIENT_REF_PREFIX:
        raise TelegramClientProviderError(f"Invalid client download ref: {ref}")
    return parts[1], int(parts[2]), int(parts[3])



def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


@dataclass(frozen=True, slots=True)
class TelegramClientProvider:
    api_id: int
    api_hash: str
    session_path: Path
    request_timeout_seconds: float = 60.0

    def healthcheck(self, remote_target: str) -> bool:
        try:
            return bool(_run_async(self._healthcheck_async(remote_target)))
        except Exception:
            return False

    async def _healthcheck_async(self, remote_target: str) -> bool:
        client = self._build_client()
        async with client:
            await client.get_entity(int(remote_target))
        return True

    def upload_file(self, local_path: Path, remote_target: str, display_name: str) -> UploadResult:
        return cast(
            UploadResult,
            _run_async(self._upload_async(local_path, remote_target, display_name)),
        )

    async def _upload_async(
        self, local_path: Path, remote_target: str, display_name: str
    ) -> UploadResult:
        client = self._build_client()
        async with client:
            entity = await client.get_entity(int(remote_target))
            message = await client.send_file(
                entity,
                str(local_path),
                caption=display_name,
                force_document=True,
            )
            if message.document is None:
                raise TelegramClientProviderError("Uploaded message has no document")
            document = message.document
            document_id = int(document.id)
            provider_ref = build_client_download_ref(remote_target, int(message.id), document_id)
            file_name = getattr(document, "file_name", None) or display_name
            return UploadResult(
                provider_name="telegram_client",
                external_file_id=str(document_id),
                external_message_id=str(message.id),
                provider_download_ref=provider_ref,
                provider_file_name=str(file_name),
            )

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        if external_file_id.startswith(f"{CLIENT_REF_PREFIX}:"):
            chat_id, message_id, document_id = parse_client_download_ref(external_file_id)
            return ProviderFileInfo(
                provider_name="telegram_client",
                external_file_id=str(document_id),
                provider_download_ref=external_file_id,
                provider_file_name=f"volume-{document_id}",
                size_bytes=0,
            )
        return cast(ProviderFileInfo, _run_async(self._get_file_info_async(external_file_id)))

    async def _get_file_info_async(self, ref: str) -> ProviderFileInfo:
        chat_id, message_id, document_id = parse_client_download_ref(ref)
        client = self._build_client()
        async with client:
            message = await client.get_messages(int(chat_id), ids=message_id)
            if message is None or message.document is None:
                raise TelegramClientProviderError(
                    f"Message {message_id} not found in chat {chat_id}"
                )
            document = message.document
            file_name = getattr(document, "file_name", None) or f"volume-{document_id}"
            size_bytes = int(getattr(document, "size", 0) or 0)
            provider_ref = build_client_download_ref(chat_id, message_id, int(document.id))
            return ProviderFileInfo(
                provider_name="telegram_client",
                external_file_id=str(document.id),
                provider_download_ref=provider_ref,
                provider_file_name=str(file_name),
                size_bytes=size_bytes,
            )

    def download_file(
        self, file_info: ProviderFileInfo, destination_path: Path, resume: bool = False
    ) -> Path:
        if resume:
            raise TelegramClientProviderError(
                "Resume download is not supported for client provider"
            )
        return cast(Path, _run_async(self._download_async(file_info, destination_path)))

    async def _download_async(self, file_info: ProviderFileInfo, destination_path: Path) -> Path:
        chat_id, message_id, _document_id = parse_client_download_ref(
            file_info.provider_download_ref
        )
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        client = self._build_client()
        async with client:
            message = await client.get_messages(int(chat_id), ids=message_id)
            if message is None:
                raise TelegramClientProviderError(
                    f"Message {message_id} not found in chat {chat_id}"
                )
            downloaded = await client.download_media(message, file=str(destination_path))
            if downloaded is None:
                raise TelegramClientProviderError(
                    f"Download failed for message {message_id} in chat {chat_id}"
                )
        return destination_path

    def classify_error(self, error_value: Exception) -> ClassifiedProviderError:
        message = str(error_value).lower()
        if "flood" in message or "wait" in message:
            return ClassifiedProviderError(
                category=ProviderErrorCategory.RATE_LIMITED,
                reason=str(error_value),
            )
        if "auth" in message or "session" in message or "unauthorized" in message:
            return ClassifiedProviderError(
                category=ProviderErrorCategory.AUTH,
                reason=str(error_value),
            )
        if "forbidden" in message or "not enough rights" in message or "permission" in message:
            return ClassifiedProviderError(
                category=ProviderErrorCategory.PERMISSION,
                reason=str(error_value),
            )
        if isinstance(error_value, TimeoutError | socket.timeout | error.URLError):
            return ClassifiedProviderError(
                category=ProviderErrorCategory.TRANSPORT,
                reason=str(error_value),
            )
        return ClassifiedProviderError(
            category=ProviderErrorCategory.UNKNOWN,
            reason=str(error_value),
        )

    def provider_limits(self) -> ProviderLimits:
        return ProviderLimits(
            max_upload_size_bytes=2_000_000_000,
            supports_resume_download=False,
            rate_limit_window_seconds=1,
            rate_limit_max_requests=20,
        )

    def _build_client(self) -> Any:
        from telethon import TelegramClient

        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        return TelegramClient(
            str(self.session_path),
            self.api_id,
            self.api_hash,
            timeout=self.request_timeout_seconds,
        )
