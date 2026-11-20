"""(f779) No test writes or trims the owner's logs: each test logs to a folder of its own, and a fence refuses the project's logs/.

llm/audit.py keeps the newest keep_sessions session files in its folder, and its folder was the project's own logs/audit. Older tests
that call the model through the gateway with the audit on each wrote a session there and pruned it, so every suite run deleted the
owner's play sessions (always older than the newest test's). The other logs (llm_calls, turns, sessions, pulse, refusals, crash.log,
reports) were written there too, and trimmed, and a log path a test named under saves/ landed in the real saves/. Now:
- core.paths.logs() is the one logs folder, asked at the call: the folder MERAVIA_LOGS names (a test's own), else logs/ beside the
  exe; core.paths.written() places every file the game writes by name from it, and while a test names its own folder any other
  relative path (a recording, a log a test named under saves/) lies in that folder too. With none named, as in play, every path is
  what it was.
- every log writer places its file through written(): the call log, the turns, the sessions, the pulse, the reports, and the
  audit's folder, which is logs/audit under the one logs folder (audit_log.yaml names no folder of its own).
- tools/run_suite.py names a logs folder for each test it runs (removed when it passes, kept as <test>_failed when it fails), and
  simlib names one for a test run by hand (a *_test.py script), which every process it starts inherits.
- a fence in every process of every test the runner starts (tools/suite_ran/sitecustomize.py) refuses a write or a removal under the
  project's own logs/ and recordings/, and the runner fails that test, naming the write.
Held here by planted tests, each in a process of its own. All but the fence's probe carry an audit hook of their own that refuses any
write under the project's logs/, recordings/ and saves/ before it happens; the fence's probe only aims at folders that are not there.
So nothing here reaches the owner's files, whatever the tree:
- the finder's case: an older test that calls the gateway with the audit on, run by the real runner, writes its audit session in a
  folder of its own outside the project, and nothing under logs/; and the rest of the kind beside it, each written by the game's own
  writer: llm_calls, turns, sessions, pulse, refusals, crash.log, a #report, a log named under saves/, and where the recordings,
  selfcheck.log and the model server's logs would go;
- a passed test's folder goes with its run, a failed one's is kept to be read;
- the fence: a test that writes under logs/ or removes under recordings/, itself or through a process it starts, is refused and
  failed by the runner;
- a test run by hand gets a folder of its own from simlib, which a process it starts inherits, gone when it ends; a tool that imports
  simlib keeps the project's logs/ (asked here, not written); a tool run by hand that plays the stub, tools/sim/fight_fixtures.py,
  names a folder of its own, so its compare writes nothing under logs/; the runner refuses an --outdir under logs/;
- the rule itself, with and without a folder named, and in a built game, which reads no test's folder; and a source check: every
  function of the game that reads a log setting of config places it through written(), each setting names a path under logs/, and
  the audit reads no folder from its table; (f781) and every setting of the logs (a path, a switch, a cap) is read off config
  itself, never with a fallback of its own, so config.py is its one home;
- the runner reads what a tree's own logs/ and recordings/ hold, for the line a run ends with (yes or no, nothing printed of it).
Run: python tools/sim/own_logs_779b_test.py"""
import ast
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import simlib                                                         # (f741, f779) saves and logs of the test's own
import yaml

import config
from core import paths
from tools import run_suite

bad: list[str] = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


def under(p, folder) -> bool:
    try:
        return Path(p).resolve().is_relative_to(Path(folder).resolve())
    except (TypeError, ValueError, OSError):
        return False


scratch = Path(tempfile.mkdtemp(prefix="f779b_")).resolve()
outdir = scratch / "out"
outdir.mkdir()

# the start of every planted script: the project's root is its working folder (the runner's, and the one given by hand here)
BASE = r'''import json, os, subprocess, sys, types
from pathlib import Path
ROOT_TEXT = os.getcwd()
sys.path.insert(0, ROOT_TEXT)


def own_files() -> list:
    own = os.environ.get("MERAVIA_LOGS", "")
    return sorted(p.relative_to(own).as_posix() for p in Path(own).rglob("*") if p.is_file()) if own and Path(own).is_dir() else []
'''

