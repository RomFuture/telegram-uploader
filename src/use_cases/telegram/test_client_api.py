"""Test Telegram Client API connectivity and upload."""

from dataclasses import dataclass
from pathlib import Path

from use_cases.shared.ports.storage_provider import StorageProviderPort


@dataclass(frozen=True, slots=True)
class TestClientApiResult:
    ok: bool
    stage: str
    message: str
    provider_ref: str | None = None


@dataclass(frozen=True, slots=True)
class TestClientApiUseCase:
    test_file_path: Path

    def execute(
        self,
        provider: StorageProviderPort,
        target_chat_id: str,
    ) -> TestClientApiResult:
        if not self.test_file_path.is_file():
            return TestClientApiResult(
                ok=False,
                stage="test_file",
                message=f"Test file missing in repo: {self.test_file_path}",
            )

        try:
            if not provider.healthcheck(target_chat_id):
                return TestClientApiResult(
                    ok=False,
                    stage="healthcheck",
                    message=(
                        "Cannot access the target group with this session.\n"
                        "Check TELEGRAM_TARGET_CHAT_ID, group membership, and chat id format."
                    ),
                )
        except Exception as error:
            return TestClientApiResult(
                ok=False,
                stage="healthcheck",
                message=f"Healthcheck failed: {error}",
            )

        try:
            upload = provider.upload_file(
                self.test_file_path,
                target_chat_id,
                "client-api-test.md",
            )
        except Exception as error:
            return TestClientApiResult(
                ok=False,
                stage="upload",
                message=f"Upload failed: {error}",
            )

        return TestClientApiResult(
            ok=True,
            stage="upload",
            message=(
                f"Uploaded test file to chat {target_chat_id}.\n"
                f"Ref: {upload.provider_download_ref}"
            ),
            provider_ref=upload.provider_download_ref,
        )
