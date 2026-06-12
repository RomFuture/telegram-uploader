#!/bin/sh
# Runtime dependency checks for packaged telegram-uploader (.deb).
# Usage: check-deps.sh [--warn-only]
# Exit 0 when OK, 1 when required tools are missing (unless --warn-only).

set -e

WARN_ONLY=0
if [ "${1:-}" = "--warn-only" ]; then
  WARN_ONLY=1
fi

MISSING=""
WARNINGS=""

add_missing() {
  MISSING="${MISSING}  - $1\n"
}

add_warning() {
  WARNINGS="${WARNINGS}  - $1\n"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

# Docker CLI (docker.io or docker-ce)
if ! have_cmd docker; then
  add_missing "docker — install: sudo apt install docker.io"
fi

# Compose v2 (plugin) or legacy docker-compose
if have_cmd docker; then
  if ! docker compose version >/dev/null 2>&1; then
    if ! have_cmd docker-compose; then
      add_missing "docker compose — install: sudo apt install docker-compose-plugin"
    fi
  fi
elif ! have_cmd docker-compose; then
  add_missing "docker compose — install: sudo apt install docker-compose-plugin docker.io"
fi

# Python + venv + Tkinter GUI
if ! have_cmd python3; then
  add_missing "python3 — install: sudo apt install python3 python3-venv python3-tk"
else
  if ! python3 -c "import venv" 2>/dev/null; then
    add_missing "python3-venv — install: sudo apt install python3-venv"
  fi
  if ! python3 -c "import tkinter" 2>/dev/null; then
    add_missing "python3-tk (Tkinter GUI) — install: sudo apt install python3-tk"
  fi
  PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
  PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
  if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
    add_missing "Python 3.12+ (found ${PY_MAJOR}.${PY_MINOR}) — Ubuntu 24.04 recommended"
  fi
fi

# 7z for archive workers
if ! have_cmd 7z; then
  add_missing "p7zip (7z) — install: sudo apt install p7zip-full"
fi

# Docker daemon (installed but not running / no permission)
if have_cmd docker; then
  if ! docker info >/dev/null 2>&1; then
    add_warning "Docker daemon not reachable. Try: sudo systemctl start docker"
    add_warning "Add your user to group docker, re-login: sudo usermod -aG docker \$USER"
  fi
fi

print_block() {
  title="$1"
  body="$2"
  if [ -n "$body" ]; then
    printf '%s\n' "$title" >&2
    printf '%b' "$body" >&2
    printf '\n' >&2
  fi
}

if [ -n "$MISSING" ]; then
  print_block "telegram-uploader: missing required packages:" "$MISSING"
  cat >&2 <<'EOF'
Install dependencies, then configure the package:

  sudo apt update
  sudo apt install docker.io docker-compose-plugin python3 python3-venv python3-tk p7zip-full
  sudo apt -f install   # if you used dpkg -i and dependencies are half-configured

Prefer installing the .deb with apt (pulls Depends automatically):

  sudo apt install ./telegram-uploader_*_amd64.deb

EOF
  if [ "$WARN_ONLY" -eq 1 ]; then
    exit 0
  fi
  exit 1
fi

if [ -n "$WARNINGS" ]; then
  print_block "telegram-uploader: warnings:" "$WARNINGS"
fi

exit 0
