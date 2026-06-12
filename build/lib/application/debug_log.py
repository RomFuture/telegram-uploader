"""Debug logging for agent sessions (remove after fix verified)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

_SESSION_ID = "5d237b"
_LOG_PATHS = (
    Path("/home/romfuture/Projects/Personal/telegram-uploader/.cursor/debug-5d237b.log"),
    Path.home() / ".config" / "telegram-uploader" / "debug-5d237b.log",
    Path("/tmp/telegram-uploader-debug-5d237b.log"),
)


def agent_debug(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, object],
    *,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    entry = {
        "sessionId": _SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(entry, default=str) + "\n"
    for path in _LOG_PATHS:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
            return
        except OSError:
            continue
    # endregion


def path_diagnostics(path: Path) -> dict[str, object]:
    parent = path.parent
    info: dict[str, object] = {
        "path": str(path),
        "resolved": str(path.resolve()),
        "cwd": os.getcwd(),
        "home": str(Path.home()),
        "xdg_config_home": os.environ.get("XDG_CONFIG_HOME", ""),
        "parent": str(parent),
        "parent_exists": parent.exists(),
        "parent_is_dir": parent.is_dir(),
    }
    if parent.exists():
        try:
            stat = parent.stat()
            info["parent_uid"] = stat.st_uid
            info["parent_gid"] = stat.st_gid
            info["parent_mode"] = oct(stat.st_mode)
        except OSError as error:
            info["parent_stat_error"] = str(error)
        info["parent_writable"] = os.access(parent, os.W_OK)
    if path.exists():
        info["path_exists"] = True
        info["path_is_dir"] = path.is_dir()
    return info
