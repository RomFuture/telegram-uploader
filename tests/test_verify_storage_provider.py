from pathlib import Path

from tests.fakes.ports import FakeStorageProvider
from use_cases.telegram.verify_storage_provider import VerifyStorageProviderUseCase


def test_verify_storage_provider_upload_download_roundtrip(tmp_path: Path) -> None:
    test_file = tmp_path / "readme.md"
    test_file.write_text("# test", encoding="utf-8")
    provider = FakeStorageProvider()
    use_case = VerifyStorageProviderUseCase(test_file_path=test_file)

    result = use_case.execute(provider)

    assert result.ok is True
    assert result.stage == "verify"
    assert result.provider_ref is not None
    assert result.provider_ref.startswith("client:")
    assert "client-api-test.md" in provider.uploaded_display_names
    assert len(provider.downloaded_files) == 1


def test_verify_storage_provider_reports_missing_test_file() -> None:
    use_case = VerifyStorageProviderUseCase(test_file_path=Path("/nonexistent/readme.md"))

    result = use_case.execute(FakeStorageProvider())

    assert result.ok is False
    assert result.stage == "test_file"


def test_verify_storage_provider_reports_healthcheck_failure(tmp_path: Path) -> None:
    test_file = tmp_path / "readme.md"
    test_file.write_text("# test", encoding="utf-8")

    class FailingProvider(FakeStorageProvider):
        def healthcheck(self) -> bool:
            return False

    result = VerifyStorageProviderUseCase(test_file_path=test_file).execute(
        FailingProvider(),
    )

    assert result.ok is False
    assert result.stage == "healthcheck"


def test_verify_storage_provider_reports_download_mismatch(tmp_path: Path) -> None:
    test_file = tmp_path / "readme.md"
    test_file.write_text("# test", encoding="utf-8")

    class MismatchProvider(FakeStorageProvider):
        def download_file(
            self,
            file_info,
            destination_path: Path,
            resume: bool = False,
            *,
            on_progress=None,
        ) -> Path:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(b"wrong-bytes")
            return destination_path

    result = VerifyStorageProviderUseCase(test_file_path=test_file).execute(
        MismatchProvider(),
    )

    assert result.ok is False
    assert result.stage == "verify"
