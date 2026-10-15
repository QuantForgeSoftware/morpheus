#!/usr/bin/env bash
#
# Build a distributable wheel (and sdist) of morpheus-toolkit locally.
# No GitHub / network required beyond whatever the build backend needs:
# uses --no-build-isolation so it works with the repo venv.
#
# Usage: scripts/package.sh            # -> dist/
#        PYTHON=.venv/bin/python scripts/package.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$ROOT/dist}"
PY="${PYTHON:-python3}"

mkdir -p "$OUT"
"$PY" -m pip wheel "$ROOT/python" --no-deps --no-build-isolation -w "$OUT"
echo "Built distribution in $OUT:"
ls -1 "$OUT"
