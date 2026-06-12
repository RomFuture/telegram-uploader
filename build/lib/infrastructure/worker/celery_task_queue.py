from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CeleryTaskQueue:
    def enqueue_archive(self, source_item_id: UUID) -> None:
        from infrastructure.worker.tasks import archive_volume

        archive_volume.delay(str(source_item_id))

    def enqueue_upload(self, archive_volume_id: UUID) -> None:
        from infrastructure.worker.tasks import upload_volume

        upload_volume.delay(str(archive_volume_id))

    def enqueue_cleanup(self, archive_volume_id: UUID) -> None:
        from infrastructure.worker.tasks import cleanup_volume

        cleanup_volume.delay(str(archive_volume_id))

    def enqueue_restore(self, archive_volume_id: UUID) -> None:
        from infrastructure.worker.tasks import restore_volume

        restore_volume.delay(str(archive_volume_id))
