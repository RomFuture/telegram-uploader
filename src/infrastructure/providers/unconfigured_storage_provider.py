"""Placeholder storage provider when Telegram credentials are not configured yet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)


class UnconfiguredProviderError(RuntimeError):
    pass


_CONFIGURE_MSG = (
    "Telegram is not configured. Open Settings → Client API, enter API id/hash and group id, "
    "then restart docker compose workers (telegram-uploader)."
)


@dataclass(frozen=True, slots=True)
class UnconfiguredStorageProvider:
    mode: str

    def healthcheck(self, remote_target: str) -> bool:
        return False

    def upload_file(self, local_path: Path, remote_target: str, display_name: str) -> UploadResult:
        raise UnconfiguredProviderError(_CONFIGURE_MSG)

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        raise UnconfiguredProviderError(_CONFIGURE_MSG)

    def download_file(
        self, file_info: ProviderFileInfo, destination_path: Path, resume: bool = False
    ) -> Path:
        raise UnconfiguredProviderError(_CONFIGURE_MSG)

    def classify_error(self, error: Exception) -> ClassifiedProviderError:
        return ClassifiedProviderError(
            category=ProviderErrorCategory.FATAL,
            reason=str(error),
        )

    def provider_limits(self) -> ProviderLimits:
        return ProviderLimits(
            max_upload_size_bytes=0,
            supports_resume_download=False,
            rate_limit_window_seconds=None,
            rate_limit_max_requests=None,
        )
