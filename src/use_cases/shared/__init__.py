"""Shared persistence, ports, repositories, and mappers for use cases."""

from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)
from use_cases.shared.mappers import (
    archive_volume_record_to_domain,
    domain_to_archive_volume_record,
    domain_to_session_record,
    domain_to_source_item_record,
    session_record_to_domain,
    source_item_record_to_domain,
)
from use_cases.shared.persistence import ArchiveVolumeRecord, SessionRecord, SourceItemRecord
from use_cases.shared.ports import (
    ArchiveServicePort,
    ArchiveServiceResult,
    ArchiveVolumePart,
    StorageProviderPort,
    TaskQueuePort,
)
from use_cases.shared.repositories import (
    ArchiveVolumeRepository,
    Repositories,
    SessionRepository,
    SourceItemRepository,
)
from use_cases.shared.types import ArchiveVolume, Session, SourceItem

__all__ = [
    "ArchiveServicePort",
    "ArchiveServiceResult",
    "ArchiveVolume",
    "ArchiveVolumePart",
    "ArchiveVolumeRecord",
    "ArchiveVolumeRepository",
    "ClassifiedProviderError",
    "ProviderErrorCategory",
    "ProviderFileInfo",
    "ProviderLimits",
    "Repositories",
    "Session",
    "SessionRecord",
    "SessionRepository",
    "SourceItem",
    "SourceItemRecord",
    "SourceItemRepository",
    "StorageProviderPort",
    "TaskQueuePort",
    "UploadResult",
    "archive_volume_record_to_domain",
    "domain_to_archive_volume_record",
    "domain_to_session_record",
    "domain_to_source_item_record",
    "session_record_to_domain",
    "source_item_record_to_domain",
]