# ...and, for all but the fence's probe, a hook that refuses any write under the project's logs/, recordings/ and saves/
HOOK = r'''
GUARDED = tuple((Path(ROOT_TEXT) / d).resolve() for d in ("logs", "recordings", "saves"))
REFUSED = []
WRITES = ("os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.truncate", "shutil.rmtree", "sqlite3.connect")


def _fence(event, args):
    if event == "open":
        mode, flags = (list(args) + [None, None, None])[1:3]
        if not (isinstance(mode, str) and any(c in mode for c in "wax+")
                or mode is None and isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT)):
            return
    elif event not in WRITES:
        return
    for t in args[:2] if event == "os.rename" else args[:1]:
        if not isinstance(t, (str, bytes, os.PathLike)):
            continue
        try:
            p = Path(os.fsdecode(t)).resolve()
        except (OSError, ValueError):
            continue
        if any(p == g or g in p.parents for g in GUARDED):
            REFUSED.append(f"{event} {p}")
            raise PermissionError(f"(the probe's own fence) a write under the project's own folder: {p}")


sys.addaudithook(_fence)
'''

NAMED = "saves/f779b_named/turns.jsonl"                             # a log path named under saves/, as older tests name theirs
OLDER = BASE + HOOK + f"NAMED = {NAMED!r}\n" + r'''
import config
config.AUDIT_LOG = True                    # an older test: the audit on, as play has it, and no simlib.install
config.REFUSALS_LOG = True
from core import selfcheck
from engine import crashlog, pulselog, recording, refusals, turnlog
from llm import backend, gateway, runtime
from pydantic import BaseModel
from scenes.audit_actions import AuditActions


class Read(BaseModel):
    x: str


backend.use(backend.StandIn(chat=lambda **k: types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content='{"x": "fine"}')),
                            name="f779b"))
asked, errors = {}, {}


def write(kind, fn):
    try:
        fn()
    except Exception as e:
        errors[kind] = f"{type(e).__name__}: {e}"


def ask(kind, fn):
    try:
        asked[kind] = str(fn())
    except Exception as e:
        errors[kind] = f"{type(e).__name__}: {e}"


def a_report():
    fake = types.SimpleNamespace(store=types.SimpleNamespace(meta=types.SimpleNamespace(turn=3), name="f779b"),
                                 player=types.SimpleNamespace(location="nowhere"), recent_narration=["a passage"], partner=None)
    AuditActions.report_content(fake, "a note")


def named_under_saves():
    config.TURN_LOG_PATH = NAMED                                 # a log path an older test names under saves/ by hand
    turnlog._write({"turn": 2, "text": "f779b"})


write("audit", lambda: gateway.generate("stranger_read", "sys", "hi", Read, temperature=0.1))
write("crash", lambda: crashlog.note("f779b", "an older test's fault"))
write("refusals", lambda: refusals.note("refused", "f779b probe line", "an older test"))
write("turns", lambda: turnlog._write({"turn": 1, "text": "f779b"}))
write("pulse", lambda: pulselog.mark("moment", "f779b", 1))
turnlog.COUNTS["f779b"] = 1
write("sessions", turnlog.write_session_stats)
write("reports", a_report)
write("named under saves/", named_under_saves)
ask("recordings", recording.where)
ask("selfcheck.log", selfcheck.log_path)
ask("the server's logs", lambda: runtime.Runtime(cfg={}).logs)
print("F779B " + json.dumps({"own": os.environ.get("MERAVIA_LOGS", ""), "files": own_files(), "asked": asked, "errors": errors,
                             "refused": REFUSED}))
'''

FAILS = BASE + HOOK + r'''
from engine import crashlog
crashlog.note("f779b", "a failed test's fault, to be read")
print("FAIL a planted failure")
sys.exit(1)
'''

