from pathlib import Path

from infrastructure.providers.telegram_provider import TelegramProviderV1


def test_send_document_multipart_includes_chat_and_file_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "chunk.7z.001"
    file_path.write_bytes(b"hello-bytes")
    provider = TelegramProviderV1(
        bot_token="token",
        base_url="http://localhost:8081",
        remote_target="-1001",
    )
    body, content_type = provider._build_send_document_multipart(
        chat_id="-100123",
        file_path=file_path,
        filename="abc.part0001.7z.001",
    )
    assert b'name="chat_id"' in body
    assert b"-100123" in body
    assert b'name="document"' in body
    assert b"hello-bytes" in body
    assert content_type.startswith("multipart/form-data; boundary=")
