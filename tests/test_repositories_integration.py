import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from infrastructure.db.migrate import apply_migrations
from infrastructure.db.sqlalchemy_repositories import SqlAlchemyRepositories
from use_cases.persistence import SessionRecord


@pytest.fixture
def postgres_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "telegram_uploader")
    user = os.getenv("POSTGRES_USER", "telegram_uploader")
    password = os.getenv("POSTGRES_PASSWORD", "telegram_uploader")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.mark.integration
def test_session_crud_round_trip(postgres_dsn: str) -> None:
    apply_migrations(postgres_dsn)
    repos = SqlAlchemyRepositories.from_dsn(postgres_dsn)
    record = SessionRecord(
        id=uuid4(),
        profile_name="integration-test",
        encryption_key="secret",
        status="created",
        created_at=datetime.now(tz=UTC),
    )
    repos.sessions.add(record)
    loaded = repos.sessions.get(record.id)
    assert loaded is not None
    assert loaded.profile_name == "integration-test"
    assert loaded.encryption_key == "secret"
