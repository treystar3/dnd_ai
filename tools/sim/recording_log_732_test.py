"""(f732) A kept recording's call log is plain text, read through one reader, so a re-bless adds a delta to git and not a new blob
(found by the audit, unneeded-files-4: the three kept logs were gzip with the time of writing in its header, which git cannot delta,
and their 419 versions were a third of the repository's history). engine/recording.py reads a recording's log in either form
(calls.jsonl when it is there, else calls.jsonl.gz, from a folder or a zip's member) and the one Recorder writes it in the form its
place keeps: plain under data/replay (a kept recording, and the folder a re-bless renames into place), anywhere else gzipped with no
time in its header, so the same rows give the same bytes.
- A made-up recording whose log is plain is read by rerun.load, replays as the same recording gzipped does, and the startup check
  counts it kept; the three kept recordings hold their log plain, every row ending in a plain newline, and no gzip beside it.
- The same rows written twice through the Recorder, a second apart, give the same bytes; where it keeps, it writes plain.
- No tracked .py outside engine/recording.py reads a recording's log by its file name (the search is tried on planted source first).
Second case, a played recording outside data/replay, still gzipped: tools/latency.py, tools/card_profile.py and tools/think_ab.py
(from a folder, a folder of them and a zip) read it as before, and read its plain copy the same.
Run: python tools/sim/recording_log_732_test.py"""
import ast
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
simlib.quiet_console()
import card_profile
import latency
import rerun
import think_ab
from engine import data_check, recording

bad: list[str] = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  {str(detail)[:900]}"), file=sys.__stdout__)
    if not ok:
        bad.append(name)


def attempt(fn, *a, **k):
    """What fn gives, or the error it raised (a reader that cannot take the file is a failed check, not a crashed test)."""
    try:
        return fn(*a, **k)
    except Exception as e:
        return e


def strip(rows) -> list:
    return [{k: v for k, v in r.items() if k != "_from"} for r in rows]


TMP = Path(tempfile.mkdtemp(prefix="recording_log_"))
ENV = {**os.environ, "MERAVIA_NO_SERVER": "1"}
SESSIONS = ROOT / "data" / "replay" / "sessions"
KEPT_NAMES = ("stub_short", "stub_party", "stub_fight")

# ---- a made-up recording, played (gzipped, outside data/replay), and its plain copy, as a kept one holds it
played_root, plain_root = TMP / "played", TMP / "kept"
played, plain = played_root / "made_up", plain_root / "made_up"
r = subprocess.run([sys.executable, "tools/rerun.py", "--make", str(played), "--inputs", "8"], capture_output=True, text=True,
                   timeout=900, env=ENV)
check("(a made-up recording is made under the stub)", r.returncode == 0 and (played / "meta.json").exists(), (r.stdout + r.stderr)[-600:])
gz_bytes = (played / "calls.jsonl.gz").read_bytes() if (played / "calls.jsonl.gz").exists() else b""
check("a played recording outside data/replay keeps its log gzipped", gz_bytes[:2] == b"\x1f\x8b" and not (played / "calls.jsonl").exists(),
      sorted(p.name for p in played.iterdir()) if played.exists() else "")
text = gzip.decompress(gz_bytes).decode("utf-8") if gz_bytes else ""
ROWS = [json.loads(l) for l in text.split("\n") if l.strip()]
shutil.copytree(played, plain)
(plain / "calls.jsonl.gz").unlink()
(plain / "calls.jsonl").write_text(text, encoding="utf-8", newline="\n")
check("(the made-up recording made model calls, chats and their requests among them)",
      len(ROWS) > 10 and any(c.get("kind") == "chat" and c.get("request") for c in ROWS), len(ROWS))

# ---- 1. the one reader
read_calls, calls_file = getattr(recording, "read_calls", None), getattr(recording, "calls_file", None)
check("engine/recording.py has the one reader of a recording's log, and the question whether a recording has one",
      callable(read_calls) and callable(calls_file), [n for n in ("read_calls", "calls_file") if not hasattr(recording, n)])
