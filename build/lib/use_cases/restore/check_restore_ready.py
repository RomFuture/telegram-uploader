"""Pre-flight checks before GUI restore."""

from dataclasses import dataclass
from uuid import UUID

import domain as domain
from use_cases.restore.refs import is_volume_restorable, restorable_source_item_ids
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.loading import map_archive_volumes

_STALE_BACKUP_MESSAGE = (
    "No restorable backups yet.\n\n"
    "{count} file(s) from a previous session did not finish uploading to Telegram.\n"
    "Click Start Backup to retry them.\n\n"
    "If upload keeps failing, check TELEGRAM_SESSION_DIR, chat id, and "
    "Settings → Client API → Test Client API."
)

_INCOMPLETE_UPLOAD_MESSAGE = (
    "Archive exists but Telegram upload did not finish.\n\n"
    "Check:\n"
    "1) Session file is shared with Docker (TELEGRAM_SESSION_DIR in .env)\n"
    "2) TELEGRAM_TARGET_CHAT_ID is correct\n"
    "3) Settings → Client API → Test Client API\n\n"
    "Worker logs: docker compose logs celery-worker-upload"
)

_HEALTHCHECK_FAIL_MESSAGE = (
    "Telegram Client API is not ready on this machine.\n\n"
    "Settings → Client API → Sign in to Telegram… (one time),\n"
    "then Test Client API.\n"
    "Or in a terminal: telegram-uploader-login"
)


@dataclass(frozen=True, slots=True)
class RestoreReadyResult:
    ready: bool
    message: str


@dataclass(frozen=True, slots=True)
class CheckRestoreReadyUseCase:
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    target_chat_id: str

    def execute(self, session_id: UUID) -> RestoreReadyResult:
        records = self.archive_volumes.list_by_session(session_id)
        if not records:
            return RestoreReadyResult(
                ready=False,
                message="No backup volumes found for this database. Run Start Backup first.",
            )

        volumes = map_archive_volumes(records)
        restorable_items = restorable_source_item_ids(volumes, self.target_chat_id)
        incomplete_volume_count = sum(
            1 for volume in volumes if not is_volume_restorable(volume, self.target_chat_id)
        )
        has_legacy_volumes = any(
            volume.status == domain.ArchiveVolumeStatus.UPLOADED
            and volume.provider_download_ref
            and not volume.provider_download_ref.startswith("client:")
            for volume in volumes
        )

        if not restorable_items:
            if has_legacy_volumes:
                return RestoreReadyResult(
                    ready=False,
                    message=(
                        "Re-backup required (legacy Bot API volumes). "
                        "Switch to TELEGRAM_PROVIDER=client and back up again."
                    ),
                )
            if incomplete_volume_count > 0:
                return RestoreReadyResult(
                    ready=False,
                    message=_STALE_BACKUP_MESSAGE.format(count=incomplete_volume_count),
                )
            return RestoreReadyResult(
                ready=False,
                message=_INCOMPLETE_UPLOAD_MESSAGE,
            )

        try:
            provider_ok = self.storage_provider.healthcheck(self.target_chat_id)
        except Exception:
            provider_ok = False

        if not provider_ok:
            return RestoreReadyResult(
                ready=False,
                message=_HEALTHCHECK_FAIL_MESSAGE,
            )

        message = "Ready to restore."
        if incomplete_volume_count > 0:
            message = (
                f"Ready to restore {len(restorable_items)} file(s).\n\n"
                f"{incomplete_volume_count} unfinished archive part(s) from older "
                "failed backups will be skipped.\n"
                "Click Start Backup to retry those files."
            )
        return RestoreReadyResult(ready=True, message=message)
