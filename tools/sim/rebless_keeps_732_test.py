"""(f732) A re-bless keeps what did not change, so an unchanged recording keeps its call log and start save byte for byte: what
the clock writes (a call's wall-clock 'seconds', the start save's 'created') is no change, and a re-bless that moves nothing
moves no row in git.
Held on copies of the kept recordings in a stand-in for data/replay (the kept ones are never touched), each re-blessed by
`tools/rerun.py --golden <name> --rebless` in a process of its own:
- stub_short, the case that found it, re-blessed as it is: its call log and its start save byte for byte as they were (and its
  inputs and turns; meta.json moves only in when and on what commit it was made), and the command says so;
- the same with one call's request changed in the copy and a row planted in the copy's start save: that call's row alone is
  written anew, as the game makes it, every other row byte for byte; the start save written anew, its content the game's.
Second case of the kind, stub_fight (a script's recording, with failed calls and a fight): re-blessed as it is, byte for byte;
with one call's answer changed in the copy, that row alone is written anew, and its start save, unchanged, kept byte for byte.
Each recording put in place holds its own files and nothing beside them (reading a save to compare leaves no -wal or -shm), and
the kept recordings end as they began. And the rule on made-up rows: a row the same but for its time is the kept line; one whose
input or operation moved is written anew.
Run: python tools/sim/rebless_keeps_732_test.py"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import rerun
from engine import recording

bad: list[str] = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  {str(detail)[:900]}"))
    if not ok:
        bad.append(name)


def attempt(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        return e


TMP = Path(tempfile.mkdtemp(prefix="rebless_keeps_"))
ENV = {**os.environ, "MERAVIA_NO_SERVER": "1", "PYTHONHASHSEED": "1"}
OTHERS = ("start.db", "inputs.jsonl", "turns.jsonl")

# the re-bless in a process of its own, everything it writes in a workspace: the kept place (data/replay) stood in by one there
CHILD = r'''
import os, sys
from pathlib import Path
ROOT, name, W = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]).resolve()
os.chdir(ROOT); sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import config, rerun
for attr, fn in (("LOG_PATH", "llm_calls.jsonl"), ("TURN_LOG_PATH", "turns_log.jsonl"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                 ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl"), ("CRASH_LOG_PATH", "crash.log")):
    setattr(config, attr, str(W / fn))
config.AUDIT_LOG = config.REFUSALS_LOG = False
import storage.campaign as sc
sc.SAVES_DIR = W / "saves"
from engine import recording
recording.FOLDER = W / "recordings"
recording.KEPT = W / "replay"
rerun.ROOT = W
rerun.golden = lambda n="stub_short": W / "replay" / "sessions" / n
sys.argv = ["rerun.py", "--golden", name, "--rebless"]
sys.exit(rerun.main())
'''


def lines_of(folder: Path) -> list[str]:
    """A recording's call log as its lines, each as it is in the file."""
    path = recording.calls_file(folder)
    return path.read_text(encoding="utf-8").splitlines(keepends=True) if path else []


def without_time(line: str) -> dict:
    return {k: v for k, v in json.loads(line).items() if k != "seconds"}


def content(db: Path) -> dict:
    """A save database read whole: its version and every table's schema and rows, the campaign's clock time of making set aside."""
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)     # read as it lies: no -wal or -shm made beside it
    try:
        out = {"version": con.execute("PRAGMA user_version").fetchone()[0]}
        for name, sql in con.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall():
            rows = con.execute(f'SELECT * FROM "{name}"').fetchall()
            if name == "kv":
                rows = [(k, json.dumps({a: b for a, b in json.loads(v).items() if a != "created"}, sort_keys=True)) if k == "campaign"
                        else (k, v) for k, v in rows]
            out[name] = (sql, sorted(rows, key=repr))
    finally:
        con.close()
    return out


