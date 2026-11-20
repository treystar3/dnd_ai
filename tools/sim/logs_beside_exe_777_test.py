"""(f777) The files the game writes under the code's own folder are placed by core.paths, so the logs land beside the exe (audit:
dead-switches-2, shell1-8, llm1-3).

In a built game a module's __file__ lies inside the bundle (_internal), not beside the exe. Four writers worked their folder out from
it: crash.log (engine/crashlog.py), the refusals (engine/refusals.py), the audit log (llm/audit.py) and the recordings
(engine/recording.py, DND_RECORD=1). So a built game wrote them inside the bundle, where the player is never pointed and which the next
install replaces, while the other logs lay in logs/ beside the exe. core.paths.written(rel) now places each, and the two files that
were joined onto APP by hand (selfcheck.log, the model server's logs): APP joined to a relative path at the call, an absolute path (a
test's, a night tool's) as it is. The files named relative to the working folder (turns, llm_calls, sessions, pulse, reports, the saves)
are left so: main.py puts the working folder at APP in a build. The audit reads its settings from core.paths.BUNDLE, as the load screen
reads its lines. Held here:
- core.paths.written: a relative path under APP, asked at the call; an absolute one returned unchanged;
- with core.paths reloaded as a build and BUNDLE apart from both APP and the code's folder: crash.log, the refusals and the audit's
  file are written under APP/logs; the recorder makes its recording under APP (a writer other than the three logs that found it), and
  prunes there; selfcheck.log and the model server's logs lie under APP/logs too; the audit's settings are read from BUNDLE; a tool's
  absolute path is kept by each;
- a process started as a built game is started (sys.frozen, the exe in a folder of its own, main.py imported) writes those files,
  the server's crash notes among them, beside the exe and nothing under the code's folder; and the files named relative to the
  working folder (turns, llm_calls, sessions, pulse, reports, the saves) resolve under APP where main.py puts it (a pin: true before
  this change, and kept);
- a source check over every game module, in the forms it reads (a / b, joinpath, os.path.join, Path(a, b); names assigned, annotated
  or given as a parameter's default; core.paths.APP however it is named): none joins anything but data/ onto a path made from
  __file__ (the startup check's readers and one frame filter are named, with why), and none but core.paths joins onto core.paths.APP;
  each form seen caught, planted. An f-string, .with_name or a string added on are not read.
A fence (an audit hook) refuses any write under the project's own logs/ and recordings/ while this runs, in this process and in the one
it starts; its saves are a folder of its own (f741).
Run: python tools/sim/logs_beside_exe_777_test.py"""
import ast
import contextlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import simlib                                                         # (f741) a saves folder of the test's own
import yaml
stub = simlib.Stub("warrior", 777)
simlib.install(stub)
import config
from core import paths, selfcheck
from engine import crashlog, recording, refusals
from llm import audit, runtime

bad: list[str] = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


def attempt(fn):
    """fn's answer, or the exception it raised."""
    try:
        return fn()
    except Exception as e:
        return e


def text_of(p) -> str:
    """The text of the file at p, or "" when there is none (or p is no path)."""
    try:
        return Path(p).read_text(encoding="utf-8")
    except (TypeError, OSError):
        return ""


def under(p, folder) -> bool:
    """p lies in folder (both resolved); False for anything that is no path."""
    try:
        return Path(p).resolve().is_relative_to(Path(folder).resolve())
    except (TypeError, ValueError, OSError):
        return False


# ---- the fence: no write under the project's own logs/ or recordings/, whichever module makes it (the saves folder is f741's: a test's own)
FENCE = r'''
import os
from pathlib import Path
GUARDED = tuple((Path(ROOT_TEXT) / d).resolve() for d in ("logs", "recordings"))
REFUSED = []
WRITES = ("os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.truncate", "shutil.rmtree", "shutil.copyfile", "sqlite3.connect")


def _fence(event, args):
    if event == "open":
        mode, flags = (list(args) + [None, None, None])[1:3]
        if not (isinstance(mode, str) and any(c in mode for c in "wax+")
                or mode is None and isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT)):
            return
    elif event not in WRITES:
        return
    for t in args[:2] if event in ("os.rename", "shutil.copyfile") else args[:1]:
        if not isinstance(t, (str, bytes, os.PathLike)):
            continue
        try:
            p = Path(os.fsdecode(t)).resolve()
        except (OSError, ValueError):
            continue
        if any(p == g or g in p.parents for g in GUARDED):
            REFUSED.append(f"{event} {p}")
            raise PermissionError(f"(f777's fence) a write under the project's own folder: {p}")
'''
fence_ns = {"ROOT_TEXT": str(ROOT)}
exec(FENCE, fence_ns)
sys.addaudithook(fence_ns["_fence"])
REFUSED = fence_ns["REFUSED"]

