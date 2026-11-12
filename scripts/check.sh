#!/usr/bin/env bash
# The full check: stage a wheel-capable Python, run the receipted local pipeline
# (scripts/pipeline.py: push -> unit -> integration -> e2e -> perf; ship stays
# human by design), then the full-history secret scan that the pipeline's push
# tier deliberately scopes to the tree only.
#
#   scripts/check.sh
#
# Needs python3 (3.9+) with pytest. The offline wheel test also needs an installed
# Python with setuptools>=61 and wheel; select one locally rather than building
# an empty wheel under macOS's older system setuptools. Nothing is downloaded.
# The demo (scripts/demo.sh) installs into a throwaway home (--home), never yours;
# it runs inside the pipeline's e2e tier.
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

echo "== pipeline (receipted: push, unit, integration, e2e incl. the demo, perf)"
rc=0
python3 scripts/pipeline.py || rc=$?
if [ "$rc" -eq 1 ]; then
  echo "CHECK: FAIL — the pipeline's verdict is FAIL; the receipt above names the tier" >&2
  exit 1
fi
# exit 2 = INCOMPLETE; acceptable only when ship (human promotion) is the sole
# tier that did not run — the verifier enforces that against the receipt.
receipt="$(ls -t .harness-work/eval-pipeline-20261110/runs/run-*.json | head -1)"
python3 scripts/pipeline.py verify "$receipt" --allow-not-run ship

echo "== secret scan (full history; the pipeline's push tier scans the tree only)"
bash scripts/secret-scan.sh

echo "CHECK: PASS"
