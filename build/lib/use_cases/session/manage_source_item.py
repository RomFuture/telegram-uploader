"""Rename, move, or remove items in the backup queue."""

from dataclasses import dataclass, replace
from uuid import UUID

import domain as domain
from use_cases.shared.mappers import domain_to_source_item_record, source_item_record_to_domain
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.source_item import SourceItemRepository


@dataclass(frozen=True, slots=True)
class RenameSourceItemUseCase:
    source_items: SourceItemRepository

    def execute(self, source_item_id: UUID, display_name: str) -> None:
        name = display_name.strip()
        if not name:
            raise domain.DomainError.invalid_status_transition(
                "SourceItem",
                "rename",
                "non-empty display name",
            )
        record = self.source_items.get(source_item_id)
        if record is None:
            raise domain.DomainError.source_item_not_found(source_item_id)
        item = source_item_record_to_domain(record)
        updated = replace(item, display_name=name)
        self.source_items.update(
            domain_to_source_item_record(updated, folder_id=record.folder_id)
        )


@dataclass(frozen=True, slots=True)
class MoveSourceItemUseCase:
    source_items: SourceItemRepository
    folders: FolderRepository

    def execute(self, source_item_id: UUID, folder_id: UUID) -> None:
        record = self.source_items.get(source_item_id)
        if record is None:
            raise domain.DomainError.source_item_not_found(source_item_id)
        folder = self.folders.get(folder_id)
        if folder is None or folder.session_id != record.session_id:
            raise domain.DomainError.invalid_status_transition(
                "SourceItem",
                "move",
                "folder in same session",
            )
        item = source_item_record_to_domain(record)
        self.source_items.update(
            domain_to_source_item_record(item, folder_id=folder_id)
        )


@dataclass(frozen=True, slots=True)
class DeleteSourceItemUseCase:
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository | None = None

    def execute(self, source_item_id: UUID) -> None:
        if self.source_items.get(source_item_id) is None:
            raise domain.DomainError.source_item_not_found(source_item_id)
        if self.archive_volumes is not None:
            for volume in self.archive_volumes.list_by_source_item(source_item_id):
                self.archive_volumes.delete(volume.id)
        self.source_items.delete(source_item_id)
