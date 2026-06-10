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

  if is_placeholder "${TELEGRAM_API_ID:-}" || ! [[ "${TELEGRAM_API_ID:-}" =~ ^[0-9]+$ ]]; then
    errors+=("TELEGRAM_API_ID must be a numeric api_id from https://my.telegram.org")
  fi
  if is_placeholder "${TELEGRAM_API_HASH:-}"; then
    errors+=("TELEGRAM_API_HASH must be your api_hash from https://my.telegram.org")
  fi
  if is_placeholder "${TELEGRAM_BOT_TOKEN:-}"; then
    errors+=("TELEGRAM_BOT_TOKEN must be the bot token from @BotFather")
  fi
  if is_placeholder "${TELEGRAM_TARGET_CHAT_ID:-}"; then
    errors+=("TELEGRAM_TARGET_CHAT_ID must be the numeric id of your backup group")
  fi

  if ((${#errors[@]} == 0)); then
    return 0
  fi

  echo "error: telegram-bot-api and backup need real Telegram credentials in .env:" >&2
  for msg in "${errors[@]}"; do
    echo "  - $msg" >&2
  done
  echo >&2
  echo "Setup guide: docs/TELEGRAM_SETUP.md" >&2
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

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "error: ${PYTHON} not found — create .venv and run: pip install -e '.[dev]'" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src"
exec "$PYTHON" -m application.gui
