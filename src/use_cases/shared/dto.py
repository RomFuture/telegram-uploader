"""DTOs shared by use_cases ports and infrastructure provider adapters."""

from dataclasses import dataclass
from enum import Enum


class RestoreRefCapability(str, Enum):
    RESTORABLE = "restorable"
    UNSUPPORTED_LEGACY = "unsupported_legacy"
    UNSUPPORTED = "unsupported"


class ProviderErrorCategory(str, Enum):
    RETRYABLE = "retryable"
    FATAL = "fatal"
    RATE_LIMITED = "rate_limited"
    AUTH = "auth"
    PERMISSION = "permission"
    TRANSPORT = "transport"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class UploadResult:
    provider_name: str
    external_file_id: str
    external_message_id: str
    provider_download_ref: str
    provider_file_name: str


@dataclass(frozen=True, slots=True)
class ProviderFileInfo:
    provider_name: str
    external_file_id: str
    provider_download_ref: str
    provider_file_name: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ProviderLimits:
    max_upload_size_bytes: int
    supports_resume_download: bool
    rate_limit_window_seconds: int | None
    rate_limit_max_requests: int | None


@dataclass(frozen=True, slots=True)
class ClassifiedProviderError:
    category: ProviderErrorCategory
    reason: str
    retry_after_seconds: int | None = None