def moved(a: dict, b: dict) -> list:
    return [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


def rebless(name: str, tag: str, change=None) -> dict:
    """A copy of the kept recording `name`, changed by `change` if given, re-blessed in a workspace of its own: what it held before,
    what it holds after, and what the command said."""
    work = TMP / f"{name}_{tag}"
    folder = work / "replay" / "sessions" / name
    shutil.copytree(rerun.golden(name), folder)
    if change:
        change(folder)
    before = {"calls": lines_of(folder), "meta": json.loads((folder / "meta.json").read_text(encoding="utf-8")),
              "files": sorted(p.name for p in folder.iterdir()), **{f: (folder / f).read_bytes() for f in OTHERS}}
    r = subprocess.run([sys.executable, "-c", CHILD, str(ROOT), name, str(work)], cwd=ROOT, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    said = r.stdout + r.stderr
    after = {"calls": lines_of(folder), "meta": json.loads((folder / "meta.json").read_text(encoding="utf-8"))
             if (folder / "meta.json").exists() else {}, "files": sorted(p.name for p in folder.iterdir()) if folder.exists() else [],
             **{f: (folder / f).read_bytes() if (folder / f).exists() else b"" for f in OTHERS}}
    return {"rc": r.returncode, "said": said, "before": before, "after": after, "folder": folder,
            "differ": [j for j in range(max(len(before["calls"]), len(after["calls"])))
                       if j >= len(before["calls"]) or j >= len(after["calls"]) or before["calls"][j] != after["calls"][j]]}


def told(out: dict):
    """The command's own count: (rows written anew, rows) and whether it kept the start save, or None when it says nothing of it."""
    m = re.search(r"call rows written anew: (\d+) of (\d+); the start save (kept as it was|written anew)", out["said"])
    return (int(m.group(1)), int(m.group(2)), m.group(3) == "kept as it was") if m else None


def unchanged(name: str, out: dict) -> None:
    b, a = out["before"], out["after"]
    check(f"{name}: the re-bless of an unchanged copy ran and kept the copy in its place",
          out["rc"] == 0 and a["calls"] and "kept replay" in out["said"], out["said"][-700:])
    timing = [j for j in out["differ"] if j < len(a["calls"]) and j < len(b["calls"]) and without_time(a["calls"][j]) == without_time(b["calls"][j])]
    check(f"{name}: its call log is byte for byte as it was ({len(b['calls'])} rows)", a["calls"] == b["calls"],
          f"{len(out['differ'])} rows differ, {len(timing)} of them in their time alone: {out['differ'][:12]}")
    same = attempt(content, out["folder"] / "start.db")
    check(f"{name}: its start save is byte for byte as it was", a["start.db"] == b["start.db"],
          "its content the same but for the time it was made" if same == content(rerun.golden(name) / "start.db") else "its content moved")
    check(f"...and its inputs and turns, written anew, are the same bytes; meta.json moves only in when and on what commit it was made",
          a["inputs.jsonl"] == b["inputs.jsonl"] and a["turns.jsonl"] == b["turns.jsonl"]
          and [k for k in moved(a["meta"], b["meta"]) if k not in ("made", "commit")] == [], moved(a["meta"], b["meta"]))
    check(f"...and the command says so: no row written anew of {len(b['calls'])}, the start save kept", told(out) == (0, len(b["calls"]), True),
          told(out))
    check("...and the recording put in place holds its own files and nothing beside them (no -wal or -shm of a save read)",
          a["files"] == b["files"], (b["files"], a["files"]))


def change_line(folder: Path, k: int, how) -> None:
    """The copy's call row k changed by how(row), written back in its place; every other line as it was."""
    ls = lines_of(folder)
    row = json.loads(ls[k])
    how(row)
    ls[k] = json.dumps(row, ensure_ascii=False, default=str) + "\n"
    recording.calls_file(folder).write_text("".join(ls), encoding="utf-8", newline="\n")


def one_changed(name: str, out: dict, k: int, what: str, start_moved: bool) -> None:
    b, a = out["before"], out["after"]
    kept = lines_of(rerun.golden(name))
    check(f"{name}, one call's {what} changed in the copy: the re-bless ran", out["rc"] == 0 and a["calls"], out["said"][-700:])
    check(f"...that row alone is written anew (row {k}), every other row byte for byte", out["differ"] == [k],
          f"rows that differ: {out['differ'][:20]}")
    check("...and the row written is the game's: the kept recording's row, its time aside",
          k < len(a["calls"]) and without_time(a["calls"][k]) == without_time(kept[k]) and a["calls"][k] != b["calls"][k])
    if start_moved:
        planted = content(out["folder"] / "start.db") if a["start.db"] else {}
        check("...the start save, whose content moved in the copy, is written anew, its content the game's",
              a["start.db"] != b["start.db"] and planted == content(rerun.golden(name) / "start.db"), moved(planted, content(rerun.golden(name) / "start.db")))
    else:
        check("...the start save, unchanged, is kept byte for byte", a["start.db"] == b["start.db"])
    check("...and the command counts it: one row written anew", told(out) == (1, len(b["calls"]), not start_moved), told(out))
    check("...and nothing beside the recording's own files", a["files"] == b["files"], (b["files"], a["files"]))


def snapshot(name: str) -> dict:
    return {p.name: p.read_bytes() for p in rerun.golden(name).iterdir()}


KEPT_BEFORE = {name: snapshot(name) for name in ("stub_short", "stub_fight")}
try:
    # ---- the rule on made-up rows, in this process
    keep = getattr(recording, "keep_unchanged", None)
    check("engine/recording.py has the one rule a re-bless keeps by", callable(keep))
    if callable(keep):
        base = {"kind": "chat", "title": "Narration", "req": "r", "request": {"messages": []}, "answer": "{}", "finish": "stop", "usage": {}}
        old_rows = [dict(base, i=0, input=1, op="", seconds=0.004), dict(base, i=1, input=1, op="", seconds=0.002),
                    dict(base, i=2, input=2, op="a1", seconds=0.003), dict(base, i=3, input=2, op="", error={"kind": "server", "detail": "x"}, seconds=0.0)]
        new_rows = [dict(old_rows[0], seconds=0.009), dict(old_rows[1], input=2, seconds=0.001), dict(old_rows[2], op="b2", seconds=0.003),
                    dict(old_rows[3], seconds=0.7), dict(base, i=4, input=3, op="", seconds=0.002)]
        made_up = {}
        for side, rs in (("old", old_rows), ("new", new_rows)):
            f = TMP / "rule" / side
            f.mkdir(parents=True)
            (f / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs), encoding="utf-8", newline="\n")
            made_up[side] = lines_of(f)
        said = attempt(keep, TMP / "rule" / "old", TMP / "rule" / "new")
        got = lines_of(TMP / "rule" / "new")
        check("a row the same but for its time is the kept line, its time included; a failed one too",
              got[:1] == made_up["old"][:1] and got[3:4] == made_up["old"][3:4], (said, got))
        check("...a row whose input moved, or whose operation moved, is written anew though its request and answer are the same; "
              "a row the kept recording never had is written", got[1:3] == made_up["new"][1:3] and got[4:] == made_up["new"][4:]
              and len(got) == 5, got)
        check("...and it says how many it wrote anew, and that there was no start save to keep",
              isinstance(said, dict) and said.get("calls") == 3 and said.get("of") == 5 and said.get("start") != "kept", said)

    # ---- stub_short, the case that found it: re-blessed as it is
    out = rebless("stub_short", "as_is")
    unchanged("stub_short", out)

    # ---- stub_short, one request changed in the copy and a row planted in its start save
    short = lines_of(rerun.golden("stub_short"))
    k = next(j for j, l in enumerate(short) if j > len(short) // 2 and json.loads(l).get("kind") == "chat")

    def asked_otherwise(row):
        row["request"]["messages"][-1]["content"] += " And the lamp is lit."
        row["req"] = recording.request_hash(row["request"])

    def changed(folder):
        change_line(folder, k, asked_otherwise)
        con = sqlite3.connect(folder / "start.db")
        try:
            con.execute("INSERT INTO kv (key, json) VALUES ('planted_by_test', '{}')")
            con.commit()
        finally:
            con.close()
    out = rebless("stub_short", "request", changed)
    one_changed("stub_short", out, k, "request", start_moved=True)

    # ---- second case of the kind: stub_fight, a script's recording with failed calls and a fight
    fight = lines_of(rerun.golden("stub_fight"))
    check("(the kept stub_fight holds failed calls, each with its time)",
          any(json.loads(l).get("error") and "seconds" in json.loads(l) for l in fight))
    out = rebless("stub_fight", "as_is")
    unchanged("stub_fight", out)
    k = next(j for j, l in enumerate(fight) if json.loads(l).get("kind") == "chat" and not json.loads(l).get("error")
             and json.loads(l).get("title") == "CombatIntent")
    out = rebless("stub_fight", "answer", lambda folder: change_line(folder, k, lambda row: row.update(answer=row["answer"] + " ")))
    one_changed("stub_fight", out, k, "answer", start_moved=False)
    check("the kept recordings themselves are untouched: the same files, the same bytes",
          all(snapshot(name) == files for name, files in KEPT_BEFORE.items()),
          {name: sorted(set(snapshot(name)) ^ set(files)) for name, files in KEPT_BEFORE.items()})
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
