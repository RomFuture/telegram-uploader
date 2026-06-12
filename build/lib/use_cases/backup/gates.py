"""Backup pipeline preconditions — which status a step requires before it runs."""

import domain as domain
from use_cases.shared.types import ArchiveVolume, Session, SourceItem


def require_session_running(session: Session) -> None:
    """Session must be ``running`` before enqueueing backup work."""
    domain.verify_session(session, status=domain.SessionStatus.RUNNING)


def require_item_queued(item: SourceItem) -> None:
    """Source item must be ``queued`` before archive starts."""
    domain.verify_source_item(item, status=domain.SourceItemStatus.QUEUED)


def require_item_archivable(item: SourceItem, *, has_volumes: bool) -> None:
    """Allow ``queued``, or orphaned ``archiving`` with no volumes yet (worker retry)."""
    if domain.is_source_item(item, status=domain.SourceItemStatus.QUEUED):
        return
    if domain.is_source_item(item, status=domain.SourceItemStatus.ARCHIVING) and not has_volumes:
        return
    domain.verify_source_item(item, status=domain.SourceItemStatus.QUEUED)


def require_volume_created(volume: ArchiveVolume) -> None:
    """Archive volume must be ``created`` before upload starts."""
    domain.verify_archive_volume(volume, status=domain.ArchiveVolumeStatus.CREATED)
