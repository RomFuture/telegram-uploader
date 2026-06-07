from copy import deepcopy
from uuid import UUID

from use_cases.persistence import ArchiveVolumeRecord, SessionRecord, SourceItemRecord


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, SessionRecord] = {}

    def add(self, record: SessionRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, session_id: UUID) -> SessionRecord | None:
        record = self._records.get(session_id)
        return deepcopy(record) if record is not None else None

    def update(self, record: SessionRecord) -> None:
        self._records[record.id] = deepcopy(record)


class InMemorySourceItemRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, SourceItemRecord] = {}

    def add(self, record: SourceItemRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, source_item_id: UUID) -> SourceItemRecord | None:
        record = self._records.get(source_item_id)
        return deepcopy(record) if record is not None else None

    def list_by_session(self, session_id: UUID) -> list[SourceItemRecord]:
        records = [record for record in self._records.values() if record.session_id == session_id]
        records.sort(key=lambda item: item.created_at)
        return [deepcopy(record) for record in records]

    def update(self, record: SourceItemRecord) -> None:
        self._records[record.id] = deepcopy(record)


class InMemoryArchiveVolumeRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, ArchiveVolumeRecord] = {}

    def add(self, record: ArchiveVolumeRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, volume_id: UUID) -> ArchiveVolumeRecord | None:
        record = self._records.get(volume_id)
        return deepcopy(record) if record is not None else None

    def list_by_source_item(self, source_item_id: UUID) -> list[ArchiveVolumeRecord]:
        records = [
            record for record in self._records.values() if record.source_item_id == source_item_id
        ]
        records.sort(key=lambda item: item.part_number)
        return [deepcopy(record) for record in records]

    def list_by_session(self, session_id: UUID) -> list[ArchiveVolumeRecord]:
        source_repo = getattr(self, "_source_items", None)
        if source_repo is None:
            return []
        source_ids = {
            record.id for record in source_repo._records.values() if record.session_id == session_id
        }
        records = [
            record for record in self._records.values() if record.source_item_id in source_ids
        ]
        records.sort(key=lambda item: (item.source_item_id, item.part_number))
        return [deepcopy(record) for record in records]

    def update(self, record: ArchiveVolumeRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def bind_source_items(self, source_items: InMemorySourceItemRepository) -> None:
        self._source_items = source_items


class InMemoryRepositories:
    def __init__(self) -> None:
        self.sessions = InMemorySessionRepository()
        self.source_items = InMemorySourceItemRepository()
        self.archive_volumes = InMemoryArchiveVolumeRepository()
        self.archive_volumes.bind_source_items(self.source_items)