FENCED = BASE + r'''
got = {}


def write_logs():
    open(Path(ROOT_TEXT) / "logs" / f"f779b_no_such_{os.getpid()}" / "x.log", "w")


def remove_recording():
    os.remove(Path(ROOT_TEXT) / "recordings" / f"f779b_no_such_{os.getpid()}" / "x")


for label, fn in (("a write under logs/", write_logs), ("a removal under recordings/", remove_recording)):
    try:
        fn()
        got[label] = "done"
    except Exception as e:
        got[label] = type(e).__name__
probe = ("import os\ntry:\n    open(os.path.join(os.getcwd(), 'logs', 'f779b_no_such_' + str(os.getpid()), 'x.log'), 'w')\n    print('done')\n"
         "except Exception as e:\n    print(type(e).__name__)\n")
got["a write under logs/ by a process it starts"] = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True).stdout.strip()
print("F779B " + json.dumps(got))
'''

BY_HAND = BASE + HOOK + r'''
import simlib
from engine import crashlog
crashlog.note("f779b", "a test run by hand")
own = os.environ.get("MERAVIA_LOGS", "")
child = subprocess.run([sys.executable, "-c", "import os; print(os.environ.get('MERAVIA_LOGS', ''))"], capture_output=True, text=True).stdout.strip()
print("F779B " + json.dumps({"own": own, "child": child, "crash": str(crashlog.path()), "files": own_files(), "refused": REFUSED}))
'''

TOOL = BASE + HOOK + r'''
import simlib
from core import paths
from engine import crashlog
print("F779B " + json.dumps({"own": os.environ.get("MERAVIA_LOGS", ""), "crash": str(crashlog.path()), "logs": str(paths.written("logs")),
                             "refused": REFUSED}))
'''

FIXTURES = BASE + HOOK + r'''
import contextlib, io, runpy
sys.argv = ["fight_fixtures.py", "0"]                      # one shard's compare, as a person runs it by hand
said = io.StringIO()
code = None
with contextlib.redirect_stdout(said):
    try:
        runpy.run_path(os.path.join(ROOT_TEXT, "tools", "sim", "fight_fixtures.py"), run_name="__main__")
    except SystemExit as e:
        code = e.code
print("F779B " + json.dumps({"code": code, "shard": [l for l in said.getvalue().splitlines() if l.startswith("shard 0:")],
                             "refused": REFUSED[:6], "refused_n": len(REFUSED)}))
'''

OUTDIR = BASE + HOOK + r'''
from tools import run_suite
rc = run_suite.main(["--outdir", os.path.join(ROOT_TEXT, "logs", f"f779b_no_such_{os.getpid()}"), "--only", "no_such_test_f779b"])
print("F779B " + json.dumps({"rc": rc, "refused": REFUSED}))
'''


def plant(name: str, text: str) -> Path:
    p = scratch / "planted" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def said(text: str) -> dict:
    line = next((l[6:] for l in text.splitlines() if l.startswith("F779B ")), None)
    return json.loads(line) if line else {}


def by_runner(name: str, text: str) -> tuple[int, str, dict]:
    """The planted test run by the real runner (run_one), the project its root: (exit code, its output, what it said)."""
    test = plant(name, text)
    _, rc, _ = run_suite.run_one(test, outdir, 300, ROOT)
    out = (outdir / f"{test.name}.out").read_text(encoding="utf-8", errors="replace")
    return rc, out, said(out)


