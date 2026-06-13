from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

from infrastructure.worker.tasks import (
    archive_volume,
    cleanup_volume,
    restore_volume,
    upload_volume,
)


@patch("infrastructure.worker.tasks.get_celery_entrypoint")
def test_archive_volume_calls_celery_entrypoint(mock_entrypoint_factory: MagicMock) -> None:
    entrypoint = MagicMock()
    mock_entrypoint_factory.return_value = entrypoint
    source_item_id = UUID("00000000-0000-0000-0000-000000000001")

    result = archive_volume.run(str(source_item_id))

    entrypoint.process_archive.assert_called_once_with(source_item_id)
    assert result["stage"] == "archive"


@patch("infrastructure.worker.tasks.get_celery_entrypoint")
def test_upload_volume_calls_celery_entrypoint(mock_entrypoint_factory: MagicMock) -> None:
    entrypoint = MagicMock()
    mock_entrypoint_factory.return_value = entrypoint
    volume_id = UUID("00000000-0000-0000-0000-000000000002")

    result = upload_volume.run(str(volume_id))

    entrypoint.process_upload.assert_called_once_with(volume_id)
    assert result["stage"] == "upload"


@patch("infrastructure.worker.tasks.get_celery_entrypoint")
def test_cleanup_volume_calls_celery_entrypoint(mock_entrypoint_factory: MagicMock) -> None:
    entrypoint = MagicMock()
    mock_entrypoint_factory.return_value = entrypoint
    volume_id = UUID("00000000-0000-0000-0000-000000000003")

    result = cleanup_volume.run(str(volume_id))

    entrypoint.process_cleanup.assert_called_once_with(volume_id)
    assert result["stage"] == "cleanup"


@patch("infrastructure.worker.tasks.get_celery_entrypoint")
def test_restore_volume_calls_celery_entrypoint(mock_entrypoint_factory: MagicMock) -> None:
    entrypoint = MagicMock()
    entrypoint.process_restore_volume.return_value = Path("/tmp/vol.7z.001")
    mock_entrypoint_factory.return_value = entrypoint
    volume_id = UUID("00000000-0000-0000-0000-000000000004")

    result = restore_volume.run(str(volume_id))

    entrypoint.process_restore_volume.assert_called_once_with(volume_id)
    assert result["stage"] == "restore"
    assert result["path"] == "/tmp/vol.7z.001"
