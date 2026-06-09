#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose up -d --build
docker compose restart \
  celery-worker-archive-1 \
  celery-worker-archive-2 \
  celery-worker-upload \
  celery-worker-cleanup \
  celery-worker-restore

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "error: ${PYTHON} not found — create .venv and run: pip install -e '.[dev]'" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src"
exec "$PYTHON" -m application.gui
