from dataclasses import dataclass
from uuid import UUID

from use_cases.domain.errors import SessionNotFound
from use_cases.domain.mappers import session_record_to_domain, source_item_record_to_domain
from use_cases.domain.models import SessionStatus, SourceItemStatus
from use_cases.domain.transitions import ensure_session_status
from use_cases.ports.task_queue import TaskQueuePort
from use_cases.repositories import Repositories


@dataclass(frozen=True, slots=True)
class StartBackupPipelineUseCase:
    repos: Repositories
    task_queue: TaskQueuePort

    def execute(self, session_id: UUID) -> int:
        session_record = self.repos.sessions.get(session_id)
        if session_record is None:
            raise SessionNotFound
        session = session_record_to_domain(session_record)
        ensure_session_status(session.status, SessionStatus.RUNNING)

        enqueued = 0
        for item_record in self.repos.source_items.list_by_session(session_id):
            item = source_item_record_to_domain(item_record)
            if item.status != SourceItemStatus.QUEUED:
                continue
            self.task_queue.enqueue_archive(item.id)
            enqueued += 1
        return enqueued