if callable(read_calls) and callable(calls_file):
    check("...it reads a log in either form, the same rows", read_calls(played) == ROWS and read_calls(plain) == ROWS)
    check("...it names the log a recording has, plain before gzipped, and none for a folder without one",
          calls_file(played) == played / "calls.jsonl.gz" and calls_file(plain) == plain / "calls.jsonl" and calls_file(TMP) is None,
          (calls_file(played), calls_file(plain), calls_file(TMP)))
    both = TMP / "both"
    both.mkdir()
    (both / "calls.jsonl").write_text(text, encoding="utf-8", newline="\n")
    with gzip.open(both / "calls.jsonl.gz", "wt", encoding="utf-8", newline="\n") as f:
        f.write(text.split("\n", 1)[0] + "\n")
    check("...the plain one when a folder holds both", read_calls(both) == ROWS)
    z = TMP / "member.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("night/made_up/calls.jsonl.gz", gz_bytes)
        zf.writestr("night/kept/calls.jsonl", text)
    check("...and a log inside a zip, by its member's name, in either form",
          attempt(read_calls, z, "night/made_up/calls.jsonl.gz") == ROWS and attempt(read_calls, z, "night/kept/calls.jsonl") == ROWS)

loaded = attempt(rerun.load, plain)
check("a recording whose log is plain calls.jsonl is read by rerun.load, the same calls", isinstance(loaded, dict) and loaded["calls"] == ROWS,
      repr(loaded)[:300])


def replayed(folder: Path) -> tuple[int, str]:
    out = subprocess.run([sys.executable, "tools/rerun.py", str(folder)], capture_output=True, text=True, timeout=900, env=ENV)
    return out.returncode, ([l for l in (out.stdout + out.stderr).splitlines() if l.strip()][-1:] or [""])[0]


gz_run, plain_run = replayed(played), replayed(plain)
check("the made-up recording replays whole from its gzipped log", gz_run[0] == 0 and gz_run[1].startswith("all "), gz_run)
check("...and the same from its plain one: every input matched, every call served", plain_run == gz_run, (plain_run, gz_run))

# ---- the startup check counts a kept recording kept, in either form
check_root = TMP / "root"
(check_root / "data" / "rules").mkdir(parents=True)
shutil.copy(ROOT / "data" / "rules" / "budget.yaml", check_root / "data" / "rules" / "budget.yaml")
shutil.copytree(plain, check_root / "data" / "replay" / "sessions" / "made_up")
shutil.copytree(played, check_root / "data" / "replay" / "sessions" / "played")
(check_root / "data" / "replay" / "sessions" / "gone").mkdir()
real_root = data_check.ROOT
data_check.ROOT = check_root
try:
    said = attempt(data_check.fights_problems, {"fight_tasks": ["combat_narrate"], "limit_seconds": 60.0,
                                                 "goldens": {"made_up": {}, "played": {}, "gone": {}}})
finally:
    data_check.ROOT = real_root
check("data_check counts a kept recording whose log is plain as kept, and one gzipped too; only a folder with no log is reported",
      said == ["bundle_e_fights.yaml goldens.gone: no such recording is kept"], said)

# ---- the three kept recordings hold their log plain
for name in KEPT_NAMES:
    folder = SESSIONS / name
    body = (folder / "calls.jsonl").read_bytes() if (folder / "calls.jsonl").exists() else b""
    check(f"{name} keeps its log as plain calls.jsonl, every row ending in a plain newline, and no gzip beside it",
          body and not (folder / "calls.jsonl.gz").exists() and b"\r" not in body and body.endswith(b"\n")
          and all(json.loads(l) for l in body.decode("utf-8").split("\n") if l.strip()),
          sorted(p.name for p in folder.iterdir()))

# ---- 2. the one writer: the Recorder
g = simlib.campaign("recording_log_732")


def recorded(folder: Path) -> Path:
    """The made-up rows written through the Recorder's writer into folder, as a session writes them, and the recorder closed."""
    rec = recording.Recorder(g.store, folder=folder)
    for row in ROWS:
        rec._write_call(row)
    rec.close()
    return folder


one = recorded(TMP / "written" / "one")
time.sleep(1.2)                                              # a second apart: a header that holds the time would differ
two = recorded(TMP / "written" / "two")
first, second = ((f / "calls.jsonl.gz").read_bytes() if (f / "calls.jsonl.gz").exists() else b"" for f in (one, two))
check("outside data/replay the Recorder writes its log gzipped", first[:2] == b"\x1f\x8b" and not (one / "calls.jsonl").exists(),
      sorted(p.name for p in one.iterdir()))
check("...the same rows, written a second apart, give the same bytes (no time in the header)", first and first == second,
      (first[4:8].hex(), second[4:8].hex()))
