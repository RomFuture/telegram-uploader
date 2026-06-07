"""Domain public API — single entry point for use cases.

Layer 1 package (`src/domain/`). Entity types are internal; status enums are
exported for typed ``mark_*`` / ``is_*`` and scenario entry points.

Import only from this module in use case code — not from ``domain.models``, etc.
"""

from .actions import (
    create_archive_volume,
    create_session,
    create_source_item,
    ensure_archive_volume,
    ensure_session,
    ensure_source_item,
    is_source_item,
    mark_archive_volume,
    mark_archive_volume_uploaded,
    mark_session,
    mark_source_item,
)
from .errors import DomainError
from .guards import (
    require_archive_volume,
    require_external_file_id,
    require_non_empty_volumes,
    require_session,
    require_source_item,
)
from .models import ArchiveVolumeStatus, SessionStatus, SourceItemStatus
from .scenarios import (
    external_file_id_for_restore,
    prepare_archive_volume_for_upload,
    prepare_session_for_backup,
    prepare_source_item_for_archive,
)

__all__ = [
    "ArchiveVolumeStatus",
    "DomainError",
    "SessionStatus",
    "SourceItemStatus",
    "create_archive_volume",
    "create_session",
    "create_source_item",
    "ensure_archive_volume",
    "ensure_session",
    "ensure_source_item",
    "external_file_id_for_restore",
    "is_source_item",
    "mark_archive_volume",
    "mark_archive_volume_uploaded",
    "mark_session",
    "mark_source_item",
    "prepare_archive_volume_for_upload",
    "prepare_session_for_backup",
    "prepare_source_item_for_archive",
    "require_archive_volume",
    "require_external_file_id",
    "require_non_empty_volumes",
    "require_session",
    "require_source_item",
]
