"""Domain-level exceptions. No I/O, no layer imports."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(slots=True)
class DomainError(Exception):
    """Single domain error type — identity via ``code`` and context fields.

    Use cases decide *when* to fail; factory methods here define *how* the
    error is shaped (``code``, ``message``, ``entity_id``, ``reason``).
    GUI and logs read ``str(error)`` for the user-facing message.
    """

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
        """Raise when loading a session by UUID and the repository has no row.

        Produces ``code="session_not_found"`` with ``entity_id=session_id``.

        Typical callers: ``use_cases.shared.repositories.loading.load_session``.
        """
        return cls(
            code="session_not_found",
            message=f"Session not found: {session_id}",
            entity="Session",
            entity_id=session_id,
        )

    @classmethod
    def source_item_not_found(cls, item_id: UUID) -> "DomainError":
        """Raise when a source item id does not exist (rename, move, delete).

        Produces ``code="source_item_not_found"`` with ``entity_id=item_id``.

        Typical callers: ``ManageSourceItemUseCase``.
        """
        return cls(
            code="source_item_not_found",
            message=f"Source item not found: {item_id}",
            entity="SourceItem",
            entity_id=item_id,
        )

    @classmethod
    def archive_volume_not_found(cls, volume_id: UUID) -> "DomainError":
        """Raise when loading an archive volume by UUID and the row is missing.

        Produces ``code="archive_volume_not_found"`` with ``entity_id=volume_id``.

        Typical callers: ``use_cases.shared.repositories.loading.load_archive_volume``.
        """
        return cls(
            code="archive_volume_not_found",
            message=f"Archive volume not found: {volume_id}",
            entity="ArchiveVolume",
            entity_id=volume_id,
        )

    @classmethod
    def no_volumes_for_session(cls, session_id: UUID) -> "DomainError":
        """Raise when restore expects volumes for a session but the list is empty.

        Same ``code`` as ``archive_volume_not_found``; distinguished by ``reason``.

        Typical callers: ``use_cases.shared.repositories.loading``.
        """
        return cls(
            code="archive_volume_not_found",
            message=f"No archive volumes found for session: {session_id}",
            entity="ArchiveVolume",
            entity_id=session_id,
            reason="no_volumes",
        )

    @classmethod
    def missing_external_file_id(cls, volume_id: UUID) -> "DomainError":
        """Raise when a volume lacks Telegram metadata required for restore.

        Produces ``code="archive_volume_not_found"`` with ``reason="missing_external_file_id"``.

        Typical callers: ``use_cases.restore.refs``.
        """
        return cls(
            code="archive_volume_not_found",
            message=f"Archive volume missing external file id: {volume_id}",
            entity="ArchiveVolume",
            entity_id=volume_id,
            reason="missing_external_file_id",
        )

    @classmethod
    def session_not_found_by_profile(cls, profile_name: str) -> "DomainError":
        """Raise when unlock/open is attempted for a profile name not in the database.

        Produces ``code="session_not_found"``; ``reason`` holds the profile name.

        Typical callers: ``UnlockSessionUseCase``.
        """
        return cls(
            code="session_not_found",
            message=f"Database not found: {profile_name}",
            entity="Session",
            reason=profile_name,
        )

    @classmethod
    def wrong_encryption_key(cls, profile_name: str) -> "DomainError":
        """Raise when the profile exists but the supplied encryption key does not match.

        Produces ``code="wrong_encryption_key"``.

        Typical callers: ``UnlockSessionUseCase``.
        """
        return cls(
            code="wrong_encryption_key",
            message="Wrong encryption key",
            entity="Session",
            reason=profile_name,
        )

    @classmethod
    def profile_already_exists(cls, profile_name: str) -> "DomainError":
        """Raise when creating a database and the profile name is already taken.

        UC checks ``sessions.find_by_profile_name`` first, then calls this factory.
        Produces ``code="profile_already_exists"``.

        Typical callers: ``CreateDatabaseUseCase``.
        """
        return cls(
            code="profile_already_exists",
            message=f"Database already exists: {profile_name}",
            entity="Session",
            reason=profile_name,
        )

    @classmethod
    def required(cls, field: str) -> "DomainError":
        """Raise when a use case rejects empty input after ``strip()``.

        ``field`` is the human-readable label (e.g. ``"Folder name"``), not the
        user's raw value. Produces ``code="invalid_input"`` and message
        ``"{field} is required"``.

        Typical callers: ``CreateDatabaseUseCase``, ``CreateFolderUseCase``.
        """
        return cls(
            code="invalid_input",
            message=f"{field} is required",
        )

    @classmethod
    def folder_already_exists(cls, folder_name: str) -> "DomainError":
        """Raise when creating a folder and the name already exists in the session.

        UC checks ``folders.find_by_name`` first. Produces ``code="folder_already_exists"``.

        Typical callers: ``CreateFolderUseCase``.
        """
        return cls(
            code="folder_already_exists",
            message=f"Folder already exists: {folder_name}",
            reason=folder_name,
        )

    @classmethod
    def folder_not_found(cls, folder_id: UUID) -> "DomainError":
        """Raise when enqueue targets a folder id missing or belonging to another session.

        Produces ``code="folder_not_found"`` with ``entity_id=folder_id``.

        Typical callers: ``EnqueueSourceItemUseCase``.
        """
        return cls(
            code="folder_not_found",
            message=f"Folder not found in session: {folder_id}",
            entity_id=folder_id,
        )

    @classmethod
    def no_restorable_backups(cls, session_id: UUID) -> "DomainError":
        """Raise when restore is requested but no completed uploads exist for the session.

        Produces ``code="no_restorable_backups"``.

        Typical callers: ``RestoreSessionUseCase``.
        """
        return cls(
            code="no_restorable_backups",
            message=(
                "No completed backups to restore. Click Start Backup to retry unfinished uploads."
            ),
            entity="Session",
            entity_id=session_id,
            reason="no_restorable_backups",
        )

    @classmethod
    def no_restorable_backups_in_folder(cls, folder_name: str) -> "DomainError":
        """Raise when restore is scoped to a folder with no uploaded items.

        Produces ``code="no_restorable_backups_in_folder"``.

        Typical callers: ``RestoreSessionUseCase``.
        """
        return cls(
            code="no_restorable_backups_in_folder",
            message=(
                f"No completed backups to restore in {folder_name}.\n\n"
                "Switch to a folder with backed-up files or run Start Backup first."
            ),
            reason=folder_name,
        )

    @classmethod
    def legacy_volumes(cls) -> "DomainError":
        """Raise when restore hits volumes from the old Bot API provider.

        Produces ``code="legacy_volumes"``. User must re-backup with Client API.

        Typical callers: ``restore/refs.py``, ``RestoreSessionUseCase``.
        """
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
    def restore_destination_not_writable(cls, dest_path: Path, detail: str) -> "DomainError":
        """Raise when the restore destination path cannot be created or written to.

        Produces ``code="restore_destination_not_writable"`` with OS error detail.

        Typical callers: ``use_cases.restore.dest_path``.
        """
        return cls(
            code="restore_destination_not_writable",
            message=(
                f"Cannot write to restore folder:\n{dest_path}\n\n"
                f"{detail}\n\n"
                "Choose a folder you own (for example ~/Restored/). "
                "Avoid directories under /opt/telegram-uploader/."
            ),
            reason=str(dest_path),
        )

    @classmethod
    def invalid_status_transition(
        cls,
        entity: str,
        from_status: str,
        to_status: str,
    ) -> "DomainError":
        """Raise when an entity is not in the status required for the next pipeline step.

        Used by ``verify_*`` actions and UC guards (e.g. rename only while ``queued``).
        Produces ``code="invalid_status_transition"``.

        Typical callers: ``backup/gates.py``, ``backup/idempotency.py``,
        ``ManageSourceItemUseCase``, ``ProcessArchiveVolumeUseCase``.
        """
        return cls(
            code="invalid_status_transition",
            message=f"{entity}: cannot transition from {from_status!r} to {to_status!r}",
            entity=entity,
            from_status=from_status,
            to_status=to_status,
        )
