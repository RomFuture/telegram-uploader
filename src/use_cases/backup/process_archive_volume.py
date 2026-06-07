from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.mappers import domain_to_archive_volume_record, domain_to_source_item_record
from use_cases.ports.archive_service import ArchiveServicePort
from use_cases.ports.task_queue import TaskQueuePort
from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.repositories.session import SessionRepository
from use_cases.repositories.source_item import SourceItemRepository


@dataclass(frozen=True, slots=True)
class ProcessArchiveVolumeUseCase:
    sessions: SessionRepository
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository
    archive_service: ArchiveServicePort
    task_queue: TaskQueuePort
    archive_cache_dir: Path

    def execute(self, source_item_id: UUID) -> None:
        item = self.source_items.require(source_item_id)
        domain.prepare_source_item_for_archive(item)

        session = self.sessions.require(item.session_id)

        archiving = domain.mark_source_item(item, status=domain.SourceItemStatus.ARCHIVING)
        self.source_items.update(domain_to_source_item_record(archiving))

        result = self.archive_service.archive(
            source_path=item.source_path,
            output_dir=self.archive_cache_dir,
            display_name=item.display_name,
            encryption_key=session.encryption_key,
            source_item_id=str(item.id),
        )

        for part in result.volumes:
            volume = domain.create_archive_volume(
                source_item_id=item.id,
                file_name=part.outgoing_file_name,
                local_path=part.outgoing_path,
                part_number=part.part_number,
            )
            self.archive_volumes.add(domain_to_archive_volume_record(volume))
            self.task_queue.enqueue_upload(volume.id)

        uploading = domain.mark_source_item(archiving, status=domain.SourceItemStatus.UPLOADING)
        self.source_items.update(domain_to_source_item_record(uploading))
