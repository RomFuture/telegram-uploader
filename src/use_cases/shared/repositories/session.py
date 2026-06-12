from typing import Protocol, runtime_checkable
from uuid import UUID

from use_cases.shared.persistence import SessionRecord
from use_cases.shared.types import Session


@runtime_checkable
class SessionRepository(Protocol):
    def add(self, record: SessionRecord) -> None: ...

    def get(self, session_id: UUID) -> SessionRecord | None: ...

    def require(self, session_id: UUID) -> Session: ...

    def update(self, record: SessionRecord) -> None: ...

    def list_profiles(self) -> tuple[str, ...]: ...

    def find_by_profile_name(self, profile_name: str) -> SessionRecord | None: ...
