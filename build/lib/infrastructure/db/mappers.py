from infrastructure.db.orm import ArchiveVolumeRow, BackupFolderRow, SourceItemRow, UploadSessionRow
from use_cases.shared.persistence import (
    ArchiveVolumeRecord,
    BackupFolderRecord,
    SessionRecord,
    SourceItemRecord,
)


def upload_session_row_to_record(row: UploadSessionRow) -> SessionRecord:
    return SessionRecord(
        id=row.id,
        profile_name=row.profile_name,
        encryption_key=row.encryption_key,
        status=row.status,
        created_at=row.created_at,
    )


def record_to_upload_session_row(record: SessionRecord) -> UploadSessionRow:
    return UploadSessionRow(
        id=record.id,
        profile_name=record.profile_name,
        encryption_key=record.encryption_key,
        status=record.status,
        created_at=record.created_at,
    )


def source_item_row_to_record(row: SourceItemRow) -> SourceItemRecord:
    return SourceItemRecord(
        id=row.id,
        session_id=row.session_id,
        source_path=row.source_path,
        display_name=row.display_name,
        status=row.status,
        created_at=row.created_at,
        folder_id=row.folder_id,
    )


def record_to_source_item_row(record: SourceItemRecord) -> SourceItemRow:
    return SourceItemRow(
        id=record.id,
        session_id=record.session_id,
        source_path=record.source_path,
        display_name=record.display_name,
        status=record.status,
        created_at=record.created_at,
        folder_id=record.folder_id,
    )


def backup_folder_row_to_record(row: BackupFolderRow) -> BackupFolderRecord:
    return BackupFolderRecord(
        id=row.id,
        session_id=row.session_id,
        name=row.name,
        created_at=row.created_at,
    )


def record_to_backup_folder_row(record: BackupFolderRecord) -> BackupFolderRow:
    return BackupFolderRow(
        id=record.id,
        session_id=record.session_id,
        name=record.name,
        created_at=record.created_at,
    )


def archive_volume_row_to_record(row: ArchiveVolumeRow) -> ArchiveVolumeRecord:
    return ArchiveVolumeRecord(
        id=row.id,
        source_item_id=row.source_item_id,
        file_name=row.file_name,
        local_path=row.local_path,
        part_number=row.part_number,
        status=row.status,
        external_file_id=row.external_file_id,
        external_message_id=row.external_message_id,
        provider_download_ref=row.provider_download_ref,
        created_at=row.created_at,
    )


def record_to_archive_volume_row(record: ArchiveVolumeRecord) -> ArchiveVolumeRow:
    return ArchiveVolumeRow(
        id=record.id,
        source_item_id=record.source_item_id,
        file_name=record.file_name,
        local_path=record.local_path,
        part_number=record.part_number,
        status=record.status,
        external_file_id=record.external_file_id,
        external_message_id=record.external_message_id,
        provider_download_ref=record.provider_download_ref,
        created_at=record.created_at,
    )