check("...and the rows read back are the rows written", first and gzip.decompress(first).decode("utf-8") == text)

kept_at = getattr(recording, "KEPT", None)
check("where a recording is kept is data/replay, which holds the kept recordings and the folder a re-bless renames into place",
      kept_at == ROOT / "data" / "replay" and rerun.golden("stub_short").resolve().is_relative_to(kept_at)
      and rerun.golden("stub_short").with_name("stub_short_new").resolve().is_relative_to(kept_at), kept_at)
stand = TMP / "replay"                                       # a stand-in for data/replay, so the test writes nothing into data/
recording.KEPT = stand
try:
    keep = recorded(stand / "sessions" / "made_up_new")
finally:
    if kept_at is None:
        del recording.KEPT
    else:
        recording.KEPT = kept_at
body = (keep / "calls.jsonl").read_bytes() if (keep / "calls.jsonl").exists() else b""
check("where it keeps, the Recorder writes its log as plain calls.jsonl with plain newlines, and no gzip",
      body.decode("utf-8") == text and not (keep / "calls.jsonl.gz").exists(), sorted(p.name for p in keep.iterdir()))
g.session.close()
shutil.rmtree("saves/recording_log_732", ignore_errors=True)

# ---- 3. no file but the reader opens a log by its name
LOGS = ("calls.jsonl", "calls.jsonl.gz")
WRITES = ("w", "a", "x")


def log_name(node) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.replace("\\", "/").rsplit("/", 1)[-1] in LOGS


def mode_of(call: ast.Call, at: int) -> str:
    m = call.args[at] if len(call.args) > at else next((k.value for k in call.keywords if k.arg == "mode"), None)
    return m.value if isinstance(m, ast.Constant) and isinstance(m.value, str) else ""


def written(call: ast.Call, inside) -> bool:
    """Whether the log's name, in the part `inside` of this call, is the file the call writes."""
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
    if isinstance(f, ast.Attribute) and inside is f:                             # path.write_text(...), path.open("w")
        return name in ("write_text", "write_bytes") or (name == "open" and mode_of(call, 0).startswith(WRITES))
    if name in ("open", "GzipFile") and call.args and inside is call.args[0]:     # open(path, "w"), gzip.open(path, "wt")
        return mode_of(call, 1).startswith(WRITES)
    return False


def game_log(tree) -> bool:
    """The file makes calls.jsonl the game's own call log (config.LOG_PATH): there that name is no recording's."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t for tg in node.targets for t in (tg.elts if isinstance(tg, ast.Tuple) else [tg])]
            if any(isinstance(t, ast.Attribute) and t.attr == "LOG_PATH" for t in targets) and any(log_name(c) for c in ast.walk(node.value)):
                return True
    return False


def readers(src: str) -> list[int]:
    """The lines where a recording's log is reached by its file name for anything but writing it."""
    tree = ast.parse(src)
    parent = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    own = game_log(tree)
    out = []
    for node in ast.walk(tree):
        if not log_name(node) or (own and node.value.endswith("calls.jsonl")):
            continue
        child, up = node, parent.get(node)
        while up is not None and not isinstance(up, ast.stmt):
            if isinstance(up, ast.Call) and written(up, child):
                break
            child, up = up, parent.get(up)
        else:
            out.append(node.lineno)
    return out


CAUGHT = {
    "a gzipped log read": 'with gzip.open(f / "calls.jsonl.gz", "rt", encoding="utf-8") as h:\n    rows = list(h)\n',
    "a plain log read": 'rows = (f / "calls.jsonl").read_text(encoding="utf-8")\n',
    "opened with no mode": 'h = open(f / "calls.jsonl", encoding="utf-8")\n',
    "a glob of them": 'logs = sorted(root.glob("*/calls.jsonl.gz"))\n',
    "asked whether it is there": 'ok = (f / "calls.jsonl.gz").exists()\n',
    "a path held for later": 'gz = f / "calls.jsonl.gz"\n',
    "a zip's member by its name": 'names = [n for n in z.namelist() if n.endswith("calls.jsonl")]\n',
    "a path in an f-string": 'p = f"{root}/calls.jsonl.gz"\n',
    "a kept one spelled whole": 'rows = gzip.open("data/replay/sessions/stub_short/calls.jsonl.gz", "rt")\n',
}
PASSED = {
    "a gzipped log written": 'with gzip.open(f / "calls.jsonl.gz", "wt", encoding="utf-8") as h:\n    h.write(x)\n',
    "a plain log written": '(f / "calls.jsonl").write_text(x, encoding="utf-8")\n',
    "bytes written": '(f / "calls.jsonl.gz").write_bytes(b"")\n',
    "opened to write": 'h = (f / "calls.jsonl").open("w", encoding="utf-8")\n',
    "the game's own log": 'config.LOG_PATH = str(t / "calls.jsonl")\nrows = latency.load(t / "calls.jsonl")\n',
    "another log": 'rows = latency.load(out / "llm_calls.jsonl")\n',
    "a sentence that names it": '"""The rows of one calls.jsonl.gz, as far as it can be read."""\n',
}
check("the search finds every way a log is reached by its name", all(readers(s) for s in CAUGHT.values()),
      [k for k, s in CAUGHT.items() if not readers(s)])
