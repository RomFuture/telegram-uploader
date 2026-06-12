#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

require_env_file() {
  if [[ -f .env ]]; then
    return 0
  fi
  cat >&2 <<'EOF'
error: .env not found.

  cp .env.example .env

Then configure Telegram credentials (required before docker compose):
  docs/TELEGRAM_SETUP.md
EOF
  exit 1
}

load_env() {
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
}

is_placeholder() {
  local value="${1:-}"
  case "$value" in
    "" | change_me | your_api_hash_here | change_me_or_leave_empty_for_auto) return 0 ;;
    *) return 1 ;;
  esac
}

validate_telegram_setup() {
  local errors=()
  local provider="${TELEGRAM_PROVIDER:-client}"

  if is_placeholder "${TELEGRAM_TARGET_CHAT_ID:-}"; then
    errors+=("TELEGRAM_TARGET_CHAT_ID must be the numeric id of your backup group")
  fi

  if [[ "$provider" == "client" ]]; then
    if is_placeholder "${TELEGRAM_API_ID:-}" || ! [[ "${TELEGRAM_API_ID:-}" =~ ^[0-9]+$ ]]; then
      errors+=("TELEGRAM_API_ID must be a numeric api_id from https://my.telegram.org")
    fi
    if is_placeholder "${TELEGRAM_API_HASH:-}"; then
      errors+=("TELEGRAM_API_HASH must be your api_hash from https://my.telegram.org")
    fi
  else
    if is_placeholder "${TELEGRAM_API_ID:-}" || ! [[ "${TELEGRAM_API_ID:-}" =~ ^[0-9]+$ ]]; then
      errors+=("TELEGRAM_API_ID must be a numeric api_id from https://my.telegram.org")
    fi
    if is_placeholder "${TELEGRAM_API_HASH:-}"; then
      errors+=("TELEGRAM_API_HASH must be your api_hash from https://my.telegram.org")
    fi
    if is_placeholder "${TELEGRAM_BOT_TOKEN:-}"; then
      errors+=("TELEGRAM_BOT_TOKEN must be the bot token from @BotFather (or set TELEGRAM_PROVIDER=client)")
    fi
  fi

  if ((${#errors[@]} == 0)); then
    return 0
  fi

  echo "error: Telegram credentials missing or invalid in .env:" >&2
  for msg in "${errors[@]}"; do
    echo "  - $msg" >&2
  done
  echo >&2
  echo "Setup guide: docs/TELEGRAM_SETUP.md" >&2
  if [[ "${TELEGRAM_PROVIDER:-client}" == "client" ]]; then
    echo "Client API auth (once): PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only" >&2
  fi
  exit 1
}

require_env_file
load_env
validate_telegram_setup

if ! docker compose up -d --build; then
  echo "error: docker compose failed. Recent telegram-bot-api logs:" >&2
  docker compose logs --tail=30 telegram-bot-api >&2 || true
  exit 1
fi
docker compose restart \
  celery-worker-archive-1 \
  celery-worker-archive-2 \
  celery-worker-upload \
  celery-worker-cleanup \
  celery-worker-restore

session_path="${TELEGRAM_SESSION_PATH:-/tmp/telegram_uploader/session.session}"
session_dir="${TELEGRAM_SESSION_DIR:-$(dirname "$session_path")}"
mkdir -p "$session_dir"
if [[ "${TELEGRAM_PROVIDER:-client}" == "client" && ! -f "$session_path" ]]; then
  echo "warning: Client API session not found at $session_path" >&2
  echo "  Run: PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only" >&2
  echo "  Workers share this file via TELEGRAM_SESSION_DIR=$session_dir (see .env)" >&2
fi

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "error: ${PYTHON} not found — create .venv and run: pip install -e '.[dev]'" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src"
echo "Applying database migrations..."
"$PYTHON" -c "from infrastructure.config import load_config; from infrastructure.db.migrate import apply_migrations; apply_migrations(load_config().postgres_dsn)"
echo "Starting GUI (Unlock → folders → backup/restore)..."
echo "Client API default. Authenticate once:"
echo "  PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only"
exec "$PYTHON" -m application.gui
