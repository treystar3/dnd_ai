"""Run the simulation tests in tools/sim, several at a time.

  python tools/run_suite.py                 all tests, 2 at a time
  python tools/run_suite.py -j 4            4 at a time
  python tools/run_suite.py --only shop,board     tests whose name contains any of these
  python tools/run_suite.py --changed DIR   only the tests a change since DIR (a copy of the last release) touches; a quick
                                            check while building - run the whole suite before shipping
  python tools/run_suite.py --busy          exit 0 if a run holds the suite, 1 if not

(f717) What --changed picks: a test that ran, the last time it passed, a function whose code changed, is new or is gone (comments
and docstrings do not count), or a method that a new method of a subclass now stands in front of; a test that opened a data file that changed and names
one of its changed keys; a test that is itself changed or that no run has recorded; and, for
any change to code, a test that starts a Python process the record cannot follow. Every run records what each test ran
(tools/suite_ran) and keeps it in tools/sim/.ran.json, which git ignores. With no record yet the tests are picked by the words
in them. It is a quick check: a new handler found by its name, or a number a test reads without naming its key, picks no test.
A test with the line `# suite: serial` runs alone, after the others: for the ones that start processes of their own.
Every run holds one lock (on saves/.suite_running, the operating system's: a run that dies lets go of it): two runs share saves/
and would fail each other. A full run waits for it (--wait SECONDS, 1200); a --changed run waits 2 and then leaves with exit code 75.
Output goes to <outdir>/<test>.out (default /tmp/meravia_suite); the summary lists failures and the slowest tests.
(f741) Each test runs with a saves folder of its own under <outdir>/saves_of, never the player's saves/: a passed test's goes with
its run, and the last failed run's stays as saves_of/<test>_failed to be looked at."""
import argparse
import ast
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "tools" / "sim"
CODE = (".py", ".yaml", ".js")
RAN_SITE = Path(__file__).resolve().parent / "suite_ran"      # (f717) loaded by each test's Python: what the test ran
UNWALKED = {"__pycache__", "saves", "logs", ".git", ".claude", ".venv", ".buildenv", "runtime", "models", "build", "dist"}
WHOLE = (("storage/statehash.py", "data_hash"), ("storage/statehash.py", "data_hashes"))              # (f717) read every data file: a test that ran one is picked for any data change


def walked(root: Path):
    """The code and data files under a root, by their path under it. (f717) A folder that is a checkout of its own (it holds a
    .git: a worktree kept inside the repo) is not walked, nor what play, a build or a tool writes."""
    for folder, dirs, names in os.walk(root):
        here = Path(folder)
        dirs[:] = sorted(d for d in dirs if d not in UNWALKED and not (here / d / ".git").exists())
        for name in sorted(names):
            if Path(name).suffix in CODE:
                yield (here / name).relative_to(root)


def changed_files(baseline: Path, root: Path = ROOT) -> list[Path]:
    """The files that differ from the baseline's, are new, or (f717) are gone. Line endings are not a difference: git checks
    a file out with either, by its settings."""
    def differs(rel: Path) -> bool:
        if not (baseline / rel).exists():
            return True
        if filecmp.cmp(root / rel, baseline / rel, shallow=False):
            return False
        return (root / rel).read_bytes().replace(b"\r\n", b"\n") != (baseline / rel).read_bytes().replace(b"\r\n", b"\n")

    now = list(walked(root))
    out = [rel for rel in now if differs(rel)]
    here = set(now)
    return out + [rel for rel in walked(baseline) if rel not in here]


BROAD = {"world", "main", "loader", "console", "simlib", "models", "rules", "dbg", "dbg2", "cc"}      # too central to pick tests by name: run those with --only or the whole suite


def affected(tests: list[Path], files: list[Path]) -> list[Path]:
    """Tests that are themselves changed, or whose text mentions a changed file's module name. (f717) What is left when no
    run has recorded what the tests ran, and for a file no test's record holds."""
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


# ---- (f717) picked by what a test ran

