from pathlib import Path
from typing import Protocol, runtime_checkable

from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)


@runtime_checkable
class StorageProviderPort(Protocol):
    def healthcheck(self, remote_target: str) -> bool:
        """Return True when provider is reachable and target is accessible."""

    def upload_file(self, local_path: Path, remote_target: str, display_name: str) -> UploadResult:
        """Upload a file and return provider identifiers needed for restore."""

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        """Fetch provider metadata required to download a file."""

    def download_file(
        self, file_info: ProviderFileInfo, destination_path: Path, resume: bool = False
    ) -> Path:
        """Download or resume download to destination path."""

    def classify_error(self, error: Exception) -> ClassifiedProviderError:
        """Map raw provider exception into application-level error category."""

    def provider_limits(self) -> ProviderLimits:
        """Return declared provider limits (size/rate/download capabilities)."""
