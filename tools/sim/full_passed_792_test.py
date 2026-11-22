"""(f792) A clean full run keeps the fingerprint of the files it passed on (tools/sim/.full_passed.json), and the stop hook's quick
run is skipped when the files are still exactly those (run_suite.py --passed). Before this, a change to the turn's core made the hook
pick nearly every test (550 of 582 for f790's change to release), so the quick run was a second full run right after the first,
and it collided with one still running ("no suite summary: the run did not finish").
The case that found it: a full run passes, nothing changes, and the files read as passed. Second cases of the kind: a changed code
file, a new one, a gone one and a changed data file each read as not passed; a change of line endings alone and a file that is not
code (a note) leave it passed; a run with a failure, a run of some tests (--only) and a run against a copy (--changed) never mark a
pass; and the stop hook asks before it runs. Every run here is of a project made for it in a folder of its own.
Run: python tools/sim/full_passed_792_test.py"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import run_suite

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


TMP = Path(tempfile.mkdtemp(prefix="full_passed_792_"))
PROJ, OUT = TMP / "proj", TMP / "out"


def project(fail: bool = False) -> None:
    shutil.rmtree(PROJ, ignore_errors=True)
    (PROJ / "tools" / "sim").mkdir(parents=True)
    (PROJ / "data").mkdir()
    (PROJ / "engine.py").write_text("X = 1\n", encoding="utf-8")
    (PROJ / "data" / "rules.yaml").write_text("a: 1\n", encoding="utf-8")
    (PROJ / "notes.md").write_text("a note\n", encoding="utf-8")
    (PROJ / "tools" / "sim" / "one_test.py").write_text("print('ok   one')\n", encoding="utf-8")
    (PROJ / "tools" / "sim" / "two_test.py").write_text(f"import sys\nprint('two')\nsys.exit({1 if fail else 0})\n", encoding="utf-8")


def run(*argv) -> int:
    with open(os.devnull, "w") as quiet:
        old, sys.stdout = sys.stdout, quiet
        try:
            return run_suite.main(list(argv) + ["-j", "2", "--outdir", str(OUT), "--no-record"], root=PROJ)
        finally:
            sys.stdout = old


def passed() -> bool:
    return run_suite.main(["--passed"], root=PROJ) == 0


try:
    project()
    check("before any run, nothing reads as passed", not passed())
    rc = run()
    check("the case: a clean full run passes", rc == 0, rc)
    check("...and the files read as passed", passed(), run_suite.passed_of(PROJ).read_text(encoding="utf-8")
          if run_suite.passed_of(PROJ).exists() else "no record")
    engine = PROJ / "engine.py"
    engine.write_text("X = 1\r\n", encoding="utf-8", newline="")
    check("a change of line endings alone leaves it passed", passed())
    (PROJ / "notes.md").write_text("another note\n", encoding="utf-8")
    check("...and so does a file that is not code (a note)", passed())
    engine.write_text("X = 2\n", encoding="utf-8")
    check("a changed code file: not passed", not passed())
    engine.write_text("X = 1\n", encoding="utf-8")
    check("...changed back: passed again (the record is of the files, not of a time)", passed())
    (PROJ / "more.py").write_text("Y = 1\n", encoding="utf-8")
    check("a new code file: not passed", not passed())
    (PROJ / "more.py").unlink()
    (PROJ / "data" / "rules.yaml").write_text("a: 2\n", encoding="utf-8")
    check("a changed data file: not passed", not passed())
    (PROJ / "data" / "rules.yaml").write_text("a: 1\n", encoding="utf-8")
    engine.unlink()
    check("a gone file: not passed", not passed())
    engine.write_text("X = 1\n", encoding="utf-8")

    engine.write_text("X = 3\n", encoding="utf-8")
    rc = run("--only", "one")
    check("a run of some tests passes but marks no pass", rc == 0 and not passed(), rc)
    base = TMP / "copy"
    shutil.copytree(PROJ, base)
    rc = run("--changed", str(base))
    check("...nor does a run against a copy (--changed)", not passed(), rc)

    project(fail=True)
    rc = run()
    check("a full run with a failure marks no pass", rc == 1 and not passed(), rc)

    project()
    (PROJ / "tools" / "sim" / "two_test.py").write_text("from pathlib import Path\nPath('engine.py').write_text('X = 9\\n')\n", encoding="utf-8")
    rc = run()
    (PROJ / "engine.py").write_text("X = 1\n", encoding="utf-8")         # put back as the run found it: a pass recorded then would read
    check("a full run whose files changed while it ran (a test wrote one) marks no pass, even once they are put back",
          rc == 0 and not passed(), rc)

    project()
    run()
    from unittest import mock
    with mock.patch.object(run_suite.sys, "version", "3.99.0 (another Python)"):
        check("a pass made under one Python is not a pass under another", not passed())
    with mock.patch.object(run_suite.sys, "platform", "another-os"):
        check("...nor on another platform", not passed())
    check("...and under this one it stands", passed())
finally:
    shutil.rmtree(TMP, ignore_errors=True)

hook = Path(".claude/hooks/quick_suite.sh").read_text(encoding="utf-8")
ask, quick = hook.find("run_suite.py --passed"), hook.find("--changed \"$base\"")
check("the stop hook asks whether these files passed before it runs the quick suite", 0 <= ask < quick, (ask, quick))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
