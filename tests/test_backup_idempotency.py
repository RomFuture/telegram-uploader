from pathlib import Path

import domain as domain
from use_cases.backup.idempotency import (
    ArchiveStepAction,
    CleanupStepAction,
    UploadStepAction,
    decide_archive_on_retry,
    decide_cleanup_on_retry,
    decide_upload_on_retry,
)


def test_decide_archive_on_retry_for_queued_and_uploading() -> None:
    session_id = domain.create_session("default", "secret").id
    queued = domain.create_source_item(session_id, Path("/tmp/a.bin"), "A")
    assert decide_archive_on_retry(queued) == ArchiveStepAction.RUN

    uploading = domain.mark_source_item(queued, status=domain.SourceItemStatus.UPLOADING)
    assert decide_archive_on_retry(uploading) == ArchiveStepAction.SKIP


def test_decide_upload_on_retry_for_created_and_uploaded() -> None:
    volume = domain.create_archive_volume(
        source_item_id=domain.create_session("default", "secret").id,
        file_name="a.7z.001",
        local_path=Path("/tmp/a.7z.001"),
        part_number=1,
    )
    assert decide_upload_on_retry(volume) == UploadStepAction.RUN

    uploaded = domain.mark_archive_volume_uploaded(
        volume,
        external_file_id="f",
        external_message_id="m",
        provider_download_ref="r",
    )
    assert decide_upload_on_retry(uploaded) == UploadStepAction.SKIP


def test_decide_cleanup_on_retry_skips_completed_item() -> None:
    session_id = domain.create_session("default", "secret").id
    item = domain.mark_source_item(
        domain.create_source_item(session_id, Path("/tmp/a.bin"), "A"),
        status=domain.SourceItemStatus.COMPLETED,
    )
    volume = domain.create_archive_volume(
        source_item_id=item.id,
        file_name="a.7z.001",
        local_path=Path("/tmp/a.7z.001"),
        part_number=1,
    )
    assert decide_cleanup_on_retry(volume, item) == CleanupStepAction.SKIP
