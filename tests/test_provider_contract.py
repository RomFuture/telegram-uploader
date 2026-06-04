from pathlib import Path

from use_cases.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)
from use_cases.ports import StorageProviderPort


class DummyProvider:
    def healthcheck(self) -> bool:
        return True

    def upload_file(self, local_path: Path, remote_target: str, display_name: str) -> UploadResult:
        return UploadResult(
            provider_name="dummy",
            external_file_id="file-id",
            external_message_id="msg-id",
            provider_download_ref="download-ref",
            provider_file_name=display_name,
        )

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        return ProviderFileInfo(
            provider_name="dummy",
            external_file_id=external_file_id,
            provider_download_ref="download-ref",
            provider_file_name="archive.001",
            size_bytes=123,
        )

    def download_file(
        self, file_info: ProviderFileInfo, destination_path: Path, resume: bool = False
    ) -> Path:
        return destination_path

    def classify_error(self, error: Exception) -> ClassifiedProviderError:
        return ClassifiedProviderError(category=ProviderErrorCategory.UNKNOWN, reason=str(error))

    def provider_limits(self) -> ProviderLimits:
        return ProviderLimits(
            max_upload_size_bytes=2_000_000_000,
            supports_resume_download=True,
            rate_limit_window_seconds=None,
            rate_limit_max_requests=None,
        )


def test_dummy_provider_matches_storage_provider_port() -> None:
    provider = DummyProvider()
    assert isinstance(provider, StorageProviderPort)
