from dataclasses import dataclass
from uuid import UUID

import domain as domain
from use_cases.mappers import domain_to_source_item_record
from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.repositories.source_item import SourceItemRepository


@dataclass(frozen=True, slots=True)
class CleanupVolumeUseCase:
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository

    def execute(self, archive_volume_id: UUID) -> None:
        volume = self.archive_volumes.require(archive_volume_id)

        if volume.local_path.exists():
            volume.local_path.unlink()

        item = self.source_items.require(volume.source_item_id)

        remaining_volumes = self.archive_volumes.list_domain_by_source_item(item.id)
        all_cleaned = all(not remaining.local_path.exists() for remaining in remaining_volumes)
        if all_cleaned and domain.is_source_item(item, status=domain.SourceItemStatus.CLEANUP):
            completed = domain.mark_source_item(item, status=domain.SourceItemStatus.COMPLETED)
            self.source_items.update(domain_to_source_item_record(completed))
