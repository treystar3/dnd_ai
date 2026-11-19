"""(f731) A replay parts when the game stops short of its recording (tools/rerun.py): the end of a session is compared as every
input before it is. A game that asks for fewer lines than the recording holds, makes fewer calls than it holds, or plays a line the
recording has no turn row for, parts the replay there, named, where before the replay said "all N inputs matched" and exited 0.
Held on copies of the kept stub_short in a temp folder, each changed one way:
- one more recorded call at the end than the game makes (its last call twice in the file);
- two more recorded lines after the game's last;
- the game's loop ended after its tenth input (its eleventh pass stops before it asks, the state untouched);
- the last input's turn row taken out (a session that ended before its last line closed).
The command (rerun.py's main(), as the golden gate and the tests that take its exit status and last line read it) exits 1 and names
the call or the line; one of them is run as those tests run it, in a process of its own. Second case, the in-process caller: replay()'s
own record has `parted` set and `matched` under `of`, on the same four and on the same four made from stub_fight (a recording with
failed calls and a fight in it). The three kept recordings, untouched, still match whole, every recorded call made."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import rerun
from engine import recording
from scenes import world as world_scene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

TMP = Path(tempfile.mkdtemp(prefix="rerun_end_"))
SHOW = ("matched", "of", "calls", "recorded_calls", "parted")


def rows(path: Path) -> list:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_rows(path: Path, rs: list) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs), encoding="utf-8", newline="\n")


def copy(name: str, how: str, tag: str = "") -> Path:
    """A copy of a kept recording, changed one way: 'call' (one more call at its end than the game makes), 'lines' (two more lines
    after its last), 'row' (the last input's turn row taken out), 'loop' (as kept: the game is changed instead)."""
    folder = TMP / f"{name}_{how}{tag}"
    shutil.copytree(rerun.golden(name), folder)
    if how == "call":
        cs = recording.read_calls(folder)
        recording.calls_file(folder).unlink()                 # (f732) the changed copy's log is written plain, whichever form was kept
        (folder / "calls.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in cs + [dict(cs[-1], i=cs[-1]["i"] + 1)]),
                                            encoding="utf-8", newline="\n")
    elif how == "lines":
        ins = rows(folder / "inputs.jsonl")
        write_rows(folder / "inputs.jsonl", ins + [dict(ins[-1], i=ins[-1]["i"] + k, text="I look around.") for k in (1, 2)])
    elif how == "row":
        write_rows(folder / "turns.jsonl", rows(folder / "turns.jsonl")[:-1])
    return folder


class Stop(Exception):
    """The game's loop ends where its next pass would begin."""


@contextlib.contextmanager
def loop_ends_after(n: int):
    """The game's loop made to end after its nth input: its next pass stops before it asks (WorldScene.run returns there), nothing
    of the state touched. start_backfill is the first thing each pass of the loop does, and nothing else calls it."""
    W = world_scene.WorldScene
    real_run, real_start = W.run, W.start_backfill
    passes = {"n": 0}

    def start_backfill(self):
        passes["n"] += 1
        if passes["n"] > n:
            raise Stop
        return real_start(self)

    def run(self):
        try:
            return real_run(self)
        except Stop:
            return None
    W.run, W.start_backfill = run, start_backfill
    try:
        yield passes
    finally:
        W.run, W.start_backfill = real_run, real_start


def replayed(folder: Path) -> dict:
    """replay()'s own record, as an in-process caller reads it (its scratch logs removed)."""
    out = rerun.replay(folder)
    shutil.rmtree(out.get("logs") or TMP / "none", ignore_errors=True)
    return out


def command(folder: Path) -> tuple:
    """rerun.py's main() on this folder in this process: its exit status, its last printed line, and replay()'s record beside it."""
    kept, real = {}, rerun.replay

    def watched(*a, **k):
        kept["out"] = real(*a, **k)
        return kept["out"]
    rerun.replay = watched
    argv, sys.argv = sys.argv, ["rerun.py", str(folder)]
    said = io.StringIO()
    try:
        with contextlib.redirect_stdout(said):
            rc = rerun.main()
    finally:
        sys.argv, rerun.replay = argv, real
    out = kept.get("out") or {}
    shutil.rmtree(out.get("logs") or TMP / "none", ignore_errors=True)
    lines = [l for l in said.getvalue().splitlines() if l.strip()]
    return rc, (lines[-1] if lines else ""), out


def expected(name: str) -> dict:
    """What each change of a kept recording must part at, read from the recording: the input and the words the part names."""
    rec = rerun.load(rerun.golden(name))
    main = [r for r in rec["inputs"] if r["main"]]
    of, last = len(main), rec["calls"][-1]
    first_unmade = next(c for c in rec["calls"] if c["input"] > 10)
    left = len(rec["inputs"]) - rec["inputs"].index(main[9]) - 1          # every row after the tenth line, asked or answered
    return {
        "call": {"of": of, "at": last["input"], "names": [f"call {last['i'] + 1} (input {last['input']}", f"'{last.get('title', '')}'"]},
        "lines": {"of": of + 2, "at": of + 1, "names": [f"input {of + 1} ('I look around.')", "2 recorded line"]},
        "loop": {"of": of, "at": 11, "names": [f"input 11 ({main[10]['text']!r})", f"{left} recorded line",
                                               f"call {first_unmade['i']} (input {first_unmade['input']}"]},
        "row": {"of": of, "at": of, "names": [f"input {of} ({main[-1]['text']!r})", "no turn row"]},
    }


WHAT = {"call": "one more recorded call at the end than the game makes", "lines": "two more recorded lines after the game's last",
        "loop": "the game's loop ended after its tenth input", "row": "the last input's turn row taken out"}

try:
    # ---- the three kept recordings, untouched: every input compared, every recorded call made
    for name in ("stub_short", "stub_party", "stub_fight"):
        out = replayed(rerun.golden(name))
        check(f"the kept {name} still matches whole: every input compared, every recorded call made, every line asked",
              out["parted"] is None and out["matched"] == out["of"] and out["calls"] == out["recorded_calls"], {k: out.get(k) for k in SHOW})

    # ---- stub_short through the command: exit 1, the part named, where it said "all N inputs matched"
    want = expected("stub_short")
    for how in ("call", "lines", "loop", "row"):
        w = want[how]
        folder = copy("stub_short", how)
        with (loop_ends_after(10) if how == "loop" else contextlib.nullcontext({})) as passes:
            rc, last, out = command(folder)
        if how == "loop":
            check("(the game's loop did end after its tenth input)", passes["n"] == 11 and out.get("calls", 0) < out.get("recorded_calls", 0), passes)
        check(f"stub_short, {WHAT[how]}: the command parts (exit 1), at input {w['at']} of {w['of']}",
              rc == 1 and last.startswith(f"parted at input {w['at']} of {w['of']}:") and "inputs matched" not in last, (rc, last))
        check("...naming the call or the line it stopped short of", all(s in last for s in w["names"]), (w["names"], last))
        check("...and replay()'s own record says so to an in-process caller: parted, matched under of",
              out.get("parted") is not None and out.get("matched") == w["at"] - 1 and out["matched"] < out["of"] == w["of"],
              {k: out.get(k) for k in SHOW})

    # ---- the command as the tests that read its exit status and last line run it: a process of its own
    folder = copy("stub_short", "lines", "_child")
    run = subprocess.run([sys.executable, "tools/rerun.py", str(folder)], capture_output=True, text=True, timeout=900,
                         env={**os.environ, "TMPDIR": str(TMP), "TEMP": str(TMP), "TMP": str(TMP)})     # its scratch logs go with the copies
    said = [l for l in (run.stdout + run.stderr).splitlines() if l.strip()]
    check("...and in a process of its own, as the golden gate runs it: exit 1, the last line the part, never 'all N inputs matched'",
          run.returncode == 1 and said[-1:] != [] and said[-1].startswith(f"parted at input {want['lines']['at']} of {want['lines']['of']}:"),
          (run.returncode, said[-2:]))

    # ---- second case: the in-process caller, the same four on stub_fight (failed calls, a fight)
    want = expected("stub_fight")
    for how in ("call", "lines", "loop", "row"):
        w = want[how]
        folder = copy("stub_fight", how)
        with loop_ends_after(10) if how == "loop" else contextlib.nullcontext():
            out = replayed(folder)
        why = (out.get("parted") or {}).get("why", "")
        check(f"stub_fight, {WHAT[how]}: replay() parts at input {w['at']}, matched under of",
              out.get("parted") is not None and out["parted"]["input"] == w["at"] and out["matched"] == w["at"] - 1 and out["of"] == w["of"],
              {k: out.get(k) for k in SHOW})
        check("...naming the call or the line it stopped short of", all(s in why for s in w["names"]), (w["names"], why))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
