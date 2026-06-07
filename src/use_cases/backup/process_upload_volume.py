from dataclasses import dataclass, replace
from uuid import UUID

from use_cases.domain.errors import ArchiveVolumeNotFound, SourceItemNotFound
from use_cases.domain.mappers import (
    archive_volume_record_to_domain,
    domain_to_archive_volume_record,
    domain_to_source_item_record,
    source_item_record_to_domain,
)
from use_cases.domain.models import ArchiveVolumeStatus, SourceItemStatus
from use_cases.domain.transitions import ensure_archive_volume_status
from use_cases.ports.storage_provider import StorageProviderPort
from use_cases.ports.task_queue import TaskQueuePort
from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.repositories.source_item import SourceItemRepository


@dataclass(frozen=True, slots=True)
class ProcessUploadVolumeUseCase:
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    task_queue: TaskQueuePort
    remote_target: str

    def execute(self, archive_volume_id: UUID) -> None:
        volume_record = self.archive_volumes.get(archive_volume_id)
        if volume_record is None:
            raise ArchiveVolumeNotFound

        volume = archive_volume_record_to_domain(volume_record)
        ensure_archive_volume_status(volume.status, ArchiveVolumeStatus.CREATED)

        uploading = replace(volume, status=ArchiveVolumeStatus.UPLOADING)
        self.archive_volumes.update(domain_to_archive_volume_record(uploading))

        upload_result = self.storage_provider.upload_file(
            local_path=uploading.local_path,
            remote_target=self.remote_target,
            display_name=uploading.file_name,
        )

        uploaded = replace(
            uploading,
            status=ArchiveVolumeStatus.UPLOADED,
            external_file_id=upload_result.external_file_id,
            external_message_id=upload_result.external_message_id,
            provider_download_ref=upload_result.provider_download_ref,
        )
        self.archive_volumes.update(domain_to_archive_volume_record(uploaded))
        self.task_queue.enqueue_cleanup(uploaded.id)

        item_record = self.source_items.get(uploaded.source_item_id)
        if item_record is None:
            raise SourceItemNotFound
        item = source_item_record_to_domain(item_record)
        if item.status == SourceItemStatus.UPLOADING:
            cleanup_ready = replace(item, status=SourceItemStatus.CLEANUP)
            self.source_items.update(domain_to_source_item_record(cleanup_ready))
