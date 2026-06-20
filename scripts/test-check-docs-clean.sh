#!/usr/bin/env bash
# Self-test for check-docs-clean.sh: clean content passes, seeded token fails.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$SCRIPT_DIR/check-docs-clean.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Case 1: clean content must pass (exit 0).
echo "Public docs about the Sierra REST API and varFields." > "$TMP/clean.md"
if "$CHECK" "$TMP" >/dev/null 2>&1; then
  echo "PASS: clean fixture accepted"
else
  echo "FAIL: clean fixture was wrongly flagged" >&2
  exit 1
fi

# Case 2: a seeded internal hostname must be caught (exit non-zero).
echo "the internal host sierra-app-rh8 must be caught" > "$TMP/dirty.md"
if "$CHECK" "$TMP" >/dev/null 2>&1; then
  echo "FAIL: sensitive token was NOT caught" >&2
  exit 1
else
  echo "PASS: sensitive fixture correctly flagged"
fi

# Case 3: a missing target directory must fail closed (non-zero), not pass.
if "$CHECK" "$TMP/does-not-exist" >/dev/null 2>&1; then
  echo "FAIL: missing directory did not fail closed" >&2
  exit 1
else
  echo "PASS: missing directory fails closed"
fi

echo "OK: check-docs-clean self-test passed"
