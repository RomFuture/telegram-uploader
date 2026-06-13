"""Central logging configuration for GUI and worker processes."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
_CONFIGURED = False


def setup_logging(*, log_file: Path, level: str, also_console: bool = True) -> None:
    """Configure root logger with file (+ optional stdout) handlers.

    Idempotent: safe to call from GUI, bootstrap, and each Celery worker process.
    Do not log secrets (tokens, encryption keys) at call sites.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    resolved_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT)

    root = logging.getLogger()
    root.setLevel(resolved_level)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if also_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    _CONFIGURED = True


def reset_logging_for_tests() -> None:
    """Clear handlers and config flag (tests only)."""
    global _CONFIGURED
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    _CONFIGURED = False
