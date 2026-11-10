#!/usr/bin/env bash
# Stop: when Claude says it is done, run the tests that mention a changed file (tools/run_suite.py --changed) against HEAD.
# Exit 2 sends the failures back so it keeps working. Skipped when nothing changed. The full suite stays a deliberate step.
[ -z "$(git status --porcelain -- '*.py' '*.yaml' '*.js')" ] && exit 0
base=/tmp/meravia_base_$(git rev-parse --short HEAD)
[ -d "$base" ] || git worktree add -f --detach "$base" HEAD >/dev/null 2>&1
out=$(python tools/run_suite.py -j 4 --changed "$base" 2>&1)
echo "$out" | tail -5
echo "$out" | grep -q "^FAILED:" && { echo "Changed-file tests failed; fix before finishing." >&2; exit 2; }
exit 0
