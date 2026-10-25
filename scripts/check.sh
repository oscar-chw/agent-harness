#!/usr/bin/env bash
# The full check: the test suite, the secret scan, and a demo of the install. Exits 0 only if all pass.
#
#   scripts/check.sh
#
# Needs python3 (3.9+) with pytest. The offline wheel test also needs an installed
# Python with setuptools>=61 and wheel; select one locally rather than building
# an empty wheel under macOS's older system setuptools. Nothing is downloaded.
# The demo (scripts/demo.sh) installs into a throwaway home (--home), never yours.
set -euo pipefail
cd "$(dirname "$0")/.."

staging_python_ok() {
  "$1" -I -c 'import importlib.metadata as m, sys; assert sys.version_info >= (3, 9) and int(m.version("setuptools").split(".")[0]) >= 61; m.version("wheel")' \
    >/dev/null 2>&1
}

if [ -n "${HARNESS_STAGING_PYTHON:-}" ]; then
  staging_python_ok "$HARNESS_STAGING_PYTHON" || {
    echo "CHECK: HARNESS_STAGING_PYTHON needs Python 3.9+, setuptools>=61 and wheel" >&2
    exit 2
  }
else
  for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10 python3.9; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    staging_python_ok "$candidate" || continue
    HARNESS_STAGING_PYTHON=$(command -v "$candidate")
    export HARNESS_STAGING_PYTHON
    break
  done
  [ -n "${HARNESS_STAGING_PYTHON:-}" ] || {
    echo "CHECK: no installed Python 3.9+ with setuptools>=61 and wheel for the offline wheel test" >&2
    exit 2
  }
fi
echo "== offline wheel build: $HARNESS_STAGING_PYTHON"

echo "== tests (the harness, the guard corpus, the eval instrument)"
python3 -m pytest -q tests eval

echo "== secret scan"
bash scripts/secret-scan.sh

echo "== demo (scripts/demo.sh: a throwaway home, never yours)"
bash scripts/demo.sh

echo "CHECK: PASS"
