from typing import Protocol, runtime_checkable
from uuid import UUID

from use_cases.persistence import ArchiveVolumeRecord


@runtime_checkable
class ArchiveVolumeRepository(Protocol):
    def add(self, record: ArchiveVolumeRecord) -> None: ...

    def get(self, volume_id: UUID) -> ArchiveVolumeRecord | None: ...

    def list_by_source_item(self, source_item_id: UUID) -> list[ArchiveVolumeRecord]: ...

    def list_by_session(self, session_id: UUID) -> list[ArchiveVolumeRecord]: ...

    def update(self, record: ArchiveVolumeRecord) -> None: ...
