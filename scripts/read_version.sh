#!/usr/bin/env bash
# Print package version from pyproject.toml (for CI and packaging).
set -euo pipefail
python3 - <<'PY'
import pathlib
import re

text = pathlib.Path("pyproject.toml").read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
if not match:
    raise SystemExit("version not found in pyproject.toml")
print(match.group(1))
PY
