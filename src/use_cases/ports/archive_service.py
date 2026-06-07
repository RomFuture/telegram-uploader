from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ArchiveVolumePart:
    part_number: int
    outgoing_path: Path
    outgoing_file_name: str


@dataclass(frozen=True, slots=True)
class ArchiveServiceResult:
    volumes: list[ArchiveVolumePart]
    work_dir: Path
    manifest_path: Path
    encryption_key_used: str


class ArchiveServicePort(Protocol):
    def archive(
        self,
        source_path: Path,
        output_dir: Path,
        display_name: str,
        encryption_key: str | None = None,
        *,
        source_item_id: str | None = None,
    ) -> ArchiveServiceResult: ...
