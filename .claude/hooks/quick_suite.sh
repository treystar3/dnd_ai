#!/usr/bin/env bash
# Stop: when Claude says it is done, run the tests that mention a changed tracked file (tools/run_suite.py --changed) against HEAD.
# Exit 2 sends new failures back so it keeps working; failures listed in .claude/known_failures.txt and untracked tests do not block.
# Skipped when Claude is already continuing from this hook (stop_hook_active), when no tracked file changed, or while
# another suite run holds saves/ (run_suite.py --busy): two runs there collide on databases and recordings.
grep -q '"stop_hook_active" *: *true' <<<"$(cat)" && exit 0
[ -z "$(git status --porcelain --untracked-files=no -- '*.py' '*.yaml' '*.js')" ] && exit 0
python tools/run_suite.py --busy && { echo "a full suite run is in progress (saves/.suite_running): quick run skipped"; exit 0; }
base=/tmp/meravia_base_$(git rev-parse --short HEAD)
[ -d "$base" ] || git worktree add -f --detach "$base" HEAD >/dev/null 2>&1
out=$(python tools/run_suite.py -j 4 --changed "$base" --outdir /tmp/meravia_quick 2>&1)
echo "$out" | tail -3
echo "$out" | python .claude/hooks/known.py --ignore-untracked || exit 2
exit 0
