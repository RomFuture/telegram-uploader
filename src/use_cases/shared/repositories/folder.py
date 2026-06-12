from typing import Protocol, runtime_checkable
from uuid import UUID

from use_cases.shared.persistence import BackupFolderRecord


@runtime_checkable
class FolderRepository(Protocol):
    def add(self, record: BackupFolderRecord) -> None: ...

    def get(self, folder_id: UUID) -> BackupFolderRecord | None: ...

    def list_by_session(self, session_id: UUID) -> list[BackupFolderRecord]: ...

    def find_by_name(self, session_id: UUID, name: str) -> BackupFolderRecord | None: ...
