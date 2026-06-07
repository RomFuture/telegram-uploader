from typing import Protocol, runtime_checkable
from uuid import UUID

from domain.models import SourceItem
from use_cases.persistence import SourceItemRecord


@runtime_checkable
class SourceItemRepository(Protocol):
    def add(self, record: SourceItemRecord) -> None: ...

    def get(self, source_item_id: UUID) -> SourceItemRecord | None: ...

    def require(self, source_item_id: UUID) -> SourceItem: ...

    def list_by_session(self, session_id: UUID) -> list[SourceItemRecord]: ...

    def list_domain_by_session(self, session_id: UUID) -> list[SourceItem]: ...

    def update(self, record: SourceItemRecord) -> None: ...
