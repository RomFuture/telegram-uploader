from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from infrastructure.db.engine import build_db_session_factory, db_session_scope
from infrastructure.db.mappers import (
    archive_volume_row_to_record,
    record_to_archive_volume_row,
    record_to_source_item_row,
    record_to_upload_session_row,
    source_item_row_to_record,
    upload_session_row_to_record,
)
from infrastructure.db.orm import ArchiveVolumeRow, SourceItemRow, UploadSessionRow
from use_cases.persistence import ArchiveVolumeRecord, SessionRecord, SourceItemRecord
from use_cases.repositories.loading import (
    map_archive_volumes,
    map_source_items,
    require_archive_volume_record,
    require_archive_volumes_for_session,
    require_session_record,
    require_source_item_record,
)
from use_cases.types import ArchiveVolume, Session, SourceItem


@dataclass(frozen=True, slots=True)
class SqlAlchemySessionRepository:
    db_session_factory: Callable[[], DbSession]

    def add(self, record: SessionRecord) -> None:
        with db_session_scope(self.db_session_factory) as db:
            db.add(record_to_upload_session_row(record))

    def get(self, session_id: UUID) -> SessionRecord | None:
        with db_session_scope(self.db_session_factory) as db:
            row = db.get(UploadSessionRow, session_id)
            if row is None:
                return None
            return upload_session_row_to_record(row)

    def require(self, session_id: UUID) -> Session:
        return require_session_record(self.get(session_id), session_id)

    def update(self, record: SessionRecord) -> None:
        with db_session_scope(self.db_session_factory) as db:
            db.merge(record_to_upload_session_row(record))


@dataclass(frozen=True, slots=True)
class SqlAlchemySourceItemRepository:
    db_session_factory: Callable[[], DbSession]

    def add(self, record: SourceItemRecord) -> None:
        with db_session_scope(self.db_session_factory) as db:
            db.add(record_to_source_item_row(record))

    def get(self, source_item_id: UUID) -> SourceItemRecord | None:
        with db_session_scope(self.db_session_factory) as db:
            row = db.get(SourceItemRow, source_item_id)
            if row is None:
                return None
            return source_item_row_to_record(row)

    def require(self, source_item_id: UUID) -> SourceItem:
        return require_source_item_record(self.get(source_item_id), source_item_id)

    def list_by_session(self, session_id: UUID) -> list[SourceItemRecord]:
        with db_session_scope(self.db_session_factory) as db:
            rows = db.scalars(
                select(SourceItemRow)
                .where(SourceItemRow.session_id == session_id)
                .order_by(SourceItemRow.created_at)
            ).all()
            return [source_item_row_to_record(row) for row in rows]

    def list_domain_by_session(self, session_id: UUID) -> list[SourceItem]:
        return map_source_items(self.list_by_session(session_id))

    def update(self, record: SourceItemRecord) -> None:
        with db_session_scope(self.db_session_factory) as db:
            db.merge(record_to_source_item_row(record))


@dataclass(frozen=True, slots=True)
class SqlAlchemyArchiveVolumeRepository:
    db_session_factory: Callable[[], DbSession]

    def add(self, record: ArchiveVolumeRecord) -> None:
        with db_session_scope(self.db_session_factory) as db:
            db.add(record_to_archive_volume_row(record))

    def get(self, volume_id: UUID) -> ArchiveVolumeRecord | None:
        with db_session_scope(self.db_session_factory) as db:
            row = db.get(ArchiveVolumeRow, volume_id)
            if row is None:
                return None
            return archive_volume_row_to_record(row)

    def require(self, volume_id: UUID) -> ArchiveVolume:
        return require_archive_volume_record(self.get(volume_id), volume_id)

    def list_by_source_item(self, source_item_id: UUID) -> list[ArchiveVolumeRecord]:
        with db_session_scope(self.db_session_factory) as db:
            rows = db.scalars(
                select(ArchiveVolumeRow)
                .where(ArchiveVolumeRow.source_item_id == source_item_id)
                .order_by(ArchiveVolumeRow.part_number)
            ).all()
            return [archive_volume_row_to_record(row) for row in rows]

    def list_domain_by_source_item(self, source_item_id: UUID) -> list[ArchiveVolume]:
        return map_archive_volumes(self.list_by_source_item(source_item_id))

    def list_by_session(self, session_id: UUID) -> list[ArchiveVolumeRecord]:
        with db_session_scope(self.db_session_factory) as db:
            rows = db.scalars(
                select(ArchiveVolumeRow)
                .join(SourceItemRow, SourceItemRow.id == ArchiveVolumeRow.source_item_id)
                .where(SourceItemRow.session_id == session_id)
                .order_by(SourceItemRow.created_at, ArchiveVolumeRow.part_number)
            ).all()
            return [archive_volume_row_to_record(row) for row in rows]

    def require_for_session(self, session_id: UUID) -> list[ArchiveVolume]:
        return require_archive_volumes_for_session(self.list_by_session(session_id), session_id)

    def update(self, record: ArchiveVolumeRecord) -> None:
        with db_session_scope(self.db_session_factory) as db:
            db.merge(record_to_archive_volume_row(record))


@dataclass(frozen=True, slots=True)
class SqlAlchemyRepositories:
    sessions: SqlAlchemySessionRepository
    source_items: SqlAlchemySourceItemRepository
    archive_volumes: SqlAlchemyArchiveVolumeRepository

    @classmethod
    def from_dsn(cls, postgres_dsn: str) -> SqlAlchemyRepositories:
        db_session_factory = build_db_session_factory(postgres_dsn)
        return cls(
            sessions=SqlAlchemySessionRepository(db_session_factory),
            source_items=SqlAlchemySourceItemRepository(db_session_factory),
            archive_volumes=SqlAlchemyArchiveVolumeRepository(db_session_factory),
        )
