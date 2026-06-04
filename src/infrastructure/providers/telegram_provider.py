import json
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from use_cases.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)
from use_cases.ports import StorageProviderPort


class TelegramProviderError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TelegramProviderV1(StorageProviderPort):
    bot_token: str
    base_url: str
    request_timeout_seconds: float = 30.0
    upload_timeout_seconds: float = 700.0

    def _api_url(self, method: str) -> str:
        return f"{self.base_url.rstrip('/')}/bot{self.bot_token}/{method}"

    def healthcheck(self) -> bool:
        try:
            payload = self._request_json("getMe", {})
        except Exception:
            return False
        return bool(payload.get("ok"))

    def upload_file(self, local_path: Path, remote_target: str, display_name: str) -> UploadResult:
        body, content_type = self._build_send_document_multipart(
            chat_id=remote_target,
            file_path=local_path,
            filename=display_name,
        )
        payload = self._post_json_body("sendDocument", body, content_type)
        result = payload["result"]
        document = result["document"]
        external_file_id = document["file_id"]
        external_message_id = str(result["message_id"])
        provider_download_ref = document.get("file_unique_id", external_file_id)
        provider_file_name = document.get("file_name", display_name)
        return UploadResult(
            provider_name="telegram",
            external_file_id=external_file_id,
            external_message_id=external_message_id,
            provider_download_ref=provider_download_ref,
            provider_file_name=provider_file_name,
        )

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        payload = self._request_json("getFile", {"file_id": external_file_id})
        result = payload["result"]
        file_path = result["file_path"]
        file_name = Path(file_path).name
        return ProviderFileInfo(
            provider_name="telegram",
            external_file_id=external_file_id,
            provider_download_ref=file_path,
            provider_file_name=file_name,
            size_bytes=int(result.get("file_size", 0)),
        )

    def download_file(
        self, file_info: ProviderFileInfo, destination_path: Path, resume: bool = False
    ) -> Path:
        file_url = (
            f"{self.base_url.rstrip('/')}/file/bot{self.bot_token}/"
            f"{file_info.provider_download_ref}"
        )
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "ab" if resume else "wb"
        req = request.Request(file_url, method="GET")
        with request.urlopen(req, timeout=self.request_timeout_seconds) as response:
            with destination_path.open(mode) as output_file:
                output_file.write(response.read())
        return destination_path

    def classify_error(self, error_value: Exception) -> ClassifiedProviderError:
        message = str(error_value).lower()
        if "retry after" in message or "flood" in message:
            retry_after = _extract_retry_after_seconds(message)
            return ClassifiedProviderError(
                category=ProviderErrorCategory.RATE_LIMITED,
                reason=str(error_value),
                retry_after_seconds=retry_after,
            )
        if "unauthorized" in message or "token" in message:
            return ClassifiedProviderError(
                category=ProviderErrorCategory.AUTH,
                reason=str(error_value),
            )
        if "forbidden" in message or "not enough rights" in message:
            return ClassifiedProviderError(
                category=ProviderErrorCategory.PERMISSION,
                reason=str(error_value),
            )
        if isinstance(error_value, TimeoutError | socket.timeout | error.URLError):
            return ClassifiedProviderError(
                category=ProviderErrorCategory.TRANSPORT,
                reason=str(error_value),
            )
        if isinstance(error_value, error.HTTPError) and 500 <= error_value.code < 600:
            return ClassifiedProviderError(
                category=ProviderErrorCategory.RETRYABLE,
                reason=str(error_value),
            )
        return ClassifiedProviderError(
            category=ProviderErrorCategory.UNKNOWN,
            reason=str(error_value),
        )

    def provider_limits(self) -> ProviderLimits:
        return ProviderLimits(
            max_upload_size_bytes=2_000_000_000,
            supports_resume_download=True,
            rate_limit_window_seconds=1,
            rate_limit_max_requests=30,
        )

    def _build_send_document_multipart(
        self,
        chat_id: str,
        file_path: Path,
        filename: str,
    ) -> tuple[bytes, str]:
        boundary = secrets.token_hex(16)
        crlf = b"\r\n"
        b_bound = boundary.encode("ascii")
        safe_filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
        file_bytes = file_path.read_bytes()
        parts: list[bytes] = []
        parts.append(b"--" + b_bound + crlf)
        parts.append(b'Content-Disposition: form-data; name="chat_id"' + crlf)
        parts.append(crlf)
        parts.append(chat_id.encode("utf-8") + crlf)

        parts.append(b"--" + b_bound + crlf)
        fn = safe_filename.encode("utf-8")
        parts.append(
            b'Content-Disposition: form-data; name="document"; filename="'
            + fn
            + b'"'
            + crlf
        )
        parts.append(b"Content-Type: application/octet-stream" + crlf)
        parts.append(crlf)
        parts.append(file_bytes + crlf)
        parts.append(b"--" + b_bound + b"--" + crlf)
        body = b"".join(parts)
        return body, f"multipart/form-data; boundary={boundary}"

    def _post_json_body(self, method: str, body: bytes, content_type: str) -> dict[str, Any]:
        req = request.Request(
            self._api_url(method),
            data=body,
            method="POST",
            headers={"Content-Type": content_type},
        )
        try:
            with request.urlopen(req, timeout=self.upload_timeout_seconds) as response:
                raw_body = response.read()
        except Exception as request_error:
            raise TelegramProviderError(str(request_error)) from request_error
        return self._parse_json_response(raw_body)

    def _request_json(self, method: str, payload: dict[str, str]) -> dict[str, Any]:
        encoded_payload = parse.urlencode(payload).encode()
        req = request.Request(
            self._api_url(method),
            data=encoded_payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                raw_body = response.read()
        except Exception as request_error:
            raise TelegramProviderError(str(request_error)) from request_error
        return self._parse_json_response(raw_body)

    def _parse_json_response(self, raw_body: bytes) -> dict[str, Any]:
        parsed = json.loads(raw_body.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise TelegramProviderError("Telegram API returned non-object JSON payload")
        if not parsed.get("ok", False):
            description = str(parsed.get("description", "Telegram API request failed"))
            raise TelegramProviderError(description)
        return parsed


def _extract_retry_after_seconds(message: str) -> int | None:
    marker = "retry after "
    if marker not in message:
        return None
    after = message.split(marker, maxsplit=1)[1]
    digits = "".join(ch for ch in after if ch.isdigit())
    if not digits:
        return None
    return int(digits)
