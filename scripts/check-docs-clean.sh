#!/usr/bin/env bash
# Fail if any known-sensitive CHPL/internal token appears in the published docs.
# Usage: check-docs-clean.sh [DIR ...]   (defaults to docs/ and examples/)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=("$ROOT/docs")
  [ -d "$ROOT/examples" ] && TARGETS+=("$ROOT/examples")
fi

# Fail closed: a missing target directory is an error, not a silent pass —
# otherwise grep's "no such file" (exit 2) inside the if below reads as "no
# match" and the guard would wrongly report the docs clean.
for target in "${TARGETS[@]}"; do
  if [ ! -d "$target" ]; then
    echo "ERROR: target directory does not exist: $target" >&2
    exit 2
  fi
done

# Case-insensitive denylist. Patterns are extended regex (grep -E).
DENYLIST=(
  'cincinnatilibrary'
  'plch'
  'chpl'
  'sqldaia'
  'ray\.voelker'
  'sierra-app-rh8'
  'ils-reports'
  'qumulo'
  '\bdaia\b'
  '10\.110\.10\.'
  '\b1320201\b'
  '\b1290754\b'
  '\b1737745\b'
  '\b2198439\b'
  '\b21984396\b'
  'RV/ILS'
)

status=0
for pattern in "${DENYLIST[@]}"; do
  if grep -rniE "$pattern" "${TARGETS[@]}" 2>/dev/null; then
    echo "LEAK: denylist pattern '$pattern' found above" >&2
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  echo "OK: docs clean — no sensitive tokens found"
fi
exit "$status"
