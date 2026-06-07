from dataclasses import dataclass
from pathlib import Path

from infrastructure.archive.seven_zip_service import SevenZipService
from use_cases.ports.archive_service import ArchiveServiceResult, ArchiveVolumePart


@dataclass(frozen=True, slots=True)
class ArchiveServiceAdapter:
    service: SevenZipService

    def archive(
        self,
        source_path: Path,
        output_dir: Path,
        display_name: str,
        encryption_key: str | None = None,
        *,
        source_item_id: str | None = None,
    ) -> ArchiveServiceResult:
        result = self.service.archive(
            source_path=source_path,
            output_dir=output_dir,
            display_name=display_name,
            encryption_key=encryption_key,
            source_item_id=source_item_id,
        )
        return ArchiveServiceResult(
            volumes=[
                ArchiveVolumePart(
                    part_number=volume.part_number,
                    outgoing_path=volume.outgoing_path,
                    outgoing_file_name=volume.outgoing_file_name,
                )
                for volume in result.volumes
            ],
            work_dir=result.work_dir,
            manifest_path=result.manifest_path,
            encryption_key_used=result.encryption_key_used,
        )
