"""(f791) The suite runs as many tests at a time as the machine has room for, when none is asked: two short of its processors, at
least 2 and at most 16. Before this the default was 2, and the owner's 28 processors ran the suite at 8 when asked: 582 tests in
about 570 s, against 388 s at 16 (measured 2026-11-22, every test passing).
The case that found it: the owner's 28 processors. Second cases of the kind: a small machine (4, as GitHub's runners), an 8 and a
2, one whose count Python cannot read, and a -j the caller names, which always wins.
Run: python tools/sim/suite_width_791_test.py"""
import shutil
import sys
import tempfile
from unittest import mock
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import run_suite

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


check("the owner's 28 processors: 16 at a time, the most", run_suite.width(28) == 16, run_suite.width(28))
check("...an 8: 6, two short of its processors", run_suite.width(8) == 6, run_suite.width(8))
check("...a 4, as GitHub's runners: 2, the least", run_suite.width(4) == 2, run_suite.width(4))
check("...a 2: still 2", run_suite.width(2) == 2, run_suite.width(2))
with mock.patch("os.cpu_count", return_value=None):
    check("...a machine whose count Python cannot read: as a 4 would", run_suite.width() == 2, run_suite.width())

seen = {}
OUT = tempfile.mkdtemp(prefix="width_791_")                  # the run's own folder, never the project's


class Stop(Exception):
    pass


def caught(*a, **k):
    seen["j"] = k.get("max_workers")
    raise Stop


def width_of(argv):
    seen.clear()
    with mock.patch.object(run_suite, "ThreadPoolExecutor", side_effect=caught), \
         mock.patch.object(run_suite, "take", return_value=mock.Mock()), \
         mock.patch.object(run_suite, "owners", return_value={}), mock.patch.object(run_suite, "lanes", return_value=([], [])):
        try:
            run_suite.main(argv + ["--outdir", OUT, "--no-record", "--only", "no_such_test_791"])
        except Stop:
            pass
    return seen.get("j")


with mock.patch("os.cpu_count", return_value=28):
    check("a run with no -j takes the machine's width", width_of([]) == 16, width_of([]))
    check("...and a -j named by the caller wins", width_of(["-j", "3"]) == 3, width_of(["-j", "3"]))
shutil.rmtree(OUT, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
