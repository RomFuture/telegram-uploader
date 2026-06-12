from copy import deepcopy
from uuid import UUID

from use_cases.shared.persistence import (
    ArchiveVolumeRecord,
    BackupFolderRecord,
    SessionRecord,
    SourceItemRecord,
)
from use_cases.shared.repositories.loading import (
    map_archive_volumes,
    map_source_items,
    require_archive_volume_record,
    require_archive_volumes_for_session,
    require_session_record,
    require_source_item_record,
)
from use_cases.shared.types import ArchiveVolume, Session, SourceItem


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, SessionRecord] = {}

    def add(self, record: SessionRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, session_id: UUID) -> SessionRecord | None:
        record = self._records.get(session_id)
        return deepcopy(record) if record is not None else None

    def require(self, session_id: UUID) -> Session:
        return require_session_record(self.get(session_id), session_id)

    def update(self, record: SessionRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def list_profiles(self) -> tuple[str, ...]:
        names = sorted({record.profile_name for record in self._records.values()})
        return tuple(names)

    def find_by_profile_name(self, profile_name: str) -> SessionRecord | None:
        for record in self._records.values():
            if record.profile_name == profile_name:
                return deepcopy(record)
        return None


class InMemoryFolderRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, BackupFolderRecord] = {}

    def add(self, record: BackupFolderRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, folder_id: UUID) -> BackupFolderRecord | None:
        record = self._records.get(folder_id)
        return deepcopy(record) if record is not None else None

    def list_by_session(self, session_id: UUID) -> list[BackupFolderRecord]:
        records = [record for record in self._records.values() if record.session_id == session_id]
        records.sort(key=lambda item: item.name.lower())
        return [deepcopy(record) for record in records]

    def find_by_name(self, session_id: UUID, name: str) -> BackupFolderRecord | None:
        for record in self._records.values():
            if record.session_id == session_id and record.name == name:
                return deepcopy(record)
        return None


class InMemorySourceItemRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, SourceItemRecord] = {}

    def add(self, record: SourceItemRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, source_item_id: UUID) -> SourceItemRecord | None:
        record = self._records.get(source_item_id)
        return deepcopy(record) if record is not None else None

    def require(self, source_item_id: UUID) -> SourceItem:
        return require_source_item_record(self.get(source_item_id), source_item_id)

    def list_by_session(self, session_id: UUID) -> list[SourceItemRecord]:
        records = [record for record in self._records.values() if record.session_id == session_id]
        records.sort(key=lambda item: item.created_at)
        return [deepcopy(record) for record in records]

    def list_domain_by_session(self, session_id: UUID) -> list[SourceItem]:
        return map_source_items(self.list_by_session(session_id))

    def update(self, record: SourceItemRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def delete(self, source_item_id: UUID) -> None:
        self._records.pop(source_item_id, None)


class InMemoryArchiveVolumeRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, ArchiveVolumeRecord] = {}

    def add(self, record: ArchiveVolumeRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def get(self, volume_id: UUID) -> ArchiveVolumeRecord | None:
        record = self._records.get(volume_id)
        return deepcopy(record) if record is not None else None

    def require(self, volume_id: UUID) -> ArchiveVolume:
        return require_archive_volume_record(self.get(volume_id), volume_id)

    def list_by_source_item(self, source_item_id: UUID) -> list[ArchiveVolumeRecord]:
        records = [
            record for record in self._records.values() if record.source_item_id == source_item_id
        ]
        records.sort(key=lambda item: item.part_number)
        return [deepcopy(record) for record in records]

    def list_domain_by_source_item(self, source_item_id: UUID) -> list[ArchiveVolume]:
        return map_archive_volumes(self.list_by_source_item(source_item_id))

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

    def require_for_session(self, session_id: UUID) -> list[ArchiveVolume]:
        return require_archive_volumes_for_session(self.list_by_session(session_id), session_id)

    def update(self, record: ArchiveVolumeRecord) -> None:
        self._records[record.id] = deepcopy(record)

    def delete(self, volume_id: UUID) -> None:
        self._records.pop(volume_id, None)

    def bind_source_items(self, source_items: InMemorySourceItemRepository) -> None:
        self._source_items = source_items


class InMemoryRepositories:
    def __init__(self) -> None:
        self.sessions = InMemorySessionRepository()
        self.folders = InMemoryFolderRepository()
        self.source_items = InMemorySourceItemRepository()
        self.archive_volumes = InMemoryArchiveVolumeRepository()
        self.archive_volumes.bind_source_items(self.source_items)
