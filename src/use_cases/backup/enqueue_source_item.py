"""Enqueue a source file into the session queue without starting workers."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import domain as domain
from use_cases.shared.mappers import domain_to_source_item_record
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.source_item import SourceItemRepository
from use_cases.shared.types import SourceItem


@dataclass(frozen=True, slots=True)
class EnqueueSourceItemUseCase:
    source_items: SourceItemRepository
    folders: FolderRepository

    def execute(
        self,
        session_id: UUID,
        source_path: Path,
        display_name: str,
        folder_id: UUID | None = None,
    ) -> SourceItem:
        if folder_id is not None:
            folder = self.folders.get(folder_id)
            if folder is None or folder.session_id != session_id:
                raise domain.DomainError.folder_not_found(folder_id)
        item = domain.create_source_item(session_id, source_path, display_name)
        self.source_items.add(domain_to_source_item_record(item, folder_id=folder_id))
        return item
