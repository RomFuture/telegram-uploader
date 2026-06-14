"""Observation: milestone logging for RestoreSessionUseCase.

Cross-cutting log copy for restore orchestration. Safe to omit: restore behavior
does not depend on these calls. Wired from ``RestoreSessionUseCase`` only.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

logger = logging.getLogger("observation.restore.session")


def log_restore_started(
    session_id: UUID,
    dest_path: Path,
    scope_label: str,
    *,
    item_count: int,
    volume_count: int,
) -> None:
    logger.info(
        "restore started session_id=%s dest=%s scope=%s items=%d volumes=%d",
        session_id,
        dest_path,
        scope_label,
        item_count,
        volume_count,
    )


def log_download_starting(label: str) -> None:
    logger.info("download starting %s", label)


def log_download_finished(label: str, path: Path) -> None:
    logger.info("download finished %s -> %s", label, path)


def log_extract_starting(
    item_index: int,
    total_items: int,
    *,
    part_count: int,
    dest_path: Path,
) -> None:
    logger.info(
        "extract starting item %d/%d parts=%d dest=%s",
        item_index,
        total_items,
        part_count,
        dest_path,
    )


def log_extract_complete(item_index: int, total_items: int, extracted_path: Path) -> None:
    logger.info(
        "extract complete item %d/%d -> %s",
        item_index,
        total_items,
        extracted_path,
    )


def log_restore_complete(session_id: UUID, scope_label: str, *, extracted_count: int) -> None:
    logger.info(
        "restore complete session_id=%s scope=%s extracted=%d path(s)",
        session_id,
        scope_label,
        extracted_count,
    )
