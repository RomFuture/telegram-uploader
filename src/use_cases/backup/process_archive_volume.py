from dataclasses import dataclass, replace
from pathlib import Path
from uuid import UUID

from use_cases.domain.errors import SessionNotFound, SourceItemNotFound
from use_cases.domain.factories import archive_volume_create
from use_cases.domain.mappers import (
    domain_to_archive_volume_record,
    domain_to_source_item_record,
    session_record_to_domain,
    source_item_record_to_domain,
)
from use_cases.domain.models import SourceItemStatus
from use_cases.domain.transitions import ensure_source_item_status
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
        item_record = self.source_items.get(source_item_id)
        if item_record is None:
            raise SourceItemNotFound

        item = source_item_record_to_domain(item_record)
        ensure_source_item_status(item.status, SourceItemStatus.QUEUED)

        session_record = self.sessions.get(item.session_id)
        if session_record is None:
            raise SessionNotFound
        session = session_record_to_domain(session_record)

        archiving = replace(item, status=SourceItemStatus.ARCHIVING)
        self.source_items.update(domain_to_source_item_record(archiving))

        result = self.archive_service.archive(
            source_path=item.source_path,
            output_dir=self.archive_cache_dir,
            display_name=item.display_name,
            encryption_key=session.encryption_key,
            source_item_id=str(item.id),
        )

        for part in result.volumes:
            volume = archive_volume_create(
                source_item_id=item.id,
                file_name=part.outgoing_file_name,
                local_path=part.outgoing_path,
                part_number=part.part_number,
            )
            self.archive_volumes.add(domain_to_archive_volume_record(volume))
            self.task_queue.enqueue_upload(volume.id)

        uploading = replace(archiving, status=SourceItemStatus.UPLOADING)
        self.source_items.update(domain_to_source_item_record(uploading))