scratch = Path(tempfile.mkdtemp(prefix="f777_")).resolve()           # the long name: Windows' TEMP may be 8.3 (RUNNER~1)
LOGS = scratch / "own_logs"                                          # this test's own logs, where it is not asking where they go
DEFAULTS = {k: getattr(config, k) for k in ("CRASH_LOG_PATH", "REFUSALS_LOG_PATH", "REFUSALS_LOG")}
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, str(LOGS / fn))
bundle, app, tool = scratch / "bundle", scratch / "app", scratch / "a_tool"
(bundle / "data" / "rules").mkdir(parents=True)
app.mkdir()
PLANTED = 77                                                         # (f779) a ceiling only the bundle's settings name
DECOY = scratch / "a_test_logs"                                       # (f779) a test's logs folder, named while the game is a build
kept_settings = (ROOT / "data" / "rules" / "audit_log.yaml").read_text(encoding="utf-8")
PROJECT_MB = yaml.safe_load(kept_settings).get("max_mb")
(bundle / "data" / "rules" / "audit_log.yaml").write_text(re.sub(r"(?m)^max_mb:\s*\S+", f"max_mb: {PLANTED}", kept_settings, count=1),
                                                          encoding="utf-8")


@contextlib.contextmanager
def replaced(obj, name, value):
    was = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, was)


@contextlib.contextmanager
def as_build():
    """core.paths reloaded as a built game's: BUNDLE where its data is unpacked, APP the exe's folder, both apart from the code's folder.
    The audit is imported again inside it, as a built game first imports it; both are put back after."""
    saved = {"frozen": getattr(sys, "frozen", None), "meipass": getattr(sys, "_MEIPASS", None), "exe": sys.executable}
    env_before = {k: os.environ.pop(k, None) for k in ("MERAVIA_RUNTIME", "MERAVIA_MODELS", "MERAVIA_RUN", "MERAVIA_LOGS")}
    os.environ["MERAVIA_LOGS"] = str(DECOY)                          # (f779) a test's logs folder named: a built game must not read it
    try:
        sys.frozen = True
        sys._MEIPASS = str(bundle)
        sys.executable = str(app / "Meravia.exe")
        importlib.reload(paths)
        importlib.reload(audit)
        yield
    finally:
        os.environ.pop("MERAVIA_LOGS", None)
        for k, v in env_before.items():
            if v is not None:
                os.environ[k] = v
        for attr, key in (("frozen", "frozen"), ("_MEIPASS", "meipass")):
            if saved[key] is None:
                if hasattr(sys, attr):
                    delattr(sys, attr)
            else:
                setattr(sys, attr, saved[key])
        sys.executable = saved["exe"]
        importlib.reload(paths)
        importlib.reload(audit)


