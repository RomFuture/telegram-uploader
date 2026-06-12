#!/usr/bin/env bash
# Verify git tag matches pyproject.toml version (e.g. tag v0.1.0 → 0.1.0).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TAG="${GITHUB_REF_NAME:-${1:-}}"
if [[ -z "$TAG" ]]; then
  echo "error: pass tag as argument or set GITHUB_REF_NAME" >&2
  exit 1
fi

if [[ "$TAG" != v* ]]; then
  echo "error: expected tag v* got ${TAG}" >&2
  exit 1
fi

EXPECTED="${TAG#v}"
ACTUAL="$(python3 - <<'PY'
import pathlib
import re
text = pathlib.Path("pyproject.toml").read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
if not match:
    raise SystemExit("version not found in pyproject.toml")
print(match.group(1))
PY
)"

if [[ "$EXPECTED" != "$ACTUAL" ]]; then
  echo "error: tag ${TAG} (version ${EXPECTED}) != pyproject.toml version ${ACTUAL}" >&2
  exit 1
fi

echo "Version OK: ${ACTUAL}"
