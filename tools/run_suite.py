"""Run the simulation tests in tools/sim, several at a time.

  python tools/run_suite.py                 all tests, 2 at a time
  python tools/run_suite.py -j 4            4 at a time
  python tools/run_suite.py --only shop,board     tests whose name contains any of these
  python tools/run_suite.py --changed DIR   only the tests that mention a file changed since DIR (a copy of the last release);
                                            a quick check while building - run the whole suite before shipping
Output goes to <outdir>/<test>.out (default /tmp/dnd_suite); the summary lists failures and the slowest tests."""
import argparse
import filecmp
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "tools" / "sim"
CODE = (".py", ".yaml", ".js")


def changed_files(baseline: Path) -> list[Path]:
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in CODE or any(x in p.parts for x in ("__pycache__", "saves", "logs", ".git")):
            continue
        rel = p.relative_to(ROOT)
        old = baseline / rel
        if not old.exists() or not filecmp.cmp(p, old, shallow=False):
            out.append(rel)
    return out


BROAD = {"world", "main", "loader", "console", "simlib", "models", "rules", "dbg", "dbg2", "cc"}      # too central to pick tests by name: run those with --only or the whole suite


def affected(tests: list[Path], files: list[Path]) -> list[Path]:
    """Tests that are themselves changed, or whose text mentions a changed file's module name."""
    stems = {f.stem for f in files if f.parts[:2] != ("tools", "sim")}
    own = {f.name for f in files if f.parts[:2] == ("tools", "sim")}
    skipped = sorted(s for s in stems if s in BROAD)
    if skipped:
        print(f"note: {', '.join(skipped)} touch too much to pick tests by name; use --only or the whole suite for them")
    stems = {s for s in stems if len(s) > 3 and s not in BROAD}
    out = []
    for t in tests:
        text = t.read_text(encoding="utf-8", errors="ignore")
        if t.name in own or any(re.search(rf"\b{re.escape(s)}\b", text) for s in stems):
            out.append(t)
    return out


def run_one(test: Path, outdir: Path, timeout: int) -> tuple[str, int, float]:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    start = time.time()
    with open(outdir / f"{test.name}.out", "w", encoding="utf-8") as fh:
        try:
            rc = subprocess.run([sys.executable, str(test)], cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    if rc == 0:                                          # a test that prints its failures but forgets to exit non-zero still fails
        try:
            text = (outdir / f"{test.name}.out").read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if re.search(r"^FAIL\b|^FAILED[: ]+(?!none\b)", text, re.M):       # "FAILED: none" is how some tests say all passed
            rc = 1
    return test.name, rc, time.time() - start


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=2, help="tests at a time")
    ap.add_argument("--only", default="", help="comma-separated name fragments")
    ap.add_argument("--changed", default="", metavar="DIR", help="a copy of the last release to compare against")
    ap.add_argument("--outdir", default="/tmp/dnd_suite")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    tests = sorted(SIM.glob("*_test.py"))
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        tests = [t for t in tests if any(k in t.name for k in keys)]
    if args.changed:
        files = changed_files(Path(args.changed))
        print(f"{len(files)} changed files")
        tests = affected(tests, files)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.j)) as pool:
        for name, rc, took in pool.map(lambda t: run_one(t, outdir, args.timeout), tests):
            results.append((name, rc, took))
            print(f"{'ok  ' if rc == 0 else 'FAIL'} {name} ({took:.0f}s)", flush=True)
    bad = [n for n, rc, _ in results if rc]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed in {time.time() - start:.0f}s")
    if results:
        print("slowest: " + ", ".join(f"{n} {t:.0f}s" for n, _, t in sorted(results, key=lambda r: -r[2])[:5]))
    if bad:
        print("FAILED: " + ", ".join(bad) + f"   (see {outdir}/<test>.out)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
