"""(f779) The pulse log is trimmed as the other logs are, and the audit folder keeps a window of sessions (audit: dead-switches-3,
llm1-4, trace-threads-6, engine5-5).

Two writers had no cap. The pulse log (engine/pulselog.py) appended every pulse event for as long as the game was installed; it is now
trimmed as the turn log and the call log are, every fiftieth write, under config.LOG_MAX_MB and LOG_KEEP_ENTRIES (the night tools raise
the megabyte cap in their own process, so they still read a run's whole pulse log). The audit log (llm/audit.py) capped each session's
file at max_mb but kept every session's file; when it names a session's file it now keeps that one and the latest of the others up to
keep_sessions (data/rules/audit_log.yaml, a whole number of at least 4, held at startup), touching only files of its own dated name.
Held here, each log driven past its cap in a scratch folder with small caps:
- the pulse log stays under its cap and keeps the newest rows, and under its megabyte cap it is never trimmed;
- the audit folder keeps keep_sessions session files, the new one among them, even when the clock names it before the others; a file
  of another name is left alone; the number in the table decides; a table with no number for keep_sessions or max_mb removes nothing
  and fails no call; a session's own file still stops at max_mb; the startup check refuses numbers that cannot be;
- every other log the game writes stays under its cap: turns, sessions, refusals, crash.log, llm_calls, the recordings, the model
  server's logs (rotated, one kept) and selfcheck.log (written anew);
- every place the game's source names a log (each paths.written call, each "logs/..." string) has a case here, or is named open:
  logs/reports (a player's own #report files) has no cap, for LONG_SAVE-1's census and the owner;
- the live tools that audit their calls (tools/nightrun.py, eventrun.py) keep the audit in their run's own folder.
Run: python tools/sim/log_caps_779_test.py"""
import ast
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import simlib                                                         # (f741) a saves folder of the test's own
import yaml

import config
from core import selfcheck
from engine import crashlog, data_check, pulselog, recording, refusals, turnlog
from llm import audit, gateway, runtime

bad: list[str] = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


@contextlib.contextmanager
def replaced(obj, **values):
    was = {k: getattr(obj, k) for k in values}
    for k, v in values.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in was.items():
            setattr(obj, k, v)


def attempt(fn):
    """fn's answer, or the exception it raised."""
    try:
        return fn()
    except Exception as e:
        return e


def rows(p) -> list[str]:
    p = Path(p)
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.is_file() else []


scratch = Path(tempfile.mkdtemp(prefix="f779_")).resolve()
KEEP, TINY = 20, 0.001                    # the entries a trim keeps; a megabyte cap of about a kilobyte
CADENCE = 50                              # a writer that trims every fiftieth write holds at most KEEP + CADENCE - 1 rows
SMALL = dict(LOG_MAX_MB=TINY, LOG_KEEP_ENTRIES=KEEP)
for key in [n for n in dir(config) if n.endswith("_PATH")]:         # any write not asked for lands here, never in the project's logs/
    setattr(config, key, str(scratch / "stray" / Path(getattr(config, key)).name))