def code_parts(text: str) -> dict[str, str]:
    """A Python file as the parts a test's record names: each function or method whole (what is nested in it with it) under
    Class.method, and a class's or the module's own lines, the rest, under Class and <module>: with a function's decorators,
    which run when its owner is loaded and may enrol it for others. Each as its syntax tree, so a comment, a blank line or a
    docstring changes none."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    out: dict[str, str] = {}

    def walk(node, name: str) -> None:
        rest = [ast.dump(x) for x in getattr(node, "bases", []) + [k.value for k in getattr(node, "keywords", [])] + getattr(node, "decorator_list", [])]
        for child in node.body:
            key = f"{name}.{child.name}" if name and hasattr(child, "name") else getattr(child, "name", "")
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[key] = out.get(key, "") + ast.dump(child)
                rest += [ast.dump(x) for x in child.decorator_list]
            elif isinstance(child, ast.ClassDef):
                walk(child, key)
            else:
                rest.append(ast.dump(child))
        out[name or "<module>"] = out.get(name or "<module>", "") + "\n".join(rest)

    walk(tree, "")
    return out


def changed_parts(old: str | None, new: str | None):
    """(the parts whose code changed or is gone, the parts that are new); None when either text cannot be read as Python: the
    whole file counts then."""
    try:
        a = code_parts(old) if old is not None else {}
        b = code_parts(new) if new is not None else {}
    except SyntaxError:
        return None
    return {k for k in a if a[k] != b.get(k)}, {k for k in b if k not in a}


def bases_of(text: str | None) -> dict[str, set[str]]:
    """Each class of a Python file, by Outer.Inner, with the last name of each class it is made from."""
    out: dict[str, set[str]] = {}

    def walk(node, name: str) -> None:
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                key = f"{name}.{child.name}" if name else child.name
                out[key] = {ast.unparse(b).rsplit(".", 1)[-1] for b in child.bases}
                walk(child, key)

    try:
        walk(ast.parse(text or ""), "")
    except SyntaxError:
        pass
    return out


def data_words(old: str | None, new: str | None, stem: str) -> set[str]:
    """The keys of a data file that changed, two levels down: the words a test names if the change is its business. The file's
    own name when it holds no keys to tell by; nothing when only comments or the layout changed."""
    try:
        import yaml
        a, b = yaml.safe_load(old or "") or {}, yaml.safe_load(new or "") or {}
    except Exception:
        return {stem}
    if a == b:
        return set()
    if not isinstance(a, dict) or not isinstance(b, dict):
        return {stem}
    words = set()
    for k in set(a) | set(b):
        x, y = a.get(k), b.get(k)
        if x != y:
            words.add(str(k))
            if isinstance(x, dict) and isinstance(y, dict):
                words |= {str(j) for j in set(x) | set(y) if x.get(j) != y.get(j)}
    return {w for w in words if len(w) > 3} or {stem}


def ran_path(root: Path = ROOT) -> Path:
    return Path(root) / "tools" / "sim" / ".ran.json"


def load_ran(root: Path = ROOT) -> dict[str, dict]:
    """The record kept: {test: {"ran": {(file, part)}, "data": {file}, "blind": it started a Python process the record could not
    follow}}; empty when none is kept or it cannot be read."""
    try:
        kept = json.loads(ran_path(root).read_text(encoding="utf-8"))
        keys = [tuple(k) for k in kept["keys"]]
        return {t: {"ran": {keys[i] for i in row["ran"]}, "data": set(row["data"]), "blind": bool(row.get("blind"))} for t, row in kept["tests"].items()}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return {}


def keep_ran(root: Path, record: dict[str, dict]) -> None:
    keys = sorted({k for row in record.values() for k in row["ran"]})
    at = {k: i for i, k in enumerate(keys)}
    kept = {"keys": [list(k) for k in keys],
            "tests": {t: {"ran": sorted(at[k] for k in row["ran"]), "data": sorted(row["data"]), "blind": bool(row.get("blind"))}
                      for t, row in sorted(record.items())}}
    tmp = ran_path(root).with_suffix(".tmp")
    tmp.write_text(json.dumps(kept, separators=(",", ":")), encoding="utf-8", newline="\n")
    os.replace(tmp, ran_path(root))


def ran_of(test: Path, outdir: Path) -> dict | None:
    """What the test's processes wrote this run (its own and any it started), taken up; None when none wrote."""
    got = None
    for f in sorted((outdir / "ran").glob(f"{test.name}.*.json")):
        try:
            one = json.loads(f.read_text(encoding="utf-8"))
            got = got or {"ran": set(), "data": set(), "blind": False}
            got["ran"] |= {tuple(k) for k in one["ran"]}
            got["data"] |= set(one["data"])
            got["blind"] = got["blind"] or bool(one.get("blind"))
        except (OSError, ValueError, KeyError, TypeError):
            pass
        f.unlink(missing_ok=True)
    return got


