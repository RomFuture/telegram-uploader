from unittest.mock import MagicMock, patch
from uuid import uuid4

from infrastructure.worker.celery_task_queue import CeleryTaskQueue


@patch("infrastructure.worker.tasks.archive_volume")
def test_enqueue_archive_calls_delay(mock_archive_volume: MagicMock) -> None:
    source_item_id = uuid4()
    CeleryTaskQueue().enqueue_archive(source_item_id)
    mock_archive_volume.delay.assert_called_once_with(str(source_item_id))


@patch("infrastructure.worker.tasks.upload_volume")
def test_enqueue_upload_calls_delay(mock_upload_volume: MagicMock) -> None:
    volume_id = uuid4()
    CeleryTaskQueue().enqueue_upload(volume_id)
    mock_upload_volume.delay.assert_called_once_with(str(volume_id))


@patch("infrastructure.worker.tasks.cleanup_volume")
def test_enqueue_cleanup_calls_delay(mock_cleanup_volume: MagicMock) -> None:
    volume_id = uuid4()
    CeleryTaskQueue().enqueue_cleanup(volume_id)
    mock_cleanup_volume.delay.assert_called_once_with(str(volume_id))


@patch("infrastructure.worker.tasks.restore_volume")
def test_enqueue_restore_calls_delay(mock_restore_volume: MagicMock) -> None:
    volume_id = uuid4()
    CeleryTaskQueue().enqueue_restore(volume_id)
    mock_restore_volume.delay.assert_called_once_with(str(volume_id))
