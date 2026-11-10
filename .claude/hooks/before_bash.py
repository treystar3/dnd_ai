"""PreToolUse on Bash: a push only after the full suite passed on this exact tree (GOALS.md: 'the full suite passes before it is pushed').
A run passes when its only failures are listed in .claude/known_failures.txt; known.py --mark then writes HEAD to .claude/.suite_passed."""
import json, os, subprocess, sys
cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")
if "git push" in cmd:
    tree = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    mark = ".claude/.suite_passed"
    if not os.path.exists(mark) or open(mark).read().strip() != tree:
        print("Blocked: run the full suite on this commit first (failures in .claude/known_failures.txt are allowed):\n"
              "  PYTHONUTF8=1 python tools/run_suite.py -j 4 | tee /tmp/suite.txt; python .claude/hooks/known.py --mark < /tmp/suite.txt",
              file=sys.stderr)
        sys.exit(2)
