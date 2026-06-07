from dataclasses import dataclass, replace
from pathlib import Path
from uuid import UUID

from use_cases.domain.errors import ArchiveVolumeNotFound, SourceItemNotFound
from use_cases.domain.mappers import (
    domain_to_source_item_record,
    source_item_record_to_domain,
)
from use_cases.domain.models import SourceItemStatus
from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.repositories.source_item import SourceItemRepository


@dataclass(frozen=True, slots=True)
class CleanupVolumeUseCase:
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository

    def execute(self, archive_volume_id: UUID) -> None:
        volume_record = self.archive_volumes.get(archive_volume_id)
        if volume_record is None:
            raise ArchiveVolumeNotFound

        local_path = Path(volume_record.local_path)
        if local_path.exists():
            local_path.unlink()

        item_record = self.source_items.get(volume_record.source_item_id)
        if item_record is None:
            raise SourceItemNotFound
        item = source_item_record_to_domain(item_record)

        remaining_volumes = self.archive_volumes.list_by_source_item(item.id)
        all_cleaned = all(not Path(record.local_path).exists() for record in remaining_volumes)
        if all_cleaned and item.status == SourceItemStatus.CLEANUP:
            completed = replace(item, status=SourceItemStatus.COMPLETED)
            self.source_items.update(domain_to_source_item_record(completed))
