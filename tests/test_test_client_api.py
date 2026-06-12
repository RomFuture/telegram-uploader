from pathlib import Path

from tests.fakes.ports import FakeStorageProvider
from use_cases.telegram.test_client_api import TestClientApiUseCase


def test_test_client_api_uploads_readme(tmp_path: Path) -> None:
    test_file = tmp_path / "readme.md"
    test_file.write_text("# test", encoding="utf-8")
    provider = FakeStorageProvider()
    use_case = TestClientApiUseCase(test_file_path=test_file)

    result = use_case.execute(provider, "-1001")

    assert result.ok is True
    assert result.stage == "upload"
    assert "client-api-test.md" in provider.uploaded_display_names


def test_test_client_api_reports_missing_test_file() -> None:
    use_case = TestClientApiUseCase(test_file_path=Path("/nonexistent/readme.md"))

    result = use_case.execute(FakeStorageProvider(), "-1001")

    assert result.ok is False
    assert result.stage == "test_file"


def test_test_client_api_reports_healthcheck_failure(tmp_path: Path) -> None:
    test_file = tmp_path / "readme.md"
    test_file.write_text("# test", encoding="utf-8")

    class FailingProvider(FakeStorageProvider):
        def healthcheck(self, remote_target: str) -> bool:
            return False

    result = TestClientApiUseCase(test_file_path=test_file).execute(
        FailingProvider(),
        "-1001",
    )

    assert result.ok is False
    assert result.stage == "healthcheck"
