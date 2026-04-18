from infrastructure.worker.celery_app import (
    QUEUE_ARCHIVE,
    QUEUE_CLEANUP,
    QUEUE_UPLOAD,
    celery_app,
)


def test_celery_task_routes_map_stages_to_expected_queues() -> None:
    routes = celery_app.conf.task_routes
    assert routes is not None
    assert routes["infrastructure.worker.tasks.archive_volume"]["queue"] == QUEUE_ARCHIVE
    assert routes["infrastructure.worker.tasks.upload_volume"]["queue"] == QUEUE_UPLOAD
    assert routes["infrastructure.worker.tasks.cleanup_volume"]["queue"] == QUEUE_CLEANUP


def test_celery_default_queue_is_archive() -> None:
    assert celery_app.conf.task_default_queue == QUEUE_ARCHIVE
