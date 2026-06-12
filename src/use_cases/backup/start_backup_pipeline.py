"""Start or resume a backup session; enqueue archive for all ``queued`` items."""

from dataclasses import dataclass
from uuid import UUID

import domain as domain
from use_cases.backup.gates import require_session_running
from use_cases.backup.idempotency import UploadStepAction, decide_upload_on_retry
from use_cases.shared.mappers import (
    domain_to_archive_volume_record,
    domain_to_session_record,
    merge_source_item_record,
)
from use_cases.shared.ports.task_queue import TaskQueuePort
from use_cases.shared.repositories import Repositories

_RESUMABLE_ITEM_STATUSES = (
    domain.SourceItemStatus.UPLOADING,
    domain.SourceItemStatus.FAILED,
    domain.SourceItemStatus.ARCHIVING,
)


@dataclass(frozen=True, slots=True)
class StartBackupPipelineUseCase:
    # Repositories bundle: needs session + all source items for the session in one inject.
    repos: Repositories
    task_queue: TaskQueuePort

    def execute(self, session_id: UUID) -> int:
        session = self.repos.sessions.require(session_id)
        if session.status == domain.SessionStatus.CREATED:
            session = domain.mark_session(session, status=domain.SessionStatus.RUNNING)
            self.repos.sessions.update(domain_to_session_record(session))
        else:
            require_session_running(session)

        enqueued = 0
        for item in self.repos.source_items.list_domain_by_session(session_id):
            if not domain.is_source_item(item, status=domain.SourceItemStatus.QUEUED):
                continue
            self.task_queue.enqueue_archive(item.id)
            enqueued += 1

        enqueued += self._resume_pending_uploads(session_id)
        enqueued += self._resume_stuck_archiving(session_id)
        return enqueued

    def _resume_stuck_archiving(self, session_id: UUID) -> int:
        enqueued = 0
        for item in self.repos.source_items.list_domain_by_session(session_id):
            if item.status != domain.SourceItemStatus.ARCHIVING:
                continue
            if self.repos.archive_volumes.list_domain_by_source_item(item.id):
                continue
            self.task_queue.enqueue_archive(item.id)
            enqueued += 1
        return enqueued

    def _resume_pending_uploads(self, session_id: UUID) -> int:
        enqueued = 0
        for item in self.repos.source_items.list_domain_by_session(session_id):
            if item.status not in _RESUMABLE_ITEM_STATUSES:
                continue

            volumes = self.repos.archive_volumes.list_domain_by_source_item(item.id)
            if not volumes:
                continue

            resumed_any = False
            for volume in volumes:
                if volume.status == domain.ArchiveVolumeStatus.UPLOADED:
                    continue

                upload_volume = volume
                if volume.status == domain.ArchiveVolumeStatus.FAILED:
                    upload_volume = domain.mark_archive_volume(
                        volume,
                        status=domain.ArchiveVolumeStatus.CREATED,
                    )
                    self.repos.archive_volumes.update(
                        domain_to_archive_volume_record(upload_volume)
                    )

                action = decide_upload_on_retry(upload_volume)
                if action in (UploadStepAction.RUN, UploadStepAction.CONTINUE):
                    self.task_queue.enqueue_upload(upload_volume.id)
                    enqueued += 1
                    resumed_any = True

            if resumed_any and item.status in (
                domain.SourceItemStatus.FAILED,
                domain.SourceItemStatus.ARCHIVING,
            ):
                uploading = domain.mark_source_item(
                    item,
                    status=domain.SourceItemStatus.UPLOADING,
                )
                existing = self.repos.source_items.get(item.id)
                self.repos.source_items.update(merge_source_item_record(existing, uploading))

        return enqueued
