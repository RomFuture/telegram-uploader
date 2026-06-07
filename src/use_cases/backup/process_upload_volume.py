from dataclasses import dataclass
from uuid import UUID

import domain as domain
from use_cases.mappers import domain_to_archive_volume_record, domain_to_source_item_record
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
        volume = self.archive_volumes.require(archive_volume_id)
        domain.prepare_archive_volume_for_upload(volume)

        uploading = domain.mark_archive_volume(volume, status=domain.ArchiveVolumeStatus.UPLOADING)
        self.archive_volumes.update(domain_to_archive_volume_record(uploading))

        upload_result = self.storage_provider.upload_file(
            local_path=uploading.local_path,
            remote_target=self.remote_target,
            display_name=uploading.file_name,
        )

        uploaded = domain.mark_archive_volume_uploaded(
            uploading,
            external_file_id=upload_result.external_file_id,
            external_message_id=upload_result.external_message_id,
            provider_download_ref=upload_result.provider_download_ref,
        )
        self.archive_volumes.update(domain_to_archive_volume_record(uploaded))
        self.task_queue.enqueue_cleanup(uploaded.id)

        item = self.source_items.require(uploaded.source_item_id)
        if domain.is_source_item(item, status=domain.SourceItemStatus.UPLOADING):
            cleanup_ready = domain.mark_source_item(item, status=domain.SourceItemStatus.CLEANUP)
            self.source_items.update(domain_to_source_item_record(cleanup_ready))
