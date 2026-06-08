from dataclasses import dataclass
from uuid import UUID

import domain as domain
from use_cases.mappers import domain_to_session_record
from use_cases.ports.task_queue import TaskQueuePort
from use_cases.repositories import Repositories


@dataclass(frozen=True, slots=True)
class StartBackupPipelineUseCase:
    repos: Repositories
    task_queue: TaskQueuePort

    def execute(self, session_id: UUID) -> int:
        session = self.repos.sessions.require(session_id)
        if session.status == domain.SessionStatus.CREATED:
            session = domain.mark_session(session, status=domain.SessionStatus.RUNNING)
            self.repos.sessions.update(domain_to_session_record(session))
        else:
            domain.prepare_session_for_backup(session)

        enqueued = 0
        for item in self.repos.source_items.list_domain_by_session(session_id):
            if not domain.is_source_item(item, status=domain.SourceItemStatus.QUEUED):
                continue
            self.task_queue.enqueue_archive(item.id)
            enqueued += 1
        return enqueued
