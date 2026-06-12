from __future__ import annotations

import json
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class SevenZipError(RuntimeError):
    """7-Zip subprocess failed (check stderr in ``__cause__`` context)."""


def generate_archive_key(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def build_hashed_volume_name(display_name: str, part_number: int) -> str:
    # Hotfix: restore download is not working yet; users pull volumes from Telegram by hand.
    # Hashed names are unreadable in the chat. Re-enable when restore ships.
    # hashed = hashlib.sha256(display_name.encode("utf-8")).hexdigest()[:12]
    # return f"{hashed}.7z.{part_number:03d}"
    return f"{display_name}.7z.{part_number:03d}"


@dataclass(frozen=True, slots=True)
class OutgoingVolume:
    """One split 7z part in ``outgoing/``, ready for upload (not a domain/DB entity)."""

    part_number: int
    outgoing_path: Path
    outgoing_file_name: str


@dataclass(frozen=True, slots=True)
class ArchivePipelineResult:
    """Encrypted split volumes and deterministic order manifest."""

    volumes: list[OutgoingVolume]
    work_dir: Path
    manifest_path: Path
    encryption_key_used: str


@dataclass(frozen=True, slots=True)
class SevenZipService:
    executable: str = "7z"
    volume_size: str = "1999m"

    def archive(
        self,
        source_path: Path,
        output_dir: Path,
        display_name: str,
        encryption_key: str | None = None,
        *,
        source_item_id: str | None = None,
    ) -> ArchivePipelineResult:
        """Archive, encrypt and split source_path into upload-ready volumes.

        Directory layout under output_dir/<scope>/:
          raw/       - volumes as produced by 7z (payload.7z.001, .002, …)
          outgoing/  - volumes renamed for upload (display_name + part suffix; hash disabled hotfix)
          volume_manifest.json
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        key = encryption_key or generate_archive_key()
        scope = source_item_id or secrets.token_hex(8)
        work_dir = output_dir / scope
        raw_dir = work_dir / "raw"
        outgoing_dir = work_dir / "outgoing"
        raw_dir.mkdir(parents=True, exist_ok=True)
        outgoing_dir.mkdir(parents=True, exist_ok=True)

        archive_base = raw_dir / "payload.7z"
        self._run_7z(source_path=source_path, archive_path=archive_base, encryption_key=key)

        raw_volumes = sorted(raw_dir.glob("payload.7z*"))
        archive_volumes: list[OutgoingVolume] = []
        for idx, raw_path in enumerate(raw_volumes, start=1):
            outgoing_name = build_hashed_volume_name(display_name, idx)
            outgoing_path = outgoing_dir / outgoing_name
            shutil.copy2(raw_path, outgoing_path)
            raw_path.unlink()
            archive_volumes.append(
                OutgoingVolume(
                    part_number=idx,
                    outgoing_path=outgoing_path,
                    outgoing_file_name=outgoing_name,
                )
            )

        manifest_path = work_dir / "volume_manifest.json"
        self._write_manifest(
            manifest_path=manifest_path,
            source_path=source_path,
            display_name=display_name,
            source_item_id=source_item_id,
            volumes=archive_volumes,
        )

        return ArchivePipelineResult(
            volumes=archive_volumes,
            work_dir=work_dir,
            manifest_path=manifest_path,
            encryption_key_used=key,
        )

    def extract(self, volume_paths: list[Path], dest_dir: Path, encryption_key: str) -> Path:
        """Decrypt and extract split archive volumes into dest_dir."""
        if not volume_paths:
            raise SevenZipError("no archive volumes to extract")

        dest_dir.mkdir(parents=True, exist_ok=True)
        existing_files = {path for path in dest_dir.iterdir() if path.is_file()}
        first_volume = volume_paths[0]
        command = [
            self.executable,
            "x",
            f"-p{encryption_key}",
            f"-o{dest_dir}",
            str(first_volume),
            "-y",
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip() or str(exc)
            raise SevenZipError(f"7z extract failed: {detail}") from exc

        new_files = {path for path in dest_dir.iterdir() if path.is_file()} - existing_files
        if len(new_files) != 1:
            raise SevenZipError(
                f"expected one new file in {dest_dir}, found {len(new_files)}"
            )
        return new_files.pop()

    def _run_7z(self, source_path: Path, archive_path: Path, encryption_key: str) -> None:
        command = [
            self.executable,
            "a",
            "-t7z",
            "-mhe=on",
            f"-v{self.volume_size}",
            f"-p{encryption_key}",
            str(archive_path),
            str(source_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip() or str(exc)
            raise SevenZipError(f"7z failed: {detail}") from exc

    def _write_manifest(
        self,
        manifest_path: Path,
        source_path: Path,
        display_name: str,
        source_item_id: str | None,
        volumes: list[OutgoingVolume],
    ) -> None:
        payload = {
            "source_path": str(source_path),
            "display_name": display_name,
            "source_item_id": source_item_id,
            "parts": [
                {
                    "part_number": volume.part_number,
                    "outgoing_file": volume.outgoing_file_name,
                }
                for volume in volumes
            ],
        }
        manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