def pick(tests: list[Path], files: list[Path], record: dict[str, dict], baseline: Path, root: Path = ROOT) -> list[Path]:
    """The tests a change touches, by the record of what each ran."""
    def text_of(p: Path) -> str | None:
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    by_file: dict[str, set] = {}
    for row in record.values():
        for rel, part in row["ran"]:
            by_file.setdefault(rel, set()).add(part)
    own = {f.name for f in files if f.parts[:2] == ("tools", "sim") and f.name.endswith("_test.py")}
    hit: set = set()                       # parts whose code changed, is new or is gone
    over: set[tuple[str, str]] = set()     # (a class, a method's name): a new method of a subclass stands in front of this one
    code = False                           # some code changed that is not a test
    data: dict[str, set[str]] = {}         # a changed data file -> its changed keys
    by_words: list[Path] = []              # files no record holds: by the words in a test
    for f in files:
        rel = f.as_posix()
        if f.name in own:
            continue
        code = code or f.suffix == ".py"
        if f.suffix == ".py" and rel in by_file:
            got = changed_parts(text_of(baseline / f), text_of(root / f))
            if got is None:
                hit |= {(rel, part) for part in by_file[rel]}
            else:
                hit |= {(rel, part) for part in got[0] | got[1]}             # new since the baseline, and run since
                made_from = bases_of(text_of(root / f))
                over |= {(base, part.rsplit(".", 1)[-1]) for part in got[1] if "." in part for base in made_from.get(part.rsplit(".", 1)[0], ())}
        elif f.suffix == ".yaml" and f.parts[:1] == ("data",):
            data[rel] = data_words(text_of(baseline / f), text_of(root / f), f.stem)
            hit |= set(WHOLE)
        else:
            by_words.append(f)
    hit |= {(rel, part) for rel, parts in by_file.items() for part in parts
            if "." in part and (part.rsplit(".", 2)[-2], part.rsplit(".", 1)[-1]) in over}
    worded = {t.name for t in affected(tests, by_words)} if by_words else set()
    out = []
    for t in tests:
        row = record.get(t.name)
        if row is None or t.name in own or t.name in worded or row["ran"] & hit or (code and row["blind"]):
            out.append(t)
            continue
        words = {w for rel, ws in data.items() if rel in row["data"] for w in ws}
        if words:
            text = t.read_text(encoding="utf-8", errors="ignore")
            if any(re.search(rf"\b{re.escape(w)}\b", text) for w in words):
                out.append(t)
    return out


def lanes(tests: list[Path]) -> tuple[list[Path], list[Path]]:
    """(the tests run several at a time, the ones that run alone after them: each says `# suite: serial` on a line of its own)."""
    alone = [t for t in tests if re.search(r"^# suite: serial\b", t.read_text(encoding="utf-8", errors="ignore"), re.M)]
    return [t for t in tests if t not in alone], alone


def own_saves(outdir: Path, test: Path) -> Path:
    """(f741) A fresh saves folder for one run of a test, outside the repository: the game's saves folder in the test and in every
    process it starts (MERAVIA_SAVES, read by storage/campaign.py), so no test reaches the player's saves/."""
    root = Path(outdir).resolve() / "saves_of"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{test.stem}_", dir=root))


def leave_saves(own: Path, test: Path, passed: bool) -> None:
    """(f741) A passed test's saves go with its run; a failed test's stay to be looked at, the last failed run's only."""
    if passed:
        shutil.rmtree(own, ignore_errors=True)
        return
    kept = own.parent / f"{test.stem}_failed"
    shutil.rmtree(kept, ignore_errors=True)
    try:
        own.rename(kept)
    except OSError:
        pass                                                               # left under its own name, to be looked at all the same


