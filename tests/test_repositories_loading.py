from uuid import uuid4

import pytest

from domain.errors import DomainError
from use_cases.shared.repositories.loading import (
    require_archive_volume_record,
    require_archive_volumes_for_session,
    require_session_record,
    require_source_item_record,
)


def test_require_session_record_raises_when_missing() -> None:
    session_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        require_session_record(None, session_id)
    assert exc_info.value.code == "session_not_found"
    assert exc_info.value.entity_id == session_id


def test_require_source_item_record_raises_when_missing() -> None:
    item_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        require_source_item_record(None, item_id)
    assert exc_info.value.code == "source_item_not_found"
    assert exc_info.value.entity_id == item_id


def test_require_archive_volume_record_raises_when_missing() -> None:
    volume_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        require_archive_volume_record(None, volume_id)
    assert exc_info.value.code == "archive_volume_not_found"
    assert exc_info.value.entity_id == volume_id


def test_require_archive_volumes_for_session_raises_when_empty() -> None:
    session_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        require_archive_volumes_for_session([], session_id)
    error = exc_info.value
    assert error.code == "archive_volume_not_found"
    assert error.reason == "no_volumes"
    assert error.entity_id == session_id