try:
    # ---- the one helper
    w = getattr(paths, "written", None)
    check("core.paths has one helper that places a file the game writes: written(rel)", callable(w), w)
    if callable(w):
        held_logs = os.environ.pop("MERAVIA_LOGS", None)              # (f779) as a player's game is: no test's logs folder named
        try:
            with replaced(paths, "APP", scratch / "exe_folder"):
                rel = attempt(lambda: w("logs/x.log"))
        finally:
            if held_logs is not None:
                os.environ["MERAVIA_LOGS"] = held_logs
        check("...a relative path lies under APP, asked at the call", rel == scratch / "exe_folder" / "logs" / "x.log", rel)
        check("...an absolute one (a test's, a night tool's) is returned as it is", attempt(lambda: w(tool / "x.log")) == tool / "x.log"
              and attempt(lambda: w(str(tool / "x.log"))) == tool / "x.log", attempt(lambda: w(tool / "x.log")))

    # ---- the finder's case and the rest of its kind, with core.paths reloaded as a build and BUNDLE apart from APP
    game = simlib.campaign("f777_recorded", seed=777)                  # a store for the recorder, made from source
    planted_rec = app / "recordings" / "an_old_one"
    with as_build():
        check("a build: BUNDLE where the data is unpacked, APP the exe's folder, each apart from the other and from the code's folder",
              paths.FROZEN and paths.BUNDLE == bundle and paths.APP == app and not under(app, ROOT), (paths.BUNDLE, paths.APP))
        config.CRASH_LOG_PATH, config.REFUSALS_LOG_PATH, config.REFUSALS_LOG = DEFAULTS["CRASH_LOG_PATH"], DEFAULTS["REFUSALS_LOG_PATH"], True
        crash_path = attempt(crashlog.path)
        crashlog.record(RuntimeError("f777 probe"), "f777: where the fault goes")
        check("crash.log lies under APP/logs: the fault is written beside the exe (dead-switches-2, shell1-8)",
              crash_path == app / "logs" / "crash.log" and "f777 probe" in text_of(app / "logs" / "crash.log"),
              (crash_path, crashlog.path()))
        refusals.note("refused", "f777 probe line", "where the refusals go")
        refusals.SESSION.pop()
        ref_path = attempt(lambda: refusals.path())
        check("the refusals too: refusals.jsonl under APP/logs, written there",
              ref_path == app / "logs" / "refusals.jsonl" and "f777 probe line" in text_of(app / "logs" / "refusals.jsonl"), ref_path)
        check("the audit's settings are read from BUNDLE, where a built game's data is", audit.A.get("max_mb") == PLANTED, audit.A.get("max_mb"))
        audit_file = attempt(audit.path)
        check("...and its session file is written under APP/logs, in the one logs folder's audit/ (llm1-3; f779)",
              isinstance(audit_file, Path) and audit_file.parent == app / "logs" / "audit" and audit_file.is_file(), audit_file)
        config.REFUSALS_LOG = False
        rec = attempt(lambda: recording.Recorder(game.store, name="f777_probe"))
        if isinstance(rec, recording.Recorder):
            rec.close()
        check("a writer other than the three logs: the recorder makes its recording under APP (DND_RECORD=1 in a built game)",
              isinstance(rec, recording.Recorder) and rec.dir == app / "recordings" / "f777_probe" and (rec.dir / "start.db").is_file()
              and (rec.dir / "meta.json").is_file(), rec if not isinstance(rec, recording.Recorder) else rec.dir)
        planted_rec.mkdir(parents=True, exist_ok=True)
        (planted_rec / "meta.json").write_text("{}", encoding="utf-8")
        recording.prune(keep=0)
        check("...and prunes the recordings it keeps there, where it makes them", not planted_rec.exists() and not (app / "recordings" / "f777_probe").exists(),
              sorted(p.name for p in (app / "recordings").iterdir()) if (app / "recordings").exists() else "no folder")
        check("selfcheck.log lies under APP/logs", attempt(selfcheck.log_path) == app / "logs" / "selfcheck.log", attempt(selfcheck.log_path))
        check("...and the model server's logs (its crash notes among them)", attempt(lambda: runtime.Runtime(cfg={}).logs) == app / "logs",
              attempt(lambda: runtime.Runtime(cfg={}).logs))
        left = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file())
        check("...and nothing is written into the bundle", left == ["data/rules/audit_log.yaml"], left)

        # a tool's absolute path is kept by each
        config.CRASH_LOG_PATH, config.REFUSALS_LOG_PATH = str(tool / "crash.log"), str(tool / "refusals.jsonl")
        check("a tool's absolute paths are kept: crash.log and the refusals", attempt(crashlog.path) == tool / "crash.log"
              and attempt(lambda: refusals.path()) == tool / "refusals.jsonl", (attempt(crashlog.path), attempt(lambda: refusals.path())))
        audit._path = None
        with replaced(audit, "FOLDER", tool / "audit"):
            tool_audit = attempt(audit.path)
        audit._path = None
        with replaced(recording, "FOLDER", tool / "recordings"):
            tool_rec = attempt(lambda: recording.where())
        check("...the audit's folder and the recorder's", isinstance(tool_audit, Path) and tool_audit.parent == tool / "audit"
              and tool_rec == tool / "recordings", (tool_audit, tool_rec))
    game.session.close()
    config.CRASH_LOG_PATH, config.REFUSALS_LOG_PATH = str(LOGS / "crash.log"), str(LOGS / "refusals.jsonl")
    check("from source both are the project folder again, and the audit reads its settings there",
          not paths.FROZEN and paths.APP == ROOT and paths.BUNDLE == ROOT and audit.A.get("max_mb") == PROJECT_MB != PLANTED,
          (paths.APP, audit.A.get("max_mb"), PROJECT_MB))

    # ---- a process started as a built game is: the working folder where main.py puts it, every file it writes beside the exe
    probe_dir, exe_dir = scratch / "probe", scratch / "installed"
    probe_dir.mkdir()
    exe_dir.mkdir()
    probe = probe_dir / "built_start_777.py"
    probe.write_text("import json, os, sys\nfrom pathlib import Path\nROOT_TEXT, APP = sys.argv[1], Path(sys.argv[2])\n" + FENCE + r'''
sys.addaudithook(_fence)
sys.path.insert(0, ROOT_TEXT)
sys.frozen, sys._MEIPASS, sys.executable = True, ROOT_TEXT, str(APP / "Meravia.exe")   # the code's folder is the bundle, as when built
import main                                                                             # as the built game starts


def ask(fn):
    try:
        return str(fn())
    except Exception as e:
        return f"{type(e).__name__}: {e}"


import config
from core import paths, selfcheck
from engine import crashlog, recording, refusals, turnlog
from llm import audit, runtime
from storage import campaign
crashlog.record(RuntimeError("f777 probe"), "f777: where the fault goes")
config.REFUSALS_LOG = True
refusals.note("refused", "f777 probe line", "where the refusals go")
out = {"cwd": os.getcwd(), "app": str(paths.APP), "bundle": str(paths.BUNDLE),
       "written": {"crash.log": ask(crashlog.path), "refusals": ask(lambda: refusals.path()), "audit": ask(audit.path),
                   "recordings": ask(lambda: recording.where()), "selfcheck.log": ask(selfcheck.log_path),
                   "the server's crash notes": ask(lambda: runtime.Runtime(cfg={}).logs / "crash.log")},
       "working": {"turns": ask(lambda: turnlog.path().resolve()), "llm_calls": ask(lambda: Path(config.LOG_PATH).resolve()),
                   "sessions": ask(lambda: Path(config.SESSION_STATS_PATH).resolve()), "pulse": ask(lambda: Path(config.PULSE_LOG_PATH).resolve()),
                   "reports": ask(lambda: Path(getattr(config, "REPORTS_PATH", "logs/reports")).resolve()),
                   "the saves folder": ask(lambda: campaign.SAVES_DIR.resolve())},
       "refused": REFUSED}
print("F777 " + json.dumps(out))
''', encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DND_", "MERAVIA_SAVES", "MERAVIA_RUNTIME", "MERAVIA_MODELS", "MERAVIA_RUN"))}
    env.update(PYTHONUTF8="1", PYTHONPATH=str(ROOT), MERAVIA_LOGS=str(DECOY))   # (f779) a test's logs folder named: the build ignores it
    done = subprocess.run([sys.executable, str(probe), str(ROOT), str(exe_dir)], cwd=str(scratch), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=300)
    line = next((l[5:] for l in done.stdout.splitlines() if l.startswith("F777 ")), None)
    got = json.loads(line) if line else {}
    check("a process started as a built game runs to its end", done.returncode == 0 and got, (done.returncode, done.stderr[-1500:]))
    if got:
        check("...its working folder is where main.py puts it, beside the exe, and its bundle is the code's folder",
              Path(got["cwd"]) == exe_dir and Path(got["app"]) == exe_dir and Path(got["bundle"]) == ROOT, (got["cwd"], got["app"], got["bundle"]))
        wrong = {k: v for k, v in got["written"].items() if not under(v, exe_dir / "logs" if k != "recordings" else exe_dir) or under(v, ROOT)}
        check("...crash.log, the refusals, the audit's file, selfcheck.log, the server's crash notes and the recordings, each placed by"
              " core.paths, lie beside the exe, none under the code's folder", not wrong and len(got["written"]) == 6, wrong)
        landed = {name: (exe_dir / "logs" / name).is_file() for name in ("crash.log", "refusals.jsonl")}
        landed["audit"] = any((exe_dir / "logs" / "audit").glob("*.md")) if (exe_dir / "logs" / "audit").is_dir() else False
        check("...and the files it wrote are there: the logs folder the player is pointed to holds them", all(landed.values()), landed)
        pinned = {k: v for k, v in got["working"].items() if not under(v, exe_dir)}
        check("the files named relative to the working folder (turns, llm_calls, sessions, pulse, reports, the saves) resolve beside"
              " the exe, where main.py puts the working folder in a build", not pinned and len(got["working"]) == 6, pinned)
        check("...and that process wrote nothing under the code's folder", got["refused"] == [], got["refused"][:5])
    check("a build reads no test's logs folder: with MERAVIA_LOGS named, in this process and in the one started as a build, nothing"
          " was written there (f779)", not DECOY.exists() or not any(p.is_file() for p in DECOY.rglob("*")),
          sorted(str(p) for p in DECOY.rglob("*"))[:5])

    # ---- the source check: nothing but data/ is joined onto a path made from __file__; nothing but core.paths joins onto APP
    GAME = ("core", "engine", "llm", "scenes", "storage", "world", "ui", "npc", "character", "services")
    ALLOWED = {                                       # (file, top-level name): why it may join something else onto the code's folder
        ("engine/data_check.py", "source"): "the startup check's one reader of the code's own source (f775)",
        ("engine/data_check.py", "modules"): "the same reader: the code's modules listed",
        ("engine/data_check.py", "_load"): "the startup check's loader: a data file by its path under the root (data/...)",
        ("engine/data_check.py", "_why"): "the same loader, telling why a data file failed",
        ("storage/worldrow.py", "_SKIP"): "frames of its own code told apart by file name: nothing read or written",
    }

    def joined(node):
        """(the base, the first part joined) of a join written a / b, a.joinpath(b), os.path.join(a, b) or Path(a, b); else None."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            base = node
            while isinstance(base, ast.BinOp) and isinstance(base.op, ast.Div):
                first, base = base.right, base.left
            return base, first
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "joinpath" and node.args:
                return f.value, node.args[0]
            if (isinstance(f, ast.Attribute) and f.attr == "join" and isinstance(f.value, ast.Attribute) and f.value.attr == "path"
                    or isinstance(f, ast.Name) and f.id == "Path") and len(node.args) >= 2:
                return node.args[0], node.args[1]
        return None

    def is_data(part, consts: dict) -> bool:
        """The first part joined is data/: the word itself, or a tuple of the module's whose first word it is (*WORDING)."""
        if isinstance(part, ast.Starred) and isinstance(part.value, ast.Name):
            return consts.get(part.value.id) == "data"
        return isinstance(part, ast.Constant) and part.value == "data"

    def bindings(nodes) -> list[tuple[str, ast.AST]]:
        """(name, value) for each name bound among nodes: an assignment, an annotated one, a parameter with its default."""
        out = []
        for n in nodes:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                out.append((n.targets[0].id, n.value))
            elif isinstance(n, ast.AnnAssign) and n.value is not None and isinstance(n.target, ast.Name):
                out.append((n.target.id, n.value))
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                a = n.args
                pos = a.posonlyargs + a.args
                out += [(arg.arg, d) for arg, d in zip(pos[len(pos) - len(a.defaults):], a.defaults)]
                out += [(arg.arg, d) for arg, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None]
        return out

    def scan(text: str) -> tuple[list, list]:
        """(joins onto the code's folder that are not data/, joins onto core.paths.APP): each (line, the top-level name it stands in).
        The forms read: a / b, a.joinpath(b), os.path.join(a, b) and Path(a, b), where a is __file__ taken further or a name bound to
        such a path (assigned, annotated, or a parameter's default), or core.paths.APP however it is named (from core import paths,
        import core.paths, from core.paths import APP, a name bound to it). Names bound in a function are its top-level statement's."""
        t = ast.parse(text)
        parent = {c: n for n in ast.walk(t) for c in ast.iter_child_nodes(n)}
        consts = {n.targets[0].id: n.value.elts[0].value for n in t.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                  and isinstance(n.targets[0], ast.Name) and isinstance(n.value, (ast.Tuple, ast.List)) and n.value.elts
                  and isinstance(n.value.elts[0], ast.Constant)}
        app_names = {a.asname or a.name for n in ast.walk(t) if isinstance(n, ast.ImportFrom) and n.module == "core.paths"
                     for a in n.names if a.name == "APP"}
        paths_names = {a.asname or a.name for n in ast.walk(t) if isinstance(n, ast.ImportFrom) and n.module == "core"
                       for a in n.names if a.name == "paths"} | {a.asname for n in ast.walk(t) if isinstance(n, ast.Import)
                                                                for a in n.names if a.name == "core.paths" and a.asname}
        dotted = any(a.name == "core.paths" and not a.asname for n in ast.walk(t) if isinstance(n, ast.Import) for a in n.names)

        def is_app(node, apps) -> bool:
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path" and node.args:
                node = node.args[0]
            if isinstance(node, ast.Name):
                return node.id in apps
            if not (isinstance(node, ast.Attribute) and node.attr == "APP"):
                return False
            v = node.value
            return (isinstance(v, ast.Name) and v.id in paths_names) or (dotted and isinstance(v, ast.Attribute) and v.attr == "paths"
                                                                         and isinstance(v.value, ast.Name) and v.value.id == "core")

        def bind(pairs, roots: dict, apps: set) -> tuple[dict, set]:
            """Names bound to a path made from __file__ (whether it is data/ already), and names bound to APP."""
            roots, apps = dict(roots), set(apps)
            for _ in range(4):
                for name, value in pairs:
                    if from_file(value, roots):
                        j = joined(value)
                        roots[name] = bool(j and (data_root(j[0], roots) or is_data(j[1], consts))) or data_root(value, roots)
                    elif is_app(value, apps):
                        apps.add(name)
            return roots, apps

        def in_def(n) -> bool:
            p = parent.get(n)
            while p is not None:
                if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    return True
                p = parent.get(p)
            return False
        module_roots, module_apps = bind(bindings(n for n in ast.walk(t) if isinstance(n, (ast.Assign, ast.AnnAssign)) and not in_def(n)),
                                         {}, app_names)
        onto_code, onto_app = [], []
        for top in t.body:
            where = getattr(top, "name", "") or next((x.id for x in getattr(top, "targets", []) if isinstance(x, ast.Name)), "") \
                or (top.target.id if isinstance(top, ast.AnnAssign) and isinstance(top.target, ast.Name) else "")
            roots, apps = bind(bindings(ast.walk(top)), module_roots, module_apps)
            for n in ast.walk(top):
                j = joined(n)
                if j is None or (isinstance(parent.get(n), ast.BinOp) and parent[n].left is n and isinstance(parent[n].op, ast.Div)):
                    continue                          # not a join, or the inside of a longer one
                base, first = j
                if from_file(base, roots) and not data_root(base, roots) and not is_data(first, consts):
                    onto_code.append((n.lineno, where))
                if is_app(base, apps):
                    onto_app.append((n.lineno, where))
        return onto_code, onto_app

    def from_file(node, roots) -> bool:
        """node is a path made from __file__: __file__ itself, a name bound to one, or one taken further (.parent, .parents[n],
        .resolve(), Path(...), os.path.dirname(...), a join). A file's text or a table read from it is no path."""
        if isinstance(node, ast.Name):
            return node.id == "__file__" or node.id in roots
        if isinstance(node, ast.Attribute):
            return node.attr in ("parent", "parents") and from_file(node.value, roots)
        if isinstance(node, ast.Subscript):
            return isinstance(node.value, ast.Attribute) and node.value.attr == "parents" and from_file(node.value, roots)
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == "Path") or (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute)
                                                              and f.value.attr == "path"):
                return bool(node.args) and from_file(node.args[0], roots)
            return isinstance(f, ast.Attribute) and f.attr in ("resolve", "absolute", "joinpath") and from_file(f.value, roots)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return from_file(node.left, roots)
        return False

    def data_root(node, roots) -> bool:
        return isinstance(node, ast.Name) and roots.get(node.id, False)

    planted_code = {
        "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\nLOG = ROOT / 'logs' / 'x.log'\n": True,
        "import config\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\ndef path():\n    return ROOT / getattr(config, 'X', 'logs/x')\n": True,
        "from pathlib import Path\nHERE = Path(__file__).resolve().parent\nOUT = HERE.parent / 'recordings'\n": True,
        "from pathlib import Path\ndef f():\n    return Path(__file__).resolve().parent.parent.joinpath('scratch')\n": True,
        "import os\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\nP = os.path.join(ROOT, 'logs')\n": True,
        "from pathlib import Path\nTOP = Path(__file__).resolve().parents[1]\nAT = TOP / 'runs'\n": True,
        "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\ndef f(root=ROOT):\n    return root / 'logs'\n": True,
        "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\ndef f(*, root: Path = ROOT):\n    return root.joinpath('logs')\n": True,
        "from pathlib import Path\nROOT: Path = Path(__file__).resolve().parent.parent\nX = ROOT / 'logs'\n": True,
        "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\nPARTS = ('logs', 'x.log')\nP = ROOT.joinpath(*PARTS)\n": True,
        "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\nWORDING = ('data', 'rules', 'w.yaml')\n"
        "def wording(root: Path = ROOT):\n    f = root.joinpath(*WORDING)\n    return f, root / 'data', root / 'data' / 'x'\n": False,
        "from pathlib import Path\nfrom core import yamlio\nR = yamlio.safe_load((Path(__file__).resolve().parent.parent / 'data' / 'r.yaml')"
        ".read_text())\nHALF = R['n'] / 2\n": False,
        "from pathlib import Path\nROOT = Path(__file__).resolve().parent.parent\nA = ROOT / 'data' / 'rules' / 'x.yaml'\n"
        "D = ROOT / 'data'\nB = D / 'world' / 'y.yaml'\nE = Path(__file__).resolve().parent.parent / 'data' / 'z.yaml'\n": False,
    }
    planted_app = {
        "from core import paths\nLOG = paths.APP / 'logs'\n": True,
        "from pathlib import Path\nfrom core import paths\ndef f():\n    return Path(paths.APP) / 'logs' / 'x.log'\n": True,
        "from core.paths import APP\nX = APP / 'outbox'\n": True,
        "from core import paths\nA = paths.APP\nX = A / 'logs'\n": True,
        "from pathlib import Path\nfrom core import paths\ndef f():\n    a: Path = Path(paths.APP)\n    return a / 'logs'\n": True,
        "import core.paths\nX = core.paths.APP / 'logs'\n": True,
        "import core.paths as cp\nX = cp.APP.joinpath('logs')\n": True,
        "from core import paths\ndef f(base=paths.APP):\n    return base / 'logs'\n": True,
        "from core import paths\nX = paths.written('logs/x.log')\nY = paths.BUNDLE / 'data'\nZ = paths.RUNTIME / 'cuda'\n": False,
    }
    caught = {src: bool(scan(src)[0]) == want for src, want in planted_code.items()}
    caught.update({src: bool(scan(src)[1]) == want for src, want in planted_app.items()})
    check("the source check catches each form it reads of joining onto the code's folder or APP, planted (a parameter's default, an"
          " annotated name, a tuple joined whole, an alias of APP, core.paths.APP dotted among them), and passes data/ and written()",
          all(caught.values()), [s for s, ok in caught.items() if not ok])
    files = [p for d in GAME for p in sorted((ROOT / d).rglob("*.py")) if "__pycache__" not in p.parts] + [ROOT / "main.py", ROOT / "config.py"]
    onto_code, onto_app, allowed_seen = [], [], set()
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        if rel == "core/paths.py":
            continue                                  # the one place that says where things are
        code_joins, app_joins = scan(p.read_text(encoding="utf-8"))
        for line, where in code_joins:
            if (rel, where) in ALLOWED:
                allowed_seen.add((rel, where))
            else:
                onto_code.append(f"{rel}:{line} ({where})")
        onto_app += [f"{rel}:{line} ({where})" for line, where in app_joins]
    check("in the forms the check reads, no game module joins anything but data/ onto a path made from its own __file__: no file the"
          " game writes is placed from where its code lies", not onto_code and len(files) > 100, onto_code[:8])
    check("...and every exception named is still there (a stale one is taken off the list)", allowed_seen == set(ALLOWED),
          sorted(set(ALLOWED) - allowed_seen))
    check("in the same forms, no game module but core.paths joins onto core.paths.APP: a file placed under APP by name goes through"
          " written()", not onto_app, onto_app[:8])
    check("nothing this test did wrote under the project's own logs/ or recordings/", REFUSED == [], REFUSED[:5])
    from storage import campaign
    check("...and its saves are a folder of its own, outside the project (f741)", not under(campaign.SAVES_DIR, ROOT), campaign.SAVES_DIR)
finally:
    audit._path = None
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
