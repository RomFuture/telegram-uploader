"""Observation: progress and heartbeat logging for long restore downloads.

Not restore business policy (scope, refs, writable dest). Lives under
``observation/`` because it only decides *when* to log bytes received during
``StorageProviderPort.download_file(on_progress=...)``. Wired from
``RestoreSessionUseCase``; infra forwards the callback to Telethon unchanged.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

logger = logging.getLogger("observation.restore.download")

DEFAULT_HEARTBEAT_SECONDS = 30.0


def make_download_progress_callback(
    *,
    label: str,
    heartbeat_seconds: float = DEFAULT_HEARTBEAT_SECONDS,
) -> Callable[[int, int], None]:
    """Return a Telethon-compatible ``progress_callback(received, total)``."""

    started = time.monotonic()
    last_log_at = started
    last_pct_bucket = -1

    def callback(received: int, total: int) -> None:
        nonlocal last_log_at, last_pct_bucket
        now = time.monotonic()
        if total > 0:
            pct = received * 100 // total
            pct_bucket = min(pct // 10, 9)
            if pct_bucket > last_pct_bucket:
                logger.info(
                    "download progress %s %d%% (%d/%d bytes) elapsed=%.0fs",
                    label,
                    pct,
                    received,
                    total,
                    now - started,
                )
                last_pct_bucket = pct_bucket
                last_log_at = now
                return
            if received >= total and pct_bucket >= last_pct_bucket:
                logger.info(
                    "download complete %s %d/%d bytes (100%%) elapsed=%.0fs",
                    label,
                    received,
                    total,
                    now - started,
                )
                last_log_at = now
                return
        if now - last_log_at >= heartbeat_seconds:
            if total > 0:
                logger.info(
                    "download in progress %s %d/%d bytes elapsed=%.0fs (heartbeat)",
                    label,
                    received,
                    total,
                    now - started,
                )
            else:
                logger.info(
                    "download in progress %s received=%d bytes elapsed=%.0fs (heartbeat)",
                    label,
                    received,
                    now - started,
                )
            last_log_at = now

    return callback
