from infrastructure.archive.seven_zip_service import _format_extract_error


def test_format_extract_error_permission_denied() -> None:
    message = _format_extract_error(
        "/opt/telegram-uploader/src/testtest",
        "ERROR: Cannot open output file : errno=13 : Permission denied : file.mkv",
    )
    assert "Permission denied" in message
    assert "~/Restored/" in message


def test_format_extract_error_passthrough() -> None:
    detail = "7z extract failed: wrong password"
    assert _format_extract_error("/tmp/out", detail) == f"7z extract failed: {detail}"
