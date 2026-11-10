"""Reads a run_suite.py summary on stdin and names the failures not listed in .claude/known_failures.txt (one test file per line, # comments).

  python .claude/hooks/known.py            exit 2 and name them if there are new failures, else exit 0
  python .claude/hooks/known.py --mark     the same, and on no new failures in a full run of a clean tree write HEAD to .claude/.suite_passed
  --ignore-untracked                       failures of untracked tests in tools/sim do not count (the stop hook: tracked changes only)

A summary without its "N/M passed" line (a run that died) never counts as passed."""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
KNOWN = ROOT / ".claude" / "known_failures.txt"
MARK = ROOT / ".claude" / ".suite_passed"


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout


def known() -> set[str]:
    if not KNOWN.exists():
        return set()
    return {l.split("#")[0].strip() for l in KNOWN.read_text(encoding="utf-8").splitlines()} - {""}


def main() -> int:
    out = sys.stdin.read()
    total = re.search(r"^(\d+)/(\d+) passed", out, re.M)
    failed = re.search(r"^FAILED: (.+?)(?:\s{2,}\(see .*)?$", out, re.M)
    names = [n.strip() for n in failed.group(1).split(",")] if failed else []
    skip = known()
    if "--ignore-untracked" in sys.argv:
        skip |= {Path(p).name for p in git("ls-files", "--others", "--exclude-standard", "tools/sim").split()}
    new = [n for n in names if n not in skip]
    if not total:
        print("no suite summary: the run did not finish", file=sys.stderr)
        return 2
    if new:
        print("new failures (not in .claude/known_failures.txt): " + ", ".join(new), file=sys.stderr)
        return 2
    print(f"{total.group(0)}; every failure is a known one ({len(names)})")
    if "--mark" in sys.argv:
        if git("status", "--porcelain", "--untracked-files=no").strip():
            print("not marked: the tree has uncommitted tracked changes", file=sys.stderr)
            return 2
        MARK.write_text(git("rev-parse", "HEAD").strip() + "\n", encoding="utf-8")
        print("marked " + MARK.read_text().strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
