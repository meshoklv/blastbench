#!/usr/bin/env bash
# Verifies every task: smoke tests green on the broken state, hidden tests RED
# before the reference patch and GREEN after it, and the patched tree equals _base.
# Usage: tasks/verify.sh [task-dir-name ...]   (exit code != 0 on any mismatch)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WORKROOT="$(mktemp -d "${TMPDIR:-/tmp}/blastbench-verify.XXXXXX")"
trap 'rm -rf "$WORKROOT"' EXIT

TASKS=("$@")
[ ${#TASKS[@]} -eq 0 ] && mapfile -t TASKS < <(cd "$HERE" && ls -d t[0-9][0-9]-* | sort)

# run_tests <dir> <pattern> -> sets RESULT=OK|FAIL and NFAIL, NRAN
run_tests() {
  local out
  out=$(cd "$1" && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . -p "$2" 2>&1)
  local rc=$?
  NRAN=$(printf '%s\n' "$out" | sed -n 's/^Ran \([0-9]*\) test.*/\1/p' | tail -1)
  NFAIL=$(printf '%s\n' "$out" | sed -n 's/^FAILED (\(.*\))/\1/p' | tail -1 | grep -o '[0-9]\+' | awk '{s+=$1} END {print s+0}')
  NFAIL=${NFAIL:-0}
  [ $rc -eq 0 ] && RESULT=OK || RESULT=FAIL
  LAST="$out"
}

# apply_patch <dir> <patch>: `patch -p1` when installed, else `git apply -p1` (works outside a repo).
apply_patch() {
  if command -v patch >/dev/null 2>&1; then
    (cd "$1" && patch -p1 -s < "$2" >/dev/null 2>&1)
  else
    (cd "$1" && git apply -p1 "$2" >/dev/null 2>&1)
  fi
}

status=0
for t in "${TASKS[@]}"; do
  src="$HERE/$t"
  W="$(mktemp -d "$WORKROOT/w.XXXXXX")"
  cp -a "$HERE/_base/." "$W/"
  find "$W" -name __pycache__ -type d -prune -exec rm -rf {} +
  cp -a "$src/before/." "$W/"
  if [ -f "$W/.delete" ]; then
    while IFS= read -r f; do [ -n "$f" ] && rm -f "$W/$f"; done < "$W/.delete"
    rm -f "$W/.delete"
  fi
  problems=""

  run_tests "$W" 'test_smoke*.py'
  [ "$RESULT" = OK ] || problems="$problems smoke-red-on-broken"

  cp "$src"/hidden/test_*.py "$W/tests/"
  run_tests "$W" 'test_t[0-9][0-9]_*.py'
  before_state="RED($NFAIL fail of $NRAN)"
  [ "$RESULT" = FAIL ] && [ "$NFAIL" -gt 0 ] || problems="$problems hidden-not-red-before"

  if ! apply_patch "$W" "$src/reference.patch"; then
    problems="$problems patch-failed"
  fi
  find "$W" -name '*.orig' -delete
  run_tests "$W" 'test_t[0-9][0-9]_*.py'
  if [ "$RESULT" = OK ]; then after_state="GREEN($NRAN ok)"; else after_state="RED($NFAIL fail)"; problems="$problems hidden-not-green-after"; fi
  run_tests "$W" 'test_smoke*.py'
  [ "$RESULT" = OK ] || problems="$problems smoke-red-after"

  # the patched tree must be identical to the canonical solution in _base
  if ! diff -rq -x __pycache__ "$HERE/_base/brightline" "$W/brightline" >/dev/null; then
    problems="$problems patched-tree-differs-from-base"
  fi

  if [ -z "$problems" ]; then verdict="ok"; else verdict="MISMATCH:$problems"; status=1; fi
  printf '%s: before=%s after=%s  [%s]\n' "${t%%-*}" "$before_state" "$after_state" "$verdict"
  rm -rf "$W"
done
exit $status
