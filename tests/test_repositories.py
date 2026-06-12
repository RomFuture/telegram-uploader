from pathlib import Path
from uuid import uuid4

from domain.models import Session, SessionStatus, SourceItemStatus
from infrastructure.db.mappers import (
    archive_volume_row_to_record,
    source_item_row_to_record,
    upload_session_row_to_record,
)
from infrastructure.db.orm import ArchiveVolumeRow, SourceItemRow, UploadSessionRow
from infrastructure.db.sqlalchemy_repositories import SqlAlchemyRepositories
from use_cases.shared.mappers import (
    archive_volume_record_to_domain,
    session_record_to_domain,
    source_item_record_to_domain,
)
from use_cases.shared.repositories.session import SessionRepository


def test_repositories_bundle_from_dsn() -> None:
    repos = SqlAlchemyRepositories.from_dsn("postgresql://example")
    assert isinstance(repos.sessions, SessionRepository)


def test_record_mappers_round_trip_to_domain() -> None:
    session_id = uuid4()
    source_item_id = uuid4()
    volume_id = uuid4()
    created_at = Session.create("default", "secret").created_at

    session = session_record_to_domain(
        upload_session_row_to_record(
            UploadSessionRow(
                id=session_id,
                profile_name="default",
                encryption_key="secret",
                status=SessionStatus.CREATED.value,
                created_at=created_at,
            )
        )
    )
    assert session.id == session_id
    assert session.status == SessionStatus.CREATED

    source_item = source_item_record_to_domain(
        source_item_row_to_record(
            SourceItemRow(
                id=source_item_id,
                session_id=session_id,
                source_path="/tmp/holiday.mov",
                display_name="holiday.mov",
                status=SourceItemStatus.QUEUED.value,
                created_at=created_at,
            )
        )
    )
    assert source_item.display_name == "holiday.mov"
    assert source_item.source_path == Path("/tmp/holiday.mov")

    volume = archive_volume_record_to_domain(
        archive_volume_row_to_record(
            ArchiveVolumeRow(
                id=volume_id,
                source_item_id=source_item_id,
                file_name="abc.7z.001",
                local_path="/tmp/outgoing/abc.7z.001",
                part_number=1,
                status="uploaded",
                external_file_id="file-1",
                external_message_id="msg-1",
                provider_download_ref="download-1",
                created_at=created_at,
            )
        )
    )
    assert volume.external_file_id == "file-1"