held_audit = (dict(audit.A), audit._path, audit._full, audit._count, audit.FOLDER)
try:
    # ---- the finder's case: the pulse log, the one log with no cap (engine5-5)
    pulse_path = scratch / "pulse.jsonl"
    with replaced(config, PULSE_LOG_PATH=str(pulse_path), **SMALL):
        for i in range(200):
            pulselog.mark("moment", f"pulse row {i}", i)
    got = rows(pulse_path)
    check("the pulse log written past its megabyte cap stays under it, as the turn log does: at most LOG_KEEP_ENTRIES and the rows"
          " since the last trim (engine5-5)", len(got) <= KEEP + CADENCE - 1, len(got))
    check("...and keeps the newest rows", bool(got) and json.loads(got[-1])["text"] == "pulse row 199", got[-1:])
    whole = scratch / "pulse_whole.jsonl"
    with replaced(config, PULSE_LOG_PATH=str(whole), LOG_MAX_MB=5, LOG_KEEP_ENTRIES=KEEP):
        for i in range(200):
            pulselog.mark("moment", f"pulse row {i}", i)
    check("...and under its megabyte cap it is never trimmed, so a night's report reads all of it", len(rows(whole)) == 200, len(rows(whole)))
    pulselog.clear()

    # ---- the audit folder's window (dead-switches-3, llm1-4, trace-threads-6)
    table = yaml.safe_load((ROOT / "data" / "rules" / "audit_log.yaml").read_text(encoding="utf-8"))
    keep = table.get("keep_sessions")
    check("audit_log.yaml says how many sessions the audit folder keeps: keep_sessions, a whole number of at least 4",
          isinstance(keep, int) and not isinstance(keep, bool) and keep >= 4, keep)
    window = keep if isinstance(keep, int) and keep >= 4 else 8

    def open_session(folder: Path, before: int, extra: dict | None = None) -> tuple[Path | Exception, list[str]]:
        """A folder holding `before` older sessions and three files of other names; one session opened in it. (the new file, the
        session files left)."""
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        for d in range(before):
            (folder / f"2026-10-{d + 1:02d}_120000.md").write_text("# an older session\n", encoding="utf-8")
        for name in ("notes.txt", "my_copy.md", "2026-10-01_120000.md.bak"):
            (folder / name).write_text("kept by hand\n", encoding="utf-8")
        audit.A.clear()
        audit.A.update({**held_audit[0], **(extra or {})})
        audit.FOLDER = folder
        audit._path = None
        try:
            new = audit.path()
        except Exception as e:
            new = e
        sessions = sorted(p.name for p in folder.iterdir() if p.suffix == ".md" and p.name[:4].isdigit())
        return new, sessions

    folder = scratch / "audit"
    new, sessions = open_session(folder, window + 3)
    check("a session opened in a folder past its window leaves keep_sessions session files: the oldest go (llm1-4)",
          len(sessions) == window, (len(sessions), window))
    check("...the new session's file among them, and the newest of the older ones", isinstance(new, Path) and new.name in sessions
          and f"2026-10-{window + 3:02d}_120000.md" in sessions and "2026-10-01_120000.md" not in sessions, (new, sessions))
    check("...and a file of another name in the folder is left alone", all((folder / n).is_file() for n in ("notes.txt", "my_copy.md",
                                                                                                          "2026-10-01_120000.md.bak")))
    new4, sessions4 = open_session(scratch / "audit4", 9, {"keep_sessions": 4})
    check("the number in the table decides: with keep_sessions 4, four session files stay", len(sessions4) == 4, sessions4)
    new_few, sessions_few = open_session(scratch / "audit_few", 2)
    check("...and a folder under its window loses nothing", len(sessions_few) == 3, sessions_few)

    def plant_ahead(folder: Path, extra: dict | None = None) -> Path | Exception:
        """A folder holding `window` sessions named later than now (a clock set back, a folder copied from another machine); one
        session opened in it."""
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        for d in range(window):
            (folder / f"2099-01-{d + 1:02d}_120000.md").write_text("# a session from a clock ahead\n", encoding="utf-8")
        audit.A.clear()
        audit.A.update({k: v for k, v in {**held_audit[0], **(extra or {})}.items() if v is not None})
        audit.FOLDER = folder
        audit._path, audit._full = None, False
        return attempt(audit.path)
    ahead = scratch / "audit_ahead"
    new_ahead = plant_ahead(ahead)
    with replaced(config, AUDIT_LOG=True):
        audit.record("narrate", 0, 0.1, [{"role": "system", "content": "s"}, {"role": "user", "content": "the call after a clock ahead"}],
                     '{"a": 1}', None)
    kept_ahead = sorted(p.name for p in ahead.iterdir() if p.suffix == ".md")
    check("a session named before the folder's others (a clock set back) is kept: its file survives, the call lands in it, and the"
          " folder holds keep_sessions files", isinstance(new_ahead, Path) and new_ahead.is_file()
          and "the call after a clock ahead" in new_ahead.read_text(encoding="utf-8") and len(kept_ahead) == window, (new_ahead, kept_ahead))
    for label, extra in (("no keep_sessions", {"keep_sessions": None}), ("keep_sessions 'eight'", {"keep_sessions": "eight"})):
        unnumbered = scratch / f"audit_{len(label)}"
        opened = plant_ahead(unnumbered, extra)                       # None: the key is not in the table at all
        count = sum(1 for p in unnumbered.iterdir() if p.suffix == ".md")
        check(f"a table with {label} (a tool that skips the startup check) opens its session and removes nothing, raising nothing",
              isinstance(opened, Path) and count == window + 1, (opened, count))
    audit.A.clear()
    audit.A.update({k: v for k, v in held_audit[0].items() if k != "max_mb"})
    audit.FOLDER = scratch / "audit_no_ceiling"
    audit._path, audit._full = None, False
    with replaced(config, AUDIT_LOG=True):
        recorded = attempt(lambda: audit.record("narrate", 0, 0.1, [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
                                                '{"a": 1}', None))
    no_ceiling = Path(audit._path).read_text(encoding="utf-8") if audit._path else ""
    check("...and with no max_mb the call is not failed: nothing raised, the file says it stops and holds no call",
          not isinstance(recorded, Exception) and "## #" not in no_ceiling and "reached its size limit" in no_ceiling, (recorded, no_ceiling[-200:]))
    audit.A.clear()
    audit.A.update({**held_audit[0], "max_mb": 0.0001})
    audit.FOLDER = scratch / "audit_full"
    audit._path, audit._full = None, False
    with replaced(config, AUDIT_LOG=True):
        for i in range(20):
            audit.record("narrate", 0, 0.1, [{"role": "system", "content": "s"}, {"role": "user", "content": f"line {i}"}], '{"a": 1}', None)
    full_text = Path(audit._path).read_text(encoding="utf-8") if audit._path else ""
    check("a session's own file still stops at max_mb, and says so once", full_text.count("reached its size limit") == 1
          and len(full_text.encode("utf-8")) < 4096, len(full_text))
    problems = getattr(data_check, "audit_log_problems", None)
    check("the startup check holds the audit's numbers: engine/data_check.audit_log_problems", callable(problems))
    if callable(problems):
        base = dict(held_audit[0])
        told = {repr(v): problems({**base, "keep_sessions": v}) for v in (3, "eight", 4.5, True, None)}
        told["max_mb 0"] = problems({**base, "max_mb": 0})
        check("...the real table passes", problems() == [], problems())
        check("...and a keep_sessions under 4, not a whole number or missing, or a max_mb of 0, is refused",
              all(told.values()), {k: v for k, v in told.items() if not v})
        with replaced(data_check, audit_log_problems=lambda A=None: ["f779 planted"]):
            whole_check = data_check.check()
        check("...and check() asks it at every start", "f779 planted" in whole_check, whole_check[-3:])

    # ---- the rest of the kind: every other log the game writes stays under its cap
    turns = scratch / "turns.jsonl"
    with replaced(config, TURN_LOG_PATH=str(turns), **SMALL):
        for i in range(200):
            turnlog._write({"turn": i, "text": f"turn row {i}"})
    check("the turn log stays under its cap", 0 < len(rows(turns)) <= KEEP + CADENCE - 1, len(rows(turns)))
    sessions_log = scratch / "sessions.jsonl"
    counts = dict(turnlog.COUNTS)
    turnlog.COUNTS.clear()
    turnlog.COUNTS["f779"] = 1
    try:
        with replaced(config, SESSION_STATS_PATH=str(sessions_log), **SMALL):
            for _ in range(60):
                turnlog.write_session_stats()
    finally:
        turnlog.COUNTS.clear()
        turnlog.COUNTS.update(counts)
    check("the sessions log stays under its cap", 0 < len(rows(sessions_log)) <= KEEP, len(rows(sessions_log)))
    refused = scratch / "refusals.jsonl"
    with replaced(config, REFUSALS_LOG=True, REFUSALS_LOG_PATH=str(refused), **SMALL):
        for i in range(60):
            refusals.note("refused", f"f779 refusal {i}", "a probe")
    del refusals.SESSION[-60:]
    check("the refusals log stays under its cap", 0 < len(rows(refused)) <= KEEP, len(rows(refused)))
    crash = scratch / "crash.log"
    with replaced(config, CRASH_LOG_PATH=str(crash)):
        for i in range(crashlog.KEEP + 10):
            crashlog.note("f779", f"entry {i}")
    entries = [e for e in crash.read_text(encoding="utf-8").split(crashlog.SEP) if e.strip()] if crash.is_file() else []
    check("crash.log keeps its last CRASH_KEEP entries", len(entries) == crashlog.KEEP and "entry " + str(crashlog.KEEP + 9) in entries[-1],
          len(entries))
    calls = scratch / "llm_calls.jsonl"
    with replaced(config, LOG_PATH=str(calls), **SMALL):
        for i in range(200):
            gateway._log("narrate", 0, 0.1, [{"role": "system", "content": "s"}, {"role": "user", "content": f"line {i}"}], "{}", None)
    check("the call log stays under its cap", 0 < len(rows(calls)) <= KEEP + CADENCE - 1, len(rows(calls)))
    made = scratch / "recordings"
    for i in range(config.RECORD_KEEP + 3):
        d = made / f"r{i}"
        d.mkdir(parents=True)
        (d / "meta.json").write_text("{}", encoding="utf-8")
        os.utime(d / "meta.json", (1_700_000_000 + i, 1_700_000_000 + i))
    with replaced(recording, FOLDER=made):
        recording.prune()
    left = sorted(p.name for p in made.iterdir())
    check("the recordings keep their last RECORD_KEEP", left == sorted(f"r{i}" for i in range(3, config.RECORD_KEEP + 3)), left)
    server_log = scratch / "server" / "llama-server.log"
    pump = runtime.LogPump(io.BytesIO(b"x" * (5 * 65536)), server_log, 65536, "head\n")
    pump.thread.join(10)
    kept = sorted(p.name for p in server_log.parent.iterdir())
    check("the model server's log is rotated at its cap, one before kept", kept == ["llama-server.log", "llama-server.log.1"]
          and all((server_log.parent / n).stat().st_size <= 65536 for n in kept), [(n, (server_log.parent / n).stat().st_size) for n in kept])
    own = scratch / "selfcheck.log"
    with replaced(selfcheck, parts=lambda: [("a part", lambda: [])]), contextlib.redirect_stdout(io.StringIO()):
        for _ in range(3):
            selfcheck.run(log=own)
    check("selfcheck.log is written anew each run", own.read_text(encoding="utf-8").count("its own check") == 1)

    # ---- every place the game's source names a log has a case above; the one folder with no cap is named, not capped
    CASES = {"pulse", "audit", "turns", "sessions", "refusals", "crash", "llm_calls", "recordings", "the server's logs", "selfcheck"}
    OPEN = {"reports"}                                                # (f779) LONG_SAVE-1's census and the owner: a cap, a window, or open
    SITES = {                                                         # (file, a "logs/..." it names, or the function a paths.written stands in): its case
        ("config.py", "logs/llm_calls.jsonl"): "llm_calls", ("config.py", "logs/pulse.jsonl"): "pulse",
        ("config.py", "logs/turns.jsonl"): "turns", ("config.py", "logs/sessions.jsonl"): "sessions",
        ("config.py", "logs/refusals.jsonl"): "refusals", ("config.py", "logs/crash.log"): "crash",
        ("config.py", "logs/reports"): "reports",                    # (f781) each log's path has one home, config.py
        ("engine/turnlog.py", "paths.written in path"): "turns", ("engine/turnlog.py", "paths.written in write_session_stats"): "sessions",
        ("llm/gateway.py", "paths.written in trim_log"): "llm_calls", ("llm/gateway.py", "paths.written in _log"): "llm_calls",
        ("engine/pulselog.py", "paths.written in _write"): "pulse",
        ("engine/refusals.py", "paths.written in path"): "refusals",
        ("engine/crashlog.py", "paths.written in path"): "crash",
        ("llm/audit.py", "logs/audit"): "audit", ("llm/audit.py", "paths.written in path"): "audit",
        ("engine/recording.py", "paths.written in where"): "recordings",
        ("llm/runtime.py", "paths.written in Runtime"): "the server's logs",       # llama-server.log, llama-embed.log, its crash notes
        ("core/selfcheck.py", "logs/selfcheck.log"): "selfcheck", ("core/selfcheck.py", "paths.written in log_path"): "selfcheck",
        ("scenes/audit_actions.py", "paths.written in AuditActions"): "reports",
    }

    def log_sites(text: str) -> list[str]:
        """Each paths.written(...) call, by the top-level name it stands in, and each string beginning "logs/" that is no docstring."""
        t = ast.parse(text)
        docs = {id(n.body[0].value) for n in ast.walk(t) if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        out = []
        for top in t.body:
            where = getattr(top, "name", "") or next((x.id for x in getattr(top, "targets", []) if isinstance(x, ast.Name)), "")
            for n in ast.walk(top):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "written":
                    out.append(f"paths.written in {where}")
                elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("logs/") and id(n) not in docs:
                    out.append(n.value)
        return out
    planted_sites = log_sites("from core import paths\n\n\ndef where():\n    \"\"\"logs/told.log is a docstring's.\"\"\"\n"
                              "    return paths.written('logs/new.log')\n\n\nOTHER = 'logs/other.jsonl'\n")
    check("the scan of the game's source finds a log named anew, planted: a paths.written call and a \"logs/...\" string, not a docstring",
          planted_sites == ["paths.written in where", "logs/new.log", "logs/other.jsonl"], planted_sites)
    from game_files import game_files                                 # (f788) the game's own code, one definition for every fence
    files = [ROOT / p for p in game_files()]
    found = {(p.relative_to(ROOT).as_posix(), s) for p in files for s in log_sites(p.read_text(encoding="utf-8"))}
    check("every log the game's source names (each paths.written call, each \"logs/...\" string) has a case above, or is named open;"
          " a new one fails here until it has", found <= set(SITES) and set(SITES.values()) <= CASES | OPEN, sorted(found - set(SITES)))
    check("...and every site listed is still there (a stale one is taken off the list)", set(SITES) <= found, sorted(set(SITES) - found))
    print("open logs/reports: a file for each #report, kept with no cap: for LONG_SAVE-1's census and the owner (not capped here)")

    # ---- the live tools that audit their calls keep the audit in their run's own folder, never in the window kept for play
    for tool in ("nightrun.py", "eventrun.py"):
        src = (ROOT / "tools" / tool).read_text(encoding="utf-8")
        check(f"tools/{tool} puts its audit in the run's own folder, beside its other logs", 'audit.FOLDER = out / "audit"' in src)
finally:
    audit.A.clear()
    audit.A.update(held_audit[0])
    audit._path, audit._full, audit._count, audit.FOLDER = held_audit[1], held_audit[2], held_audit[3], held_audit[4]
    shutil.rmtree(scratch, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
