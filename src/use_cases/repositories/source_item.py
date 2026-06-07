from typing import Protocol, runtime_checkable
from uuid import UUID

from use_cases.persistence import SourceItemRecord


@runtime_checkable
class SourceItemRepository(Protocol):
    def add(self, record: SourceItemRecord) -> None: ...

    def get(self, source_item_id: UUID) -> SourceItemRecord | None: ...

    def list_by_session(self, session_id: UUID) -> list[SourceItemRecord]: ...

    def update(self, record: SourceItemRecord) -> None: ...
