#!/usr/bin/env bash
# Resolve env file for packaged install (user-writable config first).
set -euo pipefail

PACKAGED_ENV_DIR="/etc/telegram-uploader"
PACKAGED_ENV_EXAMPLE="${PACKAGED_ENV_DIR}/env.example"
USER_ENV_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/telegram-uploader"
USER_ENV_FILE="${USER_ENV_DIR}/.env"

ensure_user_env() {
  if [[ -f "$USER_ENV_FILE" ]]; then
    return 0
  fi
  if [[ ! -f "$PACKAGED_ENV_EXAMPLE" ]]; then
    return 1
  fi
  mkdir -p "$USER_ENV_DIR"
  cp "$PACKAGED_ENV_EXAMPLE" "$USER_ENV_FILE"
  chmod 600 "$USER_ENV_FILE"
  echo "Created ${USER_ENV_FILE} — open Settings in the GUI to configure Telegram."
}

resolve_env_file() {
  if [[ -f "$USER_ENV_FILE" ]]; then
    echo "$USER_ENV_FILE"
    return 0
  fi
  if ensure_user_env; then
    echo "$USER_ENV_FILE"
    return 0
  fi
  if [[ -f "${PACKAGED_ENV_DIR}/.env" ]]; then
    echo "${PACKAGED_ENV_DIR}/.env"
    return 0
  fi
  return 1
}

load_env_file() {
  local env_file="$1"
  if [[ ! -r "$env_file" ]]; then
    echo "warning: cannot read ${env_file} — using defaults; configure in GUI Settings." >&2
    return 0
  fi
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}
