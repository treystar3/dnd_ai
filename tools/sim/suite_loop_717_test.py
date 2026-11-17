"""(f717) The suite's loop (docs/design/27_infrastructure_plan.md): a quick run picks tests by what each one ran the last time it
passed (the functions it entered, the data files it opened), not by the words in it; a second copy of the repo inside the folder
is not walked; a test that asks to runs alone, after the others; and every run holds one lock, the operating system's, so two
never share saves/ and a run that dies holds nothing.
Played on a small made-up tree in a temporary folder, with the real runner and its recorder (tools/suite_ran/sitecustomize.py).
Run: python tools/sim/suite_loop_717_test.py"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(".").resolve()
spec = importlib.util.spec_from_file_location("run_suite", ROOT / "tools" / "run_suite.py")
run_suite = importlib.util.module_from_spec(spec); spec.loader.exec_module(run_suite)

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def has(name: str) -> bool:
    return hasattr(run_suite, name)


tmp = Path(tempfile.mkdtemp(prefix="suite717_"))
tree, base, out = tmp / "tree", tmp / "base", tmp / "out"


def write(rel: str, text: str, root: Path = tree) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


CORE = '''LIMIT = 3


def alpha():
    return "alpha"


def beta():
    return "beta"


class Keeper:
    kind = "plain"

    def mind(self):
        return self.kind
'''
write("core.py", CORE)
write("data/rules/words.yaml", "apple: red\nbanana: yellow\n")
write("data/rules/other.yaml", "cherry: dark\n")
write("tools/sim/a_test.py", 'import sys, time\nsys.path.insert(0, ".")\nimport core\nopen("data/rules/words.yaml").read()\n'
                             'assert core.alpha() == "alpha"\nprint("the apple is read", time.time())\n')
write("tools/sim/b_test.py", 'import sys, time\nsys.path.insert(0, ".")\nimport core\nopen("data/rules/words.yaml").read()\n'
                             'assert core.beta() == "beta"\nprint("done", time.time())\n')
write("tools/sim/c_test.py", '# suite: serial\nimport sys, time\nsys.path.insert(0, ".")\nimport core\n'
                             'print("began", time.time())\nassert getattr(core.Keeper(), "mi" + "nd")() == "plain"\n')
write(".claude/worktrees/copy/.git", "gitdir: elsewhere\n")
write(".claude/worktrees/copy/core.py", CORE + "\n\ndef only_in_the_copy():\n    return 1\n")
write(".claude/worktrees/copy/tools/sim/z_test.py", "raise SystemExit(1)\n")
write("second/.git", "gitdir: elsewhere\n")
write("second/core.py", CORE)
shutil.copytree(tree, base, ignore=shutil.ignore_patterns(".claude", "second"))


def run(*args) -> tuple[int, list[str], str]:
    """The runner on the made-up tree: its exit code and the tests it ran, in the order they finished."""
    import contextlib, io
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        rc = run_suite.main(["--outdir", str(out), *args], root=tree) if has("lanes") else 99     # 99: not built yet
    text = said.getvalue()
    ran = [line.split()[1] for line in text.splitlines() if line.startswith(("ok  ", "FAIL ")) and line.rstrip().endswith("s)")]
    return rc, ran, text


def began(name: str) -> float:
    words = (out / f"{name}.out").read_text(encoding="utf-8").split()
    return float(words[-1]) if words else 0.0


# ---- a full run: everything passes, the copy is not run, the serial test waits for the others, and the map is kept
rc, ran, text = run("-j", "2")
check("a full run of the made-up tree passes, the three tests of its own and none of the copy's", rc == 0 and sorted(ran) == ["a_test.py", "b_test.py", "c_test.py"], (rc, ran, text[-400:]))
check("a test that says `# suite: serial` runs after the others are done", rc == 0 and ran[-1:] == ["c_test.py"]
      and began("c_test.py") >= max(began("a_test.py"), began("b_test.py")), ran)
kept = tree / "tools" / "sim" / ".ran.json"
ran_map = json.loads(kept.read_text(encoding="utf-8")) if kept.exists() else {}
def ran_by(test: str) -> set:
    row = ran_map.get("tests", {}).get(test, {})
    return {tuple(ran_map["keys"][i]) for i in row.get("ran", [])}
check("the run keeps what each test ran: the function it entered, and not its neighbour's", ("core.py", "alpha") in ran_by("a_test.py")
      and ("core.py", "beta") not in ran_by("a_test.py") and ("core.py", "beta") in ran_by("b_test.py"), sorted(ran_by("a_test.py")))
check("...a method by its class, and the module's and the class's own lines", {("core.py", "Keeper.mind"), ("core.py", "Keeper"), ("core.py", "<module>")} <= ran_by("c_test.py"),
      sorted(ran_by("c_test.py")))
check("...and the data files it opened", "data/rules/words.yaml" in ran_map.get("tests", {}).get("a_test.py", {}).get("data", [])
      and "data/rules/words.yaml" not in ran_map.get("tests", {}).get("c_test.py", {}).get("data", ["data/rules/words.yaml"]))
check("the lock is gone when the run is over", has("busy") and not run_suite.busy(tree))

# ---- which files changed: the tree's own, never a second copy of the repo inside it
files = [f.as_posix() for f in run_suite.changed_files(base, tree)] if has("lanes") else ["not built"]
check("nothing changed: no file is named, the copy under .claude and the folder with a .git of its own are not walked", files == [], files)

# ---- a quick run picks by what was run
def picked(*edits) -> list[str]:
    """The tests a quick run picks after these edits ((rel, old, new) or (rel, text)), which are then taken back."""
    before = {}
    for e in edits:
        p = tree / e[0]
        before[e[0]] = p.read_text(encoding="utf-8") if p.exists() else None
        write(e[0], before[e[0]].replace(e[1], e[2]) if len(e) == 3 else e[1])
        if len(e) == 3 and before[e[0]] == (tree / e[0]).read_text(encoding="utf-8"):
            raise SystemExit(f"the edit changed nothing: {e}")
    try:
        rc, ran, text = run("-j", "2", "--changed", str(base))
        return sorted(ran) if rc == 0 else [f"rc {rc}", text[-300:]]
    finally:
        for rel, text in before.items():
            (tree / rel).unlink() if text is None else write(rel, text)

def picks(name: str, want: list, *edits) -> None:
    got = picked(*edits)
    check(name, got == want, got)

picks("a change inside one function picks the test that ran it, not its neighbour", ["b_test.py"], ("core.py", 'return "beta"', 'return "beta" or "beta"'))
picks("...a method's change picks who called the method", ["c_test.py"], ("core.py", "return self.kind", "return str(self.kind)"))
picks("...a comment picks nothing", [], ("core.py", "def beta():", "def beta():      # a word of why"))
picks("a change to the module's own lines picks every test that loaded it", ["a_test.py", "b_test.py", "c_test.py"], ("core.py", "LIMIT = 3", "LIMIT = 4"))
picks("a change to a class's own lines picks every test that loaded the class", ["a_test.py", "b_test.py", "c_test.py"], ("core.py", 'kind = "plain"', 'kind = "plain"\n    more = 1'))
picks("a changed data key picks the test that opened the file and names the key, not one that only opened it", ["a_test.py"],
      ("data/rules/words.yaml", "apple: red", "apple: green"))
picks("...and a data file no test opened picks none", [], ("data/rules/other.yaml", "cherry: dark", "cherry: light"))
picks("a changed test picks itself", ["b_test.py"], ("tools/sim/b_test.py", '"done"', '"done now"'))
picks("a test the map has never seen is picked", ["d_test.py"], ("tools/sim/d_test.py", 'print("new")\n'))
picks("a new function no test has run picks none, whatever words a test holds (a test of it is new or changed, and picked for that)", [],
      ("core.py", CORE + "\n\ndef apple():\n    return 1\n"))
picks("a new method of a subclass picks the tests that ran the method it stands in front of", ["c_test.py"],
      ("core.py", CORE + "\n\nclass Under(Keeper):\n    def mind(self):\n        return 1\n"))
picks("...and a method of that name in a class apart picks none", [], ("core.py", CORE + "\n\nclass Apart:\n    def mind(self):\n        return 1\n"))
picks("a file whose line endings alone changed is not a changed file", [], ("core.py", CORE.replace("\n", "\r\n")))
picks("a changed decorator, which runs when the module is loaded, picks every test that loaded it", ["a_test.py", "b_test.py", "c_test.py"],
      ("core.py", "def beta():", "@staticmethod\ndef beta():"))
picks("...a changed default only the tests that ran the function", ["b_test.py"], ("core.py", "def beta():", "def beta(n=LIMIT):"))

GAMMA = CORE + "\n\ndef gamma():\n    return 1\n"
write("core.py", GAMMA)
for root in (tree, base):
    write("tools/sim/e_test.py", 'import sys\nsys.path.insert(0, ".")\nimport core\nassert getattr(core, "gam" + "ma")() in (1, 2)\n', root=root)
rc, ran, text = run("-j", "2", "--changed", str(base))
check("(a function new since the baseline is run by a test that does not name it, and has no record yet)", rc == 0 and ran == ["e_test.py"], (rc, ran))
write("core.py", GAMMA.replace("def gamma():\n    return 1", "def gamma():\n    return 2"))
rc, ran, text = run("-j", "2", "--changed", str(base))
check("a function still new since the baseline picks the tests that have run it since", rc == 0 and sorted(ran) == ["e_test.py"], (rc, ran))
for root in (tree, base):
    (root / "tools/sim/e_test.py").unlink()
write("core.py", CORE)

write("gone.py", "def left():\n    return 1\n")
write("gone.py", "def left():\n    return 1\n", root=base)
for root in (tree, base):
    write("tools/sim/g_test.py", 'import sys\nsys.path.insert(0, ".")\nimport gone\nassert gone.left() == 1\n', root=root)
rc, ran, text = run("-j", "2", "--changed", str(base))
(tree / "gone.py").unlink()
files = [f.as_posix() for f in run_suite.changed_files(base, tree)] if has("lanes") else []
rc, ran, text = run("-j", "2", "--changed", str(base), "--no-record")
check("a file that is gone is a changed file, and picks the tests that ran it", files == ["gone.py"] and ran == ["g_test.py"], (files, ran))
for root in (tree, base):
    (root / "tools/sim/g_test.py").unlink()
(base / "gone.py").unlink()

for root in (tree, base):
    write("tools/sim/f_test.py", 'import os, subprocess, sys\nenv = {k: v for k, v in os.environ.items() if not k.startswith(("MERAVIA_RAN", "PYTHONPATH"))}\n'
                             'env["PYTHONPATH"] = "."\nassert subprocess.run([sys.executable, "-c", "import core; core.beta()  # a/b"], env=env).returncode == 0\n', root=root)
rc, ran, text = run("-j", "2", "--changed", str(base))
picks("a test that starts a Python process the record cannot follow is picked for any change to code", ["a_test.py", "f_test.py"],
      ("core.py", 'return "alpha"', 'return "alpha" or 1'))
picks("...and not for a change to data", ["a_test.py"], ("data/rules/words.yaml", "apple: red", "apple: green"))
for root in (tree, base):
    (root / "tools/sim/f_test.py").unlink()

# ---- with no map, the words in a test are what is left, and it says so
held = kept.read_text(encoding="utf-8") if kept.exists() else ""
kept.unlink(missing_ok=True)
write("core.py", CORE.replace('return "beta"', 'return "beta" or 1'))
rc, ran, text = run("-j", "2", "--changed", str(base), "--no-record")
write("core.py", CORE)
check("with no map kept, tests are picked by the words in them, and the run says a full run is owed", rc == 0 and sorted(ran) == ["a_test.py", "b_test.py", "c_test.py"]
      and "no record" in text, (rc, ran, text[-300:]))
if held:
    kept.write_text(held, encoding="utf-8")

# ---- one lock
if has("take"):
    lock = run_suite.lock_of(tree)
    mine = run_suite.take(tree, wait=0)
    check("a run takes the lock, and the suite is busy while it holds it", mine is not None and run_suite.busy(tree))
    check("a second run that will not wait is turned away", run_suite.take(tree, wait=0) is None)
    rc, ran, text = run("-j", "2", "--wait", "0")
    check("...with its own exit code, one line saying who holds it, and no test run", rc == run_suite.HELD and ran == []
          and f"process {os.getpid()}" in text and "holds the suite" in text, (rc, text[-200:]))
    start = time.time()
    import threading
    threading.Timer(0.6, mine.release).start()
    waited = run_suite.take(tree, wait=10)
    check("a run that waits gets the lock when the holder is done", waited is not None and 0.3 < time.time() - start < 8, time.time() - start)
    waited.release()
    check("...and a released lock is not busy", not run_suite.busy(tree))
    holder = subprocess.Popen([sys.executable, "-c", "import importlib.util, sys, time\n"
                               f"spec = importlib.util.spec_from_file_location('run_suite', {str(ROOT / 'tools' / 'run_suite.py')!r})\n"
                               "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                               f"assert m.take({str(tree)!r}) is not None\nprint('held', flush=True)\ntime.sleep(120)\n"],
                              stdout=subprocess.PIPE, text=True)
    said = holder.stdout.readline().strip()
    check("another process holds the suite: it is busy, and a run here is turned away", said == "held" and run_suite.busy(tree)
          and run_suite.take(tree, wait=0) is None, said)
    holder.kill()
    holder.wait()
    after = run_suite.take(tree, wait=5)
    check("a holder that died holds nothing: the next run takes the lock", after is not None)
    if after is not None:
        after.release()
else:
    check("the runner has one lock every run takes", False, "not built")

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