def run_one(test: Path, outdir: Path, timeout: int, root: Path = ROOT, record: bool = False) -> tuple[str, int, float]:
    env = dict(os.environ, PYTHONPATH=str(root), MERAVIA_NO_SERVER="1")   # (f514) no test reaches a real model by accident
    env["PYTHONUTF8"] = "1"                                                # (f565) UTF-8 on every OS, not the shell's code page
    for k in [k for k in env if k.startswith("DND_")]:                    # (f533) nor plays with the settings of the shell that ran it
        env.pop(k)                                                         # (a night's DND_THINK_TASKS, its threads, its voice)
    env.pop("MERAVIA_RAN", None)                                           # (f717) a suite run inside a test keeps its own record
    own = own_saves(outdir, test)
    env["MERAVIA_SAVES"] = str(own)                                        # (f741) nor reaches the player's saves
    if record:
        (outdir / "ran").mkdir(exist_ok=True)
        for f in (outdir / "ran").glob(f"{test.name}.*.json"):
            f.unlink(missing_ok=True)
        env.update(PYTHONPATH=f"{RAN_SITE}{os.pathsep}{root}", MERAVIA_RAN=str(outdir / "ran" / test.name), MERAVIA_RAN_ROOT=str(root))
    start = time.time()
    with open(outdir / f"{test.name}.out", "w", encoding="utf-8") as fh:
        try:
            rc = subprocess.run([sys.executable, str(test)], cwd=root, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    if rc == 0:                                          # a test that prints its failures but forgets to exit non-zero still fails
        try:
            text = (outdir / f"{test.name}.out").read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if re.search(r"^FAIL\b|^FAILED(?![: ]+none\b)[: ]", text, re.M):       # "FAILED: none" is how some tests say all passed
            rc = 1
    leave_saves(own, test, rc == 0)
    return test.name, rc, time.time() - start


# ---- (f717) one lock for every run

HELD = 75                                     # the exit code of a run that found the suite held and did not wait long enough
FAR = 1 << 30                                 # the byte locked on Windows: past what the file holds, so who holds it can be read


def lock_of(root: Path = ROOT) -> Path:
    return Path(root) / "saves" / ".suite_running"


def _lock(fd: int) -> bool:
    """The operating system's lock on the open file, if nobody has it: let go of when the file is closed, or its process dies."""
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, FAR, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


class Lock:
    """The suite, held until it is released or the process ends. The file stays; it says who held it last."""

    def __init__(self, fd: int) -> None:
        self.fd = fd

    def release(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def take(root: Path = ROOT, wait: float = 0) -> Lock | None:
    """The suite's lock; None when another run holds it and `wait` seconds did not see it freed."""
    path = lock_of(root)
    path.parent.mkdir(exist_ok=True)
    until = time.time() + wait
    while True:
        fd = os.open(path, os.O_RDWR | os.O_CREAT)
        if _lock(fd):
            os.lseek(fd, 0, os.SEEK_SET)
            os.truncate(fd, 0)
            os.write(fd, str(os.getpid()).encode("ascii"))
            return Lock(fd)
        os.close(fd)
        if time.time() >= until:
            return None
        time.sleep(0.25)


def busy(root: Path = ROOT) -> bool:
    """Whether a run holds the suite now."""
    if not lock_of(root).exists():
        return False
    fd = os.open(lock_of(root), os.O_RDWR)
    try:
        return not _lock(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    root = Path(root)
    ap = argparse.ArgumentParser()
    ap.add_argument("--busy", action="store_true", help="exit 0 if another run holds the suite (saves/.suite_running), 1 if not")
    ap.add_argument("-j", type=int, default=2, help="tests at a time")
    ap.add_argument("--only", default="", help="comma-separated name fragments")
    ap.add_argument("--changed", default="", metavar="DIR", help="a copy of the last release to compare against")
    ap.add_argument("--outdir", default="/tmp/meravia_suite")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--wait", type=float, default=None, metavar="SECONDS", help="how long to wait for a run that holds the suite "
                                                                               "(default: 1200, or 2 with --changed)")
    ap.add_argument("--no-record", action="store_true", help="do not record what each test ran")
    args = ap.parse_args(argv)
    if args.busy:
        return 0 if busy(root) else 1
    tests = sorted((root / "tools" / "sim").glob("*_test.py"))
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        tests = [t for t in tests if any(k in t.name for k in keys)]
    held = take(root, wait=(2 if args.changed else 1200) if args.wait is None else args.wait)
    if held is None:
        try:
            who = lock_of(root).read_text(encoding="ascii").strip()
        except (OSError, ValueError):
            who = "?"
        print(f"another run holds the suite (saves/.suite_running, process {who}): nothing run")
        return HELD
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    results = []
    try:
        record = load_ran(root)
        if args.changed:
            files = changed_files(Path(args.changed), root)
            print(f"{len(files)} changed files")
            if record:
                tests = pick(tests, files, record, Path(args.changed), root)
                print(f"{len(tests)} tests picked by what each ran")
            else:
                print("no record of what the tests ran (a full run keeps one): picked by the words in them")
                tests = affected(tests, files)
        together, alone = lanes(tests)

        def one(t: Path) -> tuple[str, int, float]:
            name, rc, took = run_one(t, outdir, args.timeout, root, record=not args.no_record)
            got = None if args.no_record else ran_of(t, outdir)
            if got is not None and (rc == 0 or name not in record):       # a failed run may have stopped short: what it ran before stands
                record[name] = got
            print(f"{'ok  ' if rc == 0 else 'FAIL'} {name} ({took:.0f}s)", flush=True)
            return name, rc, took

        with ThreadPoolExecutor(max_workers=max(1, args.j)) as pool:
            results.extend(pool.map(one, together))
        for t in alone:
            results.append(one(t))
        if not args.no_record and results:
            if not args.only and not args.changed:                        # a full run: a test that is gone is forgotten
                record = {t: row for t, row in record.items() if any(t == r[0] for r in results)}
            keep_ran(root, record)
    finally:
        held.release()
    bad = [n for n, rc, _ in results if rc]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed in {time.time() - start:.0f}s")
    if results:
        print("slowest: " + ", ".join(f"{n} {t:.0f}s" for n, _, t in sorted(results, key=lambda r: -r[2])[:5]))
    if bad:
        print("FAILED: " + ", ".join(bad) + f"   (see {outdir}/<test>.out)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
