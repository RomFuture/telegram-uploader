import logging
from pathlib import Path
from uuid import uuid4

import pytest

from observation import restore_session_log


def test_log_restore_started(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    caplog.set_level(logging.INFO, logger="observation.restore.session")
    session_id = uuid4()
    restore_session_log.log_restore_started(
        session_id,
        tmp_path / "dest",
        "folder 'TEST'",
        item_count=1,
        volume_count=2,
    )
    assert any("restore started" in record.message for record in caplog.records)
    assert any("folder 'TEST'" in record.message for record in caplog.records)


def test_log_restore_complete(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="observation.restore.session")
    restore_session_log.log_restore_complete(uuid4(), "all files in session", extracted_count=1)
    assert any("restore complete" in record.message for record in caplog.records)
