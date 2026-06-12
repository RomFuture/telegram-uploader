from pathlib import Path
from uuid import UUID

from use_cases.shared.dto import (
    ClassifiedProviderError,
    ProviderErrorCategory,
    ProviderFileInfo,
    ProviderLimits,
    UploadResult,
)
from use_cases.shared.ports.archive_service import ArchiveServiceResult, ArchiveVolumePart


class FakeTaskQueue:
    def __init__(self) -> None:
        self.archive_ids: list[UUID] = []
        self.upload_ids: list[UUID] = []
        self.cleanup_ids: list[UUID] = []
        self.restore_ids: list[UUID] = []

    def enqueue_archive(self, source_item_id: UUID) -> None:
        self.archive_ids.append(source_item_id)

    def enqueue_upload(self, archive_volume_id: UUID) -> None:
        self.upload_ids.append(archive_volume_id)

    def enqueue_cleanup(self, archive_volume_id: UUID) -> None:
        self.cleanup_ids.append(archive_volume_id)

    def enqueue_restore(self, archive_volume_id: UUID) -> None:
        self.restore_ids.append(archive_volume_id)


class FakeArchiveService:
    def __init__(self, volumes: list[ArchiveVolumePart] | None = None) -> None:
        self._volumes = volumes or []
        self.last_display_name: str | None = None
        self.archive_calls = 0

    def archive(
        self,
        source_path: Path,
        output_dir: Path,
        display_name: str,
        encryption_key: str | None = None,
        *,
        source_item_id: str | None = None,
    ) -> ArchiveServiceResult:
        self.archive_calls += 1
        self.last_display_name = display_name
        work_dir = output_dir / (source_item_id or "test-scope")
        work_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = work_dir / "volume_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        return ArchiveServiceResult(
            volumes=self._volumes,
            work_dir=work_dir,
            manifest_path=manifest_path,
            encryption_key_used=encryption_key or "generated-key",
        )

    def extract(self, volume_paths: list[Path], dest_dir: Path, encryption_key: str) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted = dest_dir / "restored.bin"
        extracted.write_bytes(b"restored-content")
        return extracted


class FakeStorageProvider:
    def __init__(self) -> None:
        self.uploaded_display_names: list[str] = []
        self.downloaded_files: list[Path] = []
        self.requested_refs: list[str] = []

    def healthcheck(self, remote_target: str) -> bool:
        return bool(remote_target)

    def upload_file(self, local_path: Path, remote_target: str, display_name: str) -> UploadResult:
        self.uploaded_display_names.append(display_name)
        file_id = f"file-{display_name}"
        return UploadResult(
            provider_name="fake",
            external_file_id=file_id,
            external_message_id="msg-1",
            provider_download_ref=f"ref-{file_id}",
            provider_file_name=display_name,
        )

    def get_file_info(self, external_file_id: str) -> ProviderFileInfo:
        self.requested_refs.append(external_file_id)
        return ProviderFileInfo(
            provider_name="fake",
            external_file_id=external_file_id,
            provider_download_ref=f"path/{external_file_id}",
            provider_file_name=f"{external_file_id}.7z.001",
            size_bytes=10,
        )

    def download_file(
        self, file_info: ProviderFileInfo, destination_path: Path, resume: bool = False
    ) -> Path:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(b"volume-bytes")
        self.downloaded_files.append(destination_path)
        return destination_path

    def classify_error(self, error: Exception) -> ClassifiedProviderError:
        return ClassifiedProviderError(category=ProviderErrorCategory.UNKNOWN, reason=str(error))

    def provider_limits(self) -> ProviderLimits:
        return ProviderLimits(
            max_upload_size_bytes=2_000_000_000,
            supports_resume_download=True,
            rate_limit_window_seconds=None,
            rate_limit_max_requests=None,
        )
