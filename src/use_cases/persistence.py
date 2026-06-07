"""Persistence records — infrastructure contract; mirror domain fields as plain values."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class SessionRecord:
    id: UUID
    profile_name: str
    encryption_key: str
    status: str
    created_at: datetime


@dataclass(slots=True)
class SourceItemRecord:
    id: UUID
    session_id: UUID
    source_path: str
    display_name: str
    status: str
    created_at: datetime


@dataclass(slots=True)
class ArchiveVolumeRecord:
    id: UUID
    source_item_id: UUID
    file_name: str
    local_path: str
    part_number: int
    status: str
    external_file_id: str | None
    external_message_id: str | None
    provider_download_ref: str | None
    created_at: datetime
