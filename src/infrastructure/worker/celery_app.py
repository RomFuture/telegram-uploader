from celery import Celery

from infrastructure.config import load_config

QUEUE_ARCHIVE = "archive"
QUEUE_UPLOAD = "upload"
QUEUE_CLEANUP = "cleanup"
QUEUE_RESTORE = "restore"


def _make_celery() -> Celery:
    cfg = load_config()
    app = Celery(
        "telegram_uploader",
        broker=cfg.redis_url,
        backend=cfg.redis_url,
        include=["infrastructure.worker.tasks"],
    )
    app.conf.task_routes = {
        "infrastructure.worker.tasks.archive_volume": {"queue": QUEUE_ARCHIVE},
        "infrastructure.worker.tasks.upload_volume": {"queue": QUEUE_UPLOAD},
        "infrastructure.worker.tasks.cleanup_volume": {"queue": QUEUE_CLEANUP},
        "infrastructure.worker.tasks.restore_volume": {"queue": QUEUE_RESTORE},
    }
    app.conf.task_default_queue = QUEUE_ARCHIVE
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    return app


celery_app = _make_celery()
