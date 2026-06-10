"""Enqueue a source file and immediately schedule archive (eager path).

``StartBackupPipelineUseCase`` re-enqueues only ``queued`` items (batch start).
Both paths are intentional: add-file can archive before the user clicks Start Backup.
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.mappers import domain_to_source_item_record
from use_cases.ports.task_queue import TaskQueuePort
from use_cases.repositories.source_item import SourceItemRepository
from use_cases.types import SourceItem


@dataclass(frozen=True, slots=True)
class EnqueueSourceItemUseCase:
    source_items: SourceItemRepository
    task_queue: TaskQueuePort

    def execute(self, session_id: UUID, source_path: Path, display_name: str) -> SourceItem:
        item = domain.create_source_item(session_id, source_path, display_name)
        self.source_items.add(domain_to_source_item_record(item))
        self.task_queue.enqueue_archive(item.id)
        return item
