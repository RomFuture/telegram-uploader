"""Mark pipeline entities failed — called when a worker stage gives up retrying.

Rules:
- Only non-terminal statuses transition to ``failed``.
- Never overwrite ``completed``.
- Calling twice on an already ``failed`` entity is a no-op.
"""

from dataclasses import dataclass
from uuid import UUID

import domain as domain
from use_cases.shared.mappers import domain_to_archive_volume_record, merge_source_item_record
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.source_item import SourceItemRepository
from use_cases.shared.types import SourceItem


def _mark_source_item_failed_if_active(item: SourceItem) -> SourceItem | None:
    if domain.is_source_item(item, status=domain.SourceItemStatus.FAILED):
        return None
    if domain.is_source_item(item, status=domain.SourceItemStatus.COMPLETED):
        return None
    return domain.mark_source_item(item, status=domain.SourceItemStatus.FAILED)


@dataclass(frozen=True, slots=True)
class ReportArchiveFailureUseCase:
    source_items: SourceItemRepository

    def execute(self, source_item_id: UUID) -> None:
        item = self.source_items.require(source_item_id)
        failed = _mark_source_item_failed_if_active(item)
        if failed is not None:
            existing = self.source_items.get(item.id)
            self.source_items.update(merge_source_item_record(existing, failed))


@dataclass(frozen=True, slots=True)
class ReportUploadFailureUseCase:
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository

    def execute(self, archive_volume_id: UUID) -> None:
        volume = self.archive_volumes.require(archive_volume_id)
        if volume.status != domain.ArchiveVolumeStatus.FAILED:
            failed_volume = domain.mark_archive_volume(
                volume, status=domain.ArchiveVolumeStatus.FAILED
            )
            self.archive_volumes.update(domain_to_archive_volume_record(failed_volume))

        item = self.source_items.require(volume.source_item_id)
        if domain.is_source_item(item, status=domain.SourceItemStatus.UPLOADING):
            failed_item = _mark_source_item_failed_if_active(item)
            if failed_item is not None:
                existing = self.source_items.get(item.id)
                self.source_items.update(merge_source_item_record(existing, failed_item))


@dataclass(frozen=True, slots=True)
class ReportCleanupFailureUseCase:
    source_items: SourceItemRepository

    def execute(self, source_item_id: UUID) -> None:
        item = self.source_items.require(source_item_id)
        if not domain.is_source_item(item, status=domain.SourceItemStatus.CLEANUP):
            return
        failed = _mark_source_item_failed_if_active(item)
        if failed is not None:
            existing = self.source_items.get(item.id)
            self.source_items.update(merge_source_item_record(existing, failed))
