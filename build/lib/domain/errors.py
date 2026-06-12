"""Domain-level exceptions. No I/O, no layer imports."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class DomainError(Exception):
    """Single domain error type — identity via ``code`` and context fields."""

    code: str
    message: str
    entity: str | None = None
    entity_id: UUID | None = None
    from_status: str | None = None
    to_status: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    @classmethod
    def session_not_found(cls, session_id: UUID) -> "DomainError":
        return cls(
            code="session_not_found",
            message=f"Session not found: {session_id}",
            entity="Session",
            entity_id=session_id,
        )

    @classmethod
    def source_item_not_found(cls, item_id: UUID) -> "DomainError":
        return cls(
            code="source_item_not_found",
            message=f"Source item not found: {item_id}",
            entity="SourceItem",
            entity_id=item_id,
        )

    @classmethod
    def archive_volume_not_found(cls, volume_id: UUID) -> "DomainError":
        return cls(
            code="archive_volume_not_found",
            message=f"Archive volume not found: {volume_id}",
            entity="ArchiveVolume",
            entity_id=volume_id,
        )

    @classmethod
    def no_volumes_for_session(cls, session_id: UUID) -> "DomainError":
        return cls(
            code="archive_volume_not_found",
            message=f"No archive volumes found for session: {session_id}",
            entity="ArchiveVolume",
            entity_id=session_id,
            reason="no_volumes",
        )

    @classmethod
    def missing_external_file_id(cls, volume_id: UUID) -> "DomainError":
        return cls(
            code="archive_volume_not_found",
            message=f"Archive volume missing external file id: {volume_id}",
            entity="ArchiveVolume",
            entity_id=volume_id,
            reason="missing_external_file_id",
        )

    @classmethod
    def session_not_found_by_profile(cls, profile_name: str) -> "DomainError":
        return cls(
            code="session_not_found",
            message=f"Database not found: {profile_name}",
            entity="Session",
            reason=profile_name,
        )

    @classmethod
    def wrong_encryption_key(cls, profile_name: str) -> "DomainError":
        return cls(
            code="wrong_encryption_key",
            message="Wrong encryption key",
            entity="Session",
            reason=profile_name,
        )

    @classmethod
    def profile_already_exists(cls, profile_name: str) -> "DomainError":
        return cls(
            code="profile_already_exists",
            message=f"Database already exists: {profile_name}",
            entity="Session",
            reason=profile_name,
        )

    @classmethod
    def no_restorable_backups(cls, session_id: UUID) -> "DomainError":
        return cls(
            code="no_restorable_backups",
            message=(
                "No completed backups to restore. "
                "Click Start Backup to retry unfinished uploads."
            ),
            entity="Session",
            entity_id=session_id,
            reason="no_restorable_backups",
        )

    @classmethod
    def legacy_volumes(cls) -> "DomainError":
        return cls(
            code="legacy_volumes",
            message=(
                "Restore requires Client API backups. "
                "Re-backup your files with TELEGRAM_PROVIDER=client."
            ),
            entity="ArchiveVolume",
            reason="legacy_bot_api",
        )

    @classmethod
    def invalid_status_transition(
        cls,
        entity: str,
        from_status: str,
        to_status: str,
    ) -> "DomainError":
        return cls(
            code="invalid_status_transition",
            message=f"{entity}: cannot transition from {from_status!r} to {to_status!r}",
            entity=entity,
            from_status=from_status,
            to_status=to_status,
        )
