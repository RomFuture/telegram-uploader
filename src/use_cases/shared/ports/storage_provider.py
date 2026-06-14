from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderFileInfo,
    ProviderLimits,
    RestoreRefCapability,
    UploadResult,
)


@runtime_checkable
class StorageProviderPort(Protocol):
    def healthcheck(self) -> bool:
        """Return True when provider is reachable and configured target is accessible."""

    def upload_file(self, local_path: Path, display_name: str) -> UploadResult:
        """Upload a file and return provider identifiers needed for restore."""

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        """Fetch provider metadata required to download a file."""

    def download_file(
        self,
        file_info: ProviderFileInfo,
        destination_path: Path,
        resume: bool = False,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download or resume download to destination path."""

    def classify_error(self, error: Exception) -> ClassifiedProviderError:
        """Map raw provider exception into application-level error category."""

    def assess_restore_ref(self, provider_download_ref: str) -> RestoreRefCapability:
        """Classify whether this provider can download a file by the stored ref."""

    def resolve_restore_ref(self, provider_download_ref: str) -> str:
        """Return ref suitable for get_file_info/download when restorable."""

    def provider_limits(self) -> ProviderLimits:
        """Return declared provider limits (size/rate/download capabilities)."""
