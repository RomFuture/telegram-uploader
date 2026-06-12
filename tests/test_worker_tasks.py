from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

from infrastructure.worker.tasks import (
    archive_volume,
    cleanup_volume,
    restore_volume,
    upload_volume,
)


@patch("infrastructure.worker.tasks._worker_api")
def test_archive_volume_calls_worker_api(mock_api_factory: MagicMock) -> None:
    api = MagicMock()
    mock_api_factory.return_value = api
    source_item_id = UUID("00000000-0000-0000-0000-000000000001")

    result = archive_volume.run(str(source_item_id))

    api.process_archive.assert_called_once_with(source_item_id)
    assert result["stage"] == "archive"


@patch("infrastructure.worker.tasks._worker_api")
def test_upload_volume_calls_worker_api(mock_api_factory: MagicMock) -> None:
    api = MagicMock()
    mock_api_factory.return_value = api
    volume_id = UUID("00000000-0000-0000-0000-000000000002")

    result = upload_volume.run(str(volume_id))

    api.process_upload.assert_called_once_with(volume_id)
    assert result["stage"] == "upload"


@patch("infrastructure.worker.tasks._worker_api")
def test_cleanup_volume_calls_worker_api(mock_api_factory: MagicMock) -> None:
    api = MagicMock()
    mock_api_factory.return_value = api
    volume_id = UUID("00000000-0000-0000-0000-000000000003")

    result = cleanup_volume.run(str(volume_id))

    api.process_cleanup.assert_called_once_with(volume_id)
    assert result["stage"] == "cleanup"


@patch("infrastructure.worker.tasks._worker_api")
def test_restore_volume_calls_worker_api(mock_api_factory: MagicMock) -> None:
    api = MagicMock()
    api.process_restore_volume.return_value = Path("/tmp/vol.7z.001")
    mock_api_factory.return_value = api
    volume_id = UUID("00000000-0000-0000-0000-000000000004")

    result = restore_volume.run(str(volume_id))

    api.process_restore_volume.assert_called_once_with(volume_id)
    assert result["stage"] == "restore"
    assert result["path"] == "/tmp/vol.7z.001"
