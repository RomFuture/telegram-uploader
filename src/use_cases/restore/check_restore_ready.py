"""Pre-flight checks before GUI restore."""

from dataclasses import dataclass
from uuid import UUID

from use_cases.restore.preflight_types import RestorePreflightReason, RestorePreflightResult
from use_cases.restore.refs import (
    count_incomplete_volumes,
    count_legacy_volumes,
    source_item_ids_restorable_in_session,
)
from use_cases.restore.scope import (
    filter_restorable_ids_by_folder,
    is_session_wide_restore_scope,
    source_item_ids_in_restore_scope,
)
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.loading import map_archive_volumes
from use_cases.shared.repositories.source_item import SourceItemRepository


@dataclass(frozen=True, slots=True)
class CheckRestoreReadyUseCase:
    """Pre-flight checks before GUI restore starts.

    Called from ``GuiEntrypoint.check_restore_ready`` → ``BackendReceiver`` →
    ``app.py`` worker thread before ``request_restore``. Returns
    ``RestorePreflightResult`` only; does not download or extract.

    ``ProcessRestoreVolumeUseCase`` / Celery are not on this path.
    """

    archive_volumes: ArchiveVolumeRepository
    source_items: SourceItemRepository
    folders: FolderRepository
    storage_provider: StorageProviderPort

    def execute(
        self,
        session_id: UUID,
        *,
        folder_id: UUID | None = None,
    ) -> RestorePreflightResult:
        """Return whether restore can proceed for session_id and optional folder scope.

        Evaluates restorable item counts, legacy/incomplete volumes in sidebar scope,
        and storage provider healthcheck. Message copy is formatted in application layer.
        """
        records = self.archive_volumes.list_by_session(session_id)
        if not records:
            return RestorePreflightResult(
                ready=False,
                reason=RestorePreflightReason.NO_VOLUMES,
            )
        volumes = map_archive_volumes(records)
        restorable_ids_in_session = source_item_ids_restorable_in_session(
            volumes, self.storage_provider
        )
        folder_name = self._folder_name(folder_id)
        source_item_records = self.source_items.list_by_session(session_id)
        restorable_ids_in_scope = filter_restorable_ids_by_folder(
            restorable_ids_in_session=restorable_ids_in_session,
            source_items=source_item_records,
            folder_id=folder_id,
            folder_name=folder_name,
        )
        scope_item_ids = source_item_ids_in_restore_scope(
            source_item_records,
            folder_id,
            folder_name,
        )
        legacy_volume_count = count_legacy_volumes(
            volumes,
            self.storage_provider,
            source_item_ids=scope_item_ids,
        )
        incomplete_volume_count = count_incomplete_volumes(
            volumes,
            self.storage_provider,
            source_item_ids=scope_item_ids,
        )
        restore_entire_session = is_session_wide_restore_scope(folder_id, folder_name)

        if not restorable_ids_in_scope:
            if (
                restorable_ids_in_session
                and folder_id is not None
                and not restore_entire_session
            ):
                return RestorePreflightResult(
                    ready=False,
                    reason=RestorePreflightReason.EMPTY_FOLDER,
                    legacy_volume_count=legacy_volume_count,
                    incomplete_volume_count=incomplete_volume_count,
                )
            if incomplete_volume_count > 0:
                return RestorePreflightResult(
                    ready=False,
                    reason=RestorePreflightReason.STALE_BACKUP,
                    incomplete_volume_count=incomplete_volume_count,
                    legacy_volume_count=legacy_volume_count,
                )
            if legacy_volume_count > 0:
                return RestorePreflightResult(
                    ready=False,
                    reason=RestorePreflightReason.LEGACY_VOLUMES,
                    legacy_volume_count=legacy_volume_count,
                )
            return RestorePreflightResult(
                ready=False,
                reason=RestorePreflightReason.INCOMPLETE_UPLOAD,
            )

        try:
            provider_ok = self.storage_provider.healthcheck()
        except Exception:
            provider_ok = False

        if not provider_ok:
            return RestorePreflightResult(
                ready=False,
                reason=RestorePreflightReason.HEALTHCHECK_FAILED,
            )

        return RestorePreflightResult(
            ready=True,
            reason=RestorePreflightReason.READY,
            restorable_count=len(restorable_ids_in_scope),
            incomplete_volume_count=incomplete_volume_count,
            legacy_volume_count=legacy_volume_count,
        )

    def _folder_name(self, folder_id: UUID | None) -> str | None:
        """Folder display name for scope helpers; None when folder_id is unset."""
        if folder_id is None:
            return None
        folder = self.folders.get(folder_id)
        return folder.name if folder is not None else None
