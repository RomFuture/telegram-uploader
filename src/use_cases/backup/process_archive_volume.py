from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.backup.gates import require_item_queued
from use_cases.backup.idempotency import (
    ArchiveStepAction,
    UploadStepAction,
    decide_archive_on_retry,
    decide_upload_on_retry,
)
from use_cases.shared.mappers import domain_to_archive_volume_record, merge_source_item_record
from use_cases.shared.ports.archive_service import ArchiveServicePort
from use_cases.shared.ports.task_queue import TaskQueuePort
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.repositories.source_item import SourceItemRepository
from use_cases.shared.types import SourceItem


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
        action = decide_archive_on_retry(item)

        if action == ArchiveStepAction.SKIP:
            return
        if action == ArchiveStepAction.FAIL:
            return
        if action == ArchiveStepAction.RESUME:
            self._resume_uploads(item)
            return

        require_item_queued(item)
        session = self.sessions.require(item.session_id)

        archiving = domain.mark_source_item(item, status=domain.SourceItemStatus.ARCHIVING)
        self._update_source_item(archiving)

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
        self._update_source_item(uploading)

    def _update_source_item(self, source_item: SourceItem) -> None:
        existing = self.source_items.get(source_item.id)
        self.source_items.update(merge_source_item_record(existing, source_item))

    def _resume_uploads(self, item: SourceItem) -> None:
        volumes = self.archive_volumes.list_domain_by_source_item(item.id)
        if not volumes:
            raise domain.DomainError.invalid_status_transition(
                "SourceItem",
                item.status.value,
                "archiving with persisted volumes",
            )

        for volume in volumes:
            upload_action = decide_upload_on_retry(volume)
            if upload_action in (
                UploadStepAction.RUN,
                UploadStepAction.CONTINUE,
            ):
                self.task_queue.enqueue_upload(volume.id)

        if domain.is_source_item(item, status=domain.SourceItemStatus.ARCHIVING):
            uploading = domain.mark_source_item(item, status=domain.SourceItemStatus.UPLOADING)
            self._update_source_item(uploading)