try:
    # ---- the finder's case and the rest of its kind: an older test under the runner, the audit on
    rc, out, got = by_runner("planted_older_779b_test.py", OLDER)
    own = got.get("own", "")
    check("the planted older test ran to its end under the runner", rc == 0 and bool(got), (rc, out[-1500:]))
    check("...with a logs folder of its own that the runner named (MERAVIA_LOGS), outside the project", bool(own) and not under(own, ROOT)
          and under(own, outdir), own)
    check("...and nothing it did wrote, trimmed or removed anything under the project's logs/, recordings/ or saves/ (the audit's"
          " session and its prune among them)", got.get("refused") == [], (got.get("refused") or [])[:6])
    files = got.get("files") or []
    want = {"the audit's session (gateway with the audit on)": lambda f: f.startswith("audit/") and f.endswith(".md"),
            "llm_calls": lambda f: f == "llm_calls.jsonl", "turns": lambda f: f == "turns.jsonl", "sessions": lambda f: f == "sessions.jsonl",
            "pulse": lambda f: f == "pulse.jsonl", "refusals": lambda f: f == "refusals.jsonl", "crash.log": lambda f: f == "crash.log",
            "a #report": lambda f: f.startswith("reports/") and f.endswith(".json"),
            "a log named under saves/ by hand": lambda f: f == NAMED}
    missing = [k for k, ok in want.items() if not any(ok(f) for f in files)]
    check("...each written by the game's own writer into that folder: the audit's session, llm_calls, turns, sessions, pulse,"
          " refusals, crash.log, a #report, and a log a test named under saves/", not missing and not got.get("errors"),
          (missing, got.get("errors"), files))
    asked = got.get("asked") or {}
    elsewhere = {k: v for k, v in asked.items() if not under(v, own)} if own else asked
    check("...and the recordings, selfcheck.log and the model server's logs would lie there too", len(asked) == 3 and not elsewhere,
          elsewhere or asked)
    check("a passed test's logs folder goes with its run", bool(own) and not Path(own).exists(), own)

    rc_f, out_f, _ = by_runner("planted_fails_779b_test.py", FAILS)
    kept = outdir / "logs_of" / "planted_fails_779b_test_failed"
    check("a failed test's logs folder is kept to be read: its crash.log is there", rc_f != 0 and (kept / "crash.log").is_file()
          and "to be read" in (kept / "crash.log").read_text(encoding="utf-8"),
          (rc_f, sorted(p.name for p in kept.parent.iterdir()) if kept.parent.is_dir() else "no logs_of"))

    # ---- the fence, in the test and in a process it starts
    rc_x, out_x, got_x = by_runner("planted_fenced_779b_test.py", FENCED)
    check("the fence: a test that writes under the project's logs/ is refused, as is a removal under recordings/, and a process it"
          " starts is fenced too (each probe aims at a folder that is not there, so nothing is made either way)",
          bool(got_x) and set(got_x.values()) == {"PermissionError"} and len(got_x) == 3, got_x or out_x[-800:])
    check("...and the runner fails that test, naming the write", rc_x != 0 and "f779b_no_such_" in out_x
          and any(l.startswith("FAIL") and "logs" in l for l in out_x.splitlines()), (rc_x, out_x[-800:]))

    # ---- a test run by hand, and a tool that imports simlib
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MERAVIA_LOGS", "MERAVIA_SAVES", "MERAVIA_FENCE", "MERAVIA_RAN", "DND_"))}
    env.update(PYTHONUTF8="1", PYTHONPATH=str(ROOT))
    hand = plant("by_hand_779b_test.py", BY_HAND)
    done = subprocess.run([sys.executable, str(hand)], cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=300)
    got_h = said(done.stdout)
    own_h = got_h.get("own", "")
    check("a test run by hand (a *_test.py script, no runner) gets a logs folder of its own from simlib, outside the project",
          bool(own_h) and not under(own_h, ROOT), (own_h, done.stderr[-800:]))
    check("...its crash.log lies there, nothing is written under the project's folders, and a process it starts inherits it",
          bool(own_h) and under(got_h.get("crash", ""), own_h) and "crash.log" in (got_h.get("files") or []) and got_h.get("refused") == []
          and got_h.get("child") == own_h, got_h)
    check("...and the folder is gone when it ends", bool(own_h) and not Path(own_h).exists(), own_h)
    tool = plant("a_tool_779b.py", TOOL)
    done_t = subprocess.run([sys.executable, str(tool)], cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=300)
    got_t = said(done_t.stdout)
    check("a tool that imports simlib (no *_test.py) keeps the project's logs/: nothing is moved for it (asked, not written)",
          got_t.get("own") == "" and Path(got_t.get("crash", "")) == ROOT / "logs" / "crash.log"
          and Path(got_t.get("logs", "")) == ROOT / "logs" and got_t.get("refused") == [], (got_t, done_t.stderr[-800:]))
    fx_env = dict(env, MERAVIA_SAVES=str(scratch / "fixtures_saves"))  # its saves aside: this asks only where its logs go
    fixtures = plant("fixtures_by_hand_779b.py", FIXTURES)
    done_f = subprocess.run([sys.executable, str(fixtures)], cwd=str(ROOT), env=fx_env, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=600)
    got_f = said(done_f.stdout)
    check("a tool run by hand that plays the stub, tools/sim/fight_fixtures.py, compares a shard and writes nothing under the project's"
          " logs/ (its calls and turns go to a folder of its own, which it removes)",
          bool(got_f) and got_f.get("refused_n") == 0 and got_f.get("code") in (0, None) and len(got_f.get("shard") or []) == 1,
          (got_f or done_f.stdout[-600:], done_f.stderr[-800:]))
    outdir_run = plant("outdir_779b.py", OUTDIR)
    done_o = subprocess.run([sys.executable, str(outdir_run)], cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=300)
    got_o = said(done_o.stdout)
    check("the runner refuses an --outdir under the project's own logs/ (where the fence would refuse its own note), before it takes"
          " the lock or makes anything", got_o.get("rc") == 2 and got_o.get("refused") == [], (got_o, done_o.stdout[-400:], done_o.stderr[-600:]))

    # ---- the rule itself, with a folder named and without
    logs_fn = getattr(paths, "logs", None)
    check("core.paths.logs() is the one logs folder", callable(logs_fn), logs_fn)
    held_env = os.environ.get("MERAVIA_LOGS")
    named = scratch / "named_logs"
    try:
        os.environ["MERAVIA_LOGS"] = str(named)
        got_named = {"logs()": logs_fn() if callable(logs_fn) else None, "logs/a/b.log": paths.written("logs/a/b.log"),
                     "logs": paths.written("logs"), "recordings/r": paths.written("recordings/r"),
                     "absolute": paths.written(scratch / "abs.log")}
        os.environ.pop("MERAVIA_LOGS")
        got_play = {"logs()": logs_fn() if callable(logs_fn) else None, "logs/a/b.log": paths.written("logs/a/b.log"),
                    "recordings/r": paths.written("recordings/r"), "absolute": paths.written(scratch / "abs.log")}
        os.environ["MERAVIA_LOGS"] = str(named)                       # a built game, with a test's folder named all the same
        held_sys = {"frozen": getattr(sys, "frozen", None), "_MEIPASS": getattr(sys, "_MEIPASS", None)}, sys.executable
        exe_dir = scratch / "installed"
        try:
            sys.frozen, sys._MEIPASS, sys.executable = True, str(ROOT), str(exe_dir / "Meravia.exe")
            importlib.reload(paths)
            got_built = {"logs()": logs_fn and paths.logs(), "logs/a/b.log": paths.written("logs/a/b.log"),
                         "recordings/r": paths.written("recordings/r")}
        finally:
            for attr, was in held_sys[0].items():
                if was is None:
                    if hasattr(sys, attr):
                        delattr(sys, attr)
                else:
                    setattr(sys, attr, was)
            sys.executable = held_sys[1]
            importlib.reload(paths)
    finally:
        if held_env is None:
            os.environ.pop("MERAVIA_LOGS", None)
        else:
            os.environ["MERAVIA_LOGS"] = held_env
    check("with a folder named (a test's): logs/ is that folder, and every other relative path the game writes by name lies in it",
          got_named == {"logs()": named, "logs/a/b.log": named / "a" / "b.log", "logs": named, "recordings/r": named / "recordings" / "r",
                        "absolute": scratch / "abs.log"}, got_named)
    check("...and with none, as in play, every path is what it was: under APP, an absolute one as it is",
          got_play == {"logs()": paths.APP / "logs", "logs/a/b.log": paths.APP / "logs" / "a" / "b.log",
                       "recordings/r": paths.APP / "recordings" / "r", "absolute": scratch / "abs.log"}, got_play)
    check("...and a built game reads no test's folder: with one named, its logs and recordings lie beside the exe all the same",
          got_built == {"logs()": exe_dir / "logs", "logs/a/b.log": exe_dir / "logs" / "a" / "b.log",
                        "recordings/r": exe_dir / "recordings" / "r"} and not paths.FROZEN, got_built)

    # ---- the audit's folder has one home: the logs folder
    table = yaml.safe_load((ROOT / "data" / "rules" / "audit_log.yaml").read_text(encoding="utf-8"))
    audit_src = (ROOT / "llm" / "audit.py").read_text(encoding="utf-8")
    check("the audit's folder is logs/audit under the one logs folder: audit_log.yaml names none, and llm/audit.py reads none from it",
          "folder" not in table and 'A.get("folder"' not in audit_src and 'A["folder"]' not in audit_src, sorted(table))

    # ---- the source check: every log setting is placed through written(), and names a path under logs/
    settings = sorted(n for n in dir(config) if n.endswith("_PATH") and isinstance(getattr(config, n), str))

    def unplaced(text: str) -> list[str]:
        """Each function (or the module's own lines) that reads a config setting named *_PATH (config.X_PATH, getattr(config,
        "X_PATH", ...)) and calls no written(...): the line and the name it stands in."""
        t = ast.parse(text)
        out = []
        scopes = [n for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        inner = {id(c) for s in scopes for c in ast.walk(s) if c is not s}

        def reads(node) -> list[int]:
            hits = []
            for n in ast.walk(node):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "config" and n.attr.endswith("_PATH") \
                        and isinstance(n.ctx, ast.Load):
                    hits.append(n.lineno)
                elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2 \
                        and isinstance(n.args[0], ast.Name) and n.args[0].id == "config" and isinstance(n.args[1], ast.Constant) \
                        and str(n.args[1].value).endswith("_PATH"):
                    hits.append(n.lineno)
            return hits

        def places(node) -> bool:
            return any(isinstance(n, ast.Call) and (isinstance(n.func, ast.Attribute) and n.func.attr == "written"
                                                    or isinstance(n.func, ast.Name) and n.func.id == "written") for n in ast.walk(node))
        for s in scopes:
            if id(s) in inner:
                continue                                              # a nested function is read with the one it stands in
            if reads(s) and not places(s):
                out.append(f"{s.lineno} ({s.name})")
        top = [n for n in t.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        out += [f"{line} (<module>)" for n in top for line in reads(n) if not places(n)]
        return out

    planted = {
        "import config\nfrom pathlib import Path\ndef f():\n    return Path(config.LOG_PATH)\n": True,
        "import config\ndef f():\n    with open(getattr(config, 'TURN_LOG_PATH', 'logs/t.jsonl'), 'a') as fh:\n        fh.write('x')\n": True,
        "import config\nfrom pathlib import Path\nP = Path(config.CRASH_LOG_PATH)\n": True,
        "import config\nclass A:\n    def report(self):\n        return open(getattr(config, 'REPORTS_PATH', 'logs/reports'))\n": True,
        "import config\nfrom core import paths\ndef f():\n    return paths.written(config.LOG_PATH)\n": False,
        "import config\nfrom core import paths\ndef f():\n    p = getattr(config, 'PULSE_LOG_PATH', '')\n    if not p:\n        return None\n"
        "    return paths.written(p)\n": False,
        "import config\ndef f():\n    return config.LOG_MAX_MB\n": False,
    }
    caught = {src: bool(unplaced(src)) == want for src, want in planted.items()}
    check("the source check catches a log setting read and not placed through written(), planted (a Path, an open, a module's own"
          " line, a method), and passes one placed, one checked first, and a setting that is no path", all(caught.values()),
          [s for s, ok in caught.items() if not ok])
    GAME = ("core", "engine", "llm", "scenes", "storage", "world", "ui", "npc", "character", "services")
    files_ = [p for d in GAME for p in sorted((ROOT / d).rglob("*.py")) if "__pycache__" not in p.parts] + [ROOT / "main.py"]
    loose = [f"{p.relative_to(ROOT).as_posix()}:{x}" for p in files_ for x in unplaced(p.read_text(encoding="utf-8"))]
    check("every function of the game that reads a log setting of config places it through core.paths.written(): one rule for"
          " where a log lies, so a log a test names, or the folder a test is given, is honoured by every writer",
          not loose and len(files_) > 100, loose)
    check("...and every log setting of config names a path under logs/, so the one logs folder decides each",
          len(settings) >= 6 and all(getattr(config, n).startswith("logs/") for n in settings),
          {n: getattr(config, n) for n in settings if not getattr(config, n).startswith("logs/")})

    # ---- (f781) each setting of the logs has one home, config.py: the game reads it off config, never with a fallback of its own
    import re
    LOG_SETTING = re.compile(r"^LOG_|_LOG$|_PATH$|_KEEP$")            # where a log lies, whether it is written, how much it keeps

    def two_homes(text: str) -> list[str]:
        """Each read of a log setting with a fallback (getattr(config, NAME, default): the default is a second home, free to drift from
        config.py's), and each read of one config.py does not define: the line and the name."""
        out = []
        for n in ast.walk(ast.parse(text)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 3 \
                    and isinstance(n.args[0], ast.Name) and n.args[0].id == "config" and isinstance(n.args[1], ast.Constant) \
                    and LOG_SETTING.search(str(n.args[1].value)):
                out.append(f"{n.lineno} ({n.args[1].value}, with a fallback)")
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "config" \
                    and isinstance(n.ctx, ast.Load) and LOG_SETTING.search(n.attr) and not hasattr(config, n.attr):
                out.append(f"{n.lineno} ({n.attr}, which config.py does not define)")
        return out

    planted = {
        "import config\nKEEP = int(getattr(config, 'CRASH_KEEP', 50))\n": True,
        "import config\nfrom core import paths\ndef path():\n    return paths.written(getattr(config, 'CRASH_LOG_PATH', 'logs/c.log'))\n": True,
        "import config\ndef note():\n    if not getattr(config, 'REFUSALS_LOG', True):\n        return\n": True,
        "import config\ndef trim():\n    return getattr(config, 'LOG_MAX_MB', None) or 5\n": True,
        "import config\nfrom core import paths\ndef path():\n    return paths.written(config.X_NEVER_SET_PATH)\n": True,
        "import config\nKEEP = int(config.CRASH_KEEP)\n": False,
        "import config\nfrom core import paths\ndef path():\n    return paths.written(config.CRASH_LOG_PATH)\n": False,
        "import config\nx = getattr(config, 'VOICED_MENTOR', True)\n": False,
    }
    caught = {src: bool(two_homes(src)) == want for src, want in planted.items()}
    check("(f781) the source check catches a log setting read with a fallback of its own, planted (a cap, a path, a switch, a fallback "
          "after `or`) and one config.py does not define, and passes one read off config and a setting that is not a log's",
          all(caught.values()), [s for s, ok in caught.items() if not ok])
    twice = [f"{p.relative_to(ROOT).as_posix()}:{x}" for p in files_ for x in two_homes(p.read_text(encoding="utf-8"))]
    check("...and every log setting the game reads has one home, config.py: read off config itself, so a value changed there is the "
          "value every reader meets", not twice, twice)

    # ---- the runner says, by counts alone, whether a tree's own logs/ and recordings/ changed while it ran
    owners = getattr(run_suite, "owners", None)
    check("the runner reads what a tree's own logs/ and recordings/ hold (run_suite.owners), for the line a run ends with",
          callable(owners), owners)
    if callable(owners):
        tree = scratch / "tree"
        (tree / "logs" / "audit").mkdir(parents=True)
        (tree / "logs" / "audit" / "2026-11-01_120000.md").write_text("a session", encoding="utf-8")
        (tree / "recordings" / "r1").mkdir(parents=True)
        (tree / "recordings" / "r1" / "meta.json").write_text("{}", encoding="utf-8")
        first = owners(tree)
        same = owners(tree)
        (tree / "logs" / "crash.log").write_text("x", encoding="utf-8")
        check("...each file once, the same when nothing changed, and a new file seen", len(first) == 2 and first == same
              and len(owners(tree)) == 3, (first, owners(tree)))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
