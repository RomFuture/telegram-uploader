#!/usr/bin/env bash
# Build .deb from repo root. Requires nfpm on PATH (see release workflow).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  VERSION="$(python3 - <<'PY'
import pathlib
import re
text = pathlib.Path("pyproject.toml").read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
if not match:
    raise SystemExit("version not found in pyproject.toml")
print(match.group(1))
PY
)"
fi

STAGING="${ROOT}/dist/staging"
OUTPUT_DIR="${ROOT}/dist"
NFPM_CONFIG="${ROOT}/dist/nfpm.generated.yaml"

rm -rf "$STAGING"
mkdir -p "$STAGING/opt/telegram-uploader/scripts" "$STAGING/opt/telegram-uploader/share" "$STAGING/etc/telegram-uploader" "$STAGING/usr/share/doc/telegram-uploader"

cp -a src pyproject.toml README.md docker-compose.yml Dockerfile "$STAGING/opt/telegram-uploader/"
cp packaging/assets/client_api_test.md "$STAGING/opt/telegram-uploader/share/"
if [[ -f scripts/telegram_client_spike.py ]]; then
  cp scripts/telegram_client_spike.py "$STAGING/opt/telegram-uploader/scripts/"
fi
cp .env.example "$STAGING/etc/telegram-uploader/env.example"
gzip -c README.md > "$STAGING/usr/share/doc/telegram-uploader/README.gz"

if ! command -v nfpm >/dev/null 2>&1; then
  echo "error: nfpm not found. Install from https://nfpm.goreleaser.com/" >&2
  exit 1
fi

export VERSION STAGING
envsubst '${VERSION} ${STAGING}' < packaging/nfpm.yaml > "$NFPM_CONFIG"

mkdir -p "$OUTPUT_DIR"
DEB="${OUTPUT_DIR}/telegram-uploader_${VERSION}_amd64.deb"
nfpm pkg --config "$NFPM_CONFIG" --packager deb --target "$DEB"

echo "Built ${DEB}"