check("...and passes what is not one", not any(readers(s) for s in PASSED.values()), [k for k, s in PASSED.items() if readers(s)])
ME = Path(__file__).name
files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True).stdout.split()
by_name = {}
for f in files:
    p = Path(f)
    if p.name == ME or p.as_posix() == "engine/recording.py" or not p.exists():
        continue
    try:
        lines = readers(p.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        continue
    if lines:
        by_name[p.as_posix()] = lines
check(f"no tracked .py outside engine/recording.py reads a recording's log by its file name (of {len(files)} read)", len(files) > 500 and not by_name,
      sorted(by_name.items()))

# ---- second case: a played recording, still gzipped, read by the tools as before, and its plain copy the same
asked = {c["i"]: c["request"] for c in ROWS if c.get("request")}
m_gz, m_plain = attempt(card_profile.measure, played), attempt(card_profile.measure, plain)
check("card_profile reads a played recording, gzipped: its calls, the requests it prices a re-timed one by, and its measure",
      attempt(card_profile.calls_of, played) == ROWS and attempt(card_profile.requests_of, played) == asked
      and isinstance(m_gz, dict) and m_gz.get("calls") == len(ROWS), repr(m_gz)[:200])
check("...and a kept one's, plain, the same", attempt(card_profile.calls_of, plain) == ROWS
      and attempt(card_profile.requests_of, plain) == asked and m_plain == m_gz, repr(m_plain)[:200])
over_gz, over_plain = attempt(latency.over_limit, played_root, 0.0), attempt(latency.over_limit, plain_root, 0.0)
check("latency finds a folder of played recordings, gzipped, and prices each input",
      isinstance(over_gz, dict) and over_gz.get("made_up"), over_gz)
check("...and a folder of kept ones, plain, the same", over_plain == over_gz, (over_plain, over_gz))
check("think_ab reads a played recording's rows, gzipped, from its folder and from a folder of them",
      strip(think_ab.recorded_rows(played)) == ROWS and strip(think_ab.recorded_rows(played_root)) == ROWS)
check("...and a kept one's, plain, the same", strip(think_ab.recorded_rows(plain)) == ROWS and strip(think_ab.recorded_rows(plain_root)) == ROWS)
night = TMP / "night.zip"
with zipfile.ZipFile(night, "w") as zf:
    zf.writestr("night/made_up/calls.jsonl.gz", gz_bytes)
    zf.writestr("night/kept/calls.jsonl", text)
from_zip = list(think_ab.recorded_rows(night))
check("...and a played one's from a zip, gzipped inside it", strip(r for r in from_zip if "/made_up/" in r["_from"]) == ROWS,
      sorted({r["_from"] for r in from_zip}))
check("...and a kept one's from a zip, plain inside it, the same", strip(r for r in from_zip if "/kept/" in r["_from"]) == ROWS,
      sorted({r["_from"] for r in from_zip}))
cut = TMP / "cut"
cut.mkdir()
(cut / "calls.jsonl.gz").write_bytes(gz_bytes[: len(gz_bytes) * 2 // 3])          # a run killed mid-night: the file has no end
think_ab.WARNINGS.clear()
kept_rows = list(think_ab.recorded_rows(cut))
check("...and a log cut off mid-night still gives the rows before the cut, and says so",
      0 < len(kept_rows) < len(ROWS) and len(think_ab.WARNINGS) == 1 and "cut off" in think_ab.WARNINGS[0], (len(kept_rows), think_ab.WARNINGS))

shutil.rmtree(TMP, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
