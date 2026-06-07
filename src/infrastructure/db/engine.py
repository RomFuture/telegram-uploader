from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker


def sqlalchemy_dsn(postgres_dsn: str) -> str:
    if postgres_dsn.startswith("postgresql+psycopg://"):
        return postgres_dsn
    return postgres_dsn.replace("postgresql://", "postgresql+psycopg://", 1)


def build_db_session_factory(postgres_dsn: str) -> Callable[[], DbSession]:
    engine = create_engine(sqlalchemy_dsn(postgres_dsn), future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


@contextmanager
def db_session_scope(factory: Callable[[], DbSession]) -> Iterator[DbSession]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
