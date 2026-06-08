from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from infrastructure.worker.tasks import (
    archive_volume,
    cleanup_volume,
    restore_volume,
    upload_volume,
)


@patch("infrastructure.worker.tasks._facade")
def test_archive_volume_calls_facade(mock_facade_factory: MagicMock) -> None:
    facade = MagicMock()
    mock_facade_factory.return_value = facade
    source_item_id = uuid4()

    result = archive_volume.run(str(source_item_id))

    facade.process_archive_volume.assert_called_once_with(source_item_id)
    assert result["status"] == "done"
    assert result["stage"] == "archive"
    assert "stub" not in result["status"]


@patch("infrastructure.worker.tasks._facade")
def test_upload_volume_calls_facade(mock_facade_factory: MagicMock) -> None:
    facade = MagicMock()
    mock_facade_factory.return_value = facade
    volume_id = uuid4()

    result = upload_volume.run(str(volume_id))

    facade.process_upload_volume.assert_called_once_with(volume_id)
    assert result["status"] == "done"


@patch("infrastructure.worker.tasks._facade")
def test_cleanup_volume_calls_facade(mock_facade_factory: MagicMock) -> None:
    facade = MagicMock()
    mock_facade_factory.return_value = facade
    volume_id = uuid4()

    result = cleanup_volume.run(str(volume_id))

    facade.process_cleanup_volume.assert_called_once_with(volume_id)
    assert result["status"] == "done"


@patch("infrastructure.worker.tasks._facade")
def test_restore_volume_calls_facade(mock_facade_factory: MagicMock) -> None:
    facade = MagicMock()
    facade.process_restore_volume.return_value = Path("/tmp/vol.7z.001")
    mock_facade_factory.return_value = facade
    volume_id = uuid4()

    result = restore_volume.run(str(volume_id))

    facade.process_restore_volume.assert_called_once_with(volume_id)
    assert result["status"] == "done"
    assert result["stage"] == "restore"
