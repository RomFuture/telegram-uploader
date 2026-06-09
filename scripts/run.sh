#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose up -d

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "error: ${PYTHON} not found — create .venv and run: pip install -e '.[dev]'" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src"
exec "$PYTHON" -m application.gui
