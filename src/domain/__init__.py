"""Foundation layer of telegram-uploader. Single import entry for use cases.

What each file is for:

- ``models.py`` — the objects we store (session, file in queue, archive part) and the
  list of allowed states for each.
- ``actions.py`` — create those objects and move them between states; check that the
  current state is what we expect.
- ``errors.py`` — typed failures when someone tries an illegal state change.

Import as ``import domain as domain``, not from submodules.

Full guide: ``MANUAL.md`` in this package.
"""

from .actions import (
    create_archive_volume,
    create_session,
    create_source_item,
    is_source_item,
    mark_archive_volume,
    mark_archive_volume_uploaded,
    mark_session,
    mark_source_item,
    verify_archive_volume,
    verify_session,
    verify_source_item,
)
from .errors import DomainError
from .models import ArchiveVolumeStatus, SessionStatus, SourceItemStatus

__all__ = [
    "ArchiveVolumeStatus",
    "DomainError",
    "SessionStatus",
    "SourceItemStatus",
    "create_archive_volume",
    "create_session",
    "create_source_item",
    "verify_archive_volume",
    "verify_session",
    "verify_source_item",
    "is_source_item",
    "mark_archive_volume",
    "mark_archive_volume_uploaded",
    "mark_session",
    "mark_source_item",
]
