from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from use_cases.backup.cleanup_volume import CleanupVolumeUseCase
from use_cases.backup.process_archive_volume import ProcessArchiveVolumeUseCase
from use_cases.backup.process_upload_volume import ProcessUploadVolumeUseCase
from use_cases.backup.report_failure import (
    ReportArchiveFailureUseCase,
    ReportCleanupFailureUseCase,
    ReportUploadFailureUseCase,
)
from use_cases.restore.process_restore_volume import ProcessRestoreVolumeUseCase


@dataclass(frozen=True, slots=True)
class WorkerApi:
    process_archive_uc: ProcessArchiveVolumeUseCase
    process_upload_uc: ProcessUploadVolumeUseCase
    process_cleanup_uc: CleanupVolumeUseCase
    process_restore_volume_uc: ProcessRestoreVolumeUseCase
    report_archive_failure_uc: ReportArchiveFailureUseCase
    report_upload_failure_uc: ReportUploadFailureUseCase
    report_cleanup_failure_uc: ReportCleanupFailureUseCase

    def process_archive(self, source_item_id: UUID) -> None:
        self.process_archive_uc.execute(source_item_id)

    def process_upload(self, archive_volume_id: UUID) -> None:
        self.process_upload_uc.execute(archive_volume_id)

    def process_cleanup(self, archive_volume_id: UUID) -> None:
        self.process_cleanup_uc.execute(archive_volume_id)

    def process_restore_volume(self, archive_volume_id: UUID) -> Path:
        return self.process_restore_volume_uc.execute(archive_volume_id)

    def report_archive_failure(self, source_item_id: UUID) -> None:
        self.report_archive_failure_uc.execute(source_item_id)

    def report_upload_failure(self, archive_volume_id: UUID) -> None:
        self.report_upload_failure_uc.execute(archive_volume_id)

    def report_cleanup_failure(self, source_item_id: UUID) -> None:
        self.report_cleanup_failure_uc.execute(source_item_id)

    def report_cleanup_failure_for_volume(self, archive_volume_id: UUID) -> None:
        volume = self.process_cleanup_uc.archive_volumes.require(archive_volume_id)
        self.report_cleanup_failure(volume.source_item_id)
