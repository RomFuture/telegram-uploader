"""Verify storage provider connectivity via upload and download round-trip."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from use_cases.shared.ports.storage_provider import StorageProviderPort


@dataclass(frozen=True, slots=True)
class VerifyStorageProviderResult:
    ok: bool
    stage: str
    message: str
    provider_ref: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyStorageProviderUseCase:
    test_file_path: Path

    def execute(self, provider: StorageProviderPort) -> VerifyStorageProviderResult:
        if not self.test_file_path.is_file():
            return VerifyStorageProviderResult(
                ok=False,
                stage="test_file",
                message=f"Test file missing in repo: {self.test_file_path}",
            )

        try:
            if not provider.healthcheck():
                return VerifyStorageProviderResult(
                    ok=False,
                    stage="healthcheck",
                    message=(
                        "Cannot access the target group with this session.\n"
                        "Check TELEGRAM_TARGET_CHAT_ID, group membership, and chat id format."
                    ),
                )
        except Exception as error:
            return VerifyStorageProviderResult(
                ok=False,
                stage="healthcheck",
                message=f"Healthcheck failed: {error}",
            )

        try:
            upload = provider.upload_file(
                self.test_file_path,
                "client-api-test.md",
            )
        except Exception as error:
            return VerifyStorageProviderResult(
                ok=False,
                stage="upload",
                message=f"Upload failed: {error}",
            )

        provider_ref = upload.provider_download_ref
        try:
            file_info = provider.get_file_info(provider_ref)
        except Exception as error:
            return VerifyStorageProviderResult(
                ok=False,
                stage="download",
                message=f"Could not resolve uploaded file ref: {error}",
                provider_ref=provider_ref,
            )

        original = self.test_file_path.read_bytes()
        downloaded: bytes
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                destination = Path(tmp_dir) / "client-api-test-download.md"
                provider.download_file(file_info, destination)
                downloaded = destination.read_bytes()
        except Exception as error:
            return VerifyStorageProviderResult(
                ok=False,
                stage="download",
                message=f"Download failed: {error}",
                provider_ref=provider_ref,
            )

        if original != downloaded:
            return VerifyStorageProviderResult(
                ok=False,
                stage="verify",
                message=(
                    f"Downloaded bytes do not match the uploaded test file.\nRef: {provider_ref}"
                ),
                provider_ref=provider_ref,
            )

        return VerifyStorageProviderResult(
            ok=True,
            stage="verify",
            message=(f"Upload and download OK for configured target.\nRef: {provider_ref}"),
            provider_ref=provider_ref,
        )
