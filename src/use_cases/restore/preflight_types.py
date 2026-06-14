"""Restore preflight DTOs: reason codes and check outcome."""

from dataclasses import dataclass
from enum import StrEnum


class RestorePreflightReason(StrEnum):
    NO_VOLUMES = "no_volumes"
    EMPTY_FOLDER = "empty_folder"
    LEGACY_VOLUMES = "legacy_volumes"
    STALE_BACKUP = "stale_backup"
    INCOMPLETE_UPLOAD = "incomplete_upload"
    HEALTHCHECK_FAILED = "healthcheck_failed"
    READY = "ready"


@dataclass(frozen=True, slots=True)
class RestorePreflightResult:
    ready: bool
    reason: RestorePreflightReason
    restorable_count: int = 0
    incomplete_volume_count: int = 0
    legacy_volume_count: int = 0
