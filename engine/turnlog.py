"""The turn log: one row for every line the player typed, whoever handled it, and a summary of the session at the end.

A typed line is read by the model (the interpreter) or claimed before it reaches the model by one of the intercepts in
scenes/world.py handle(): the mentor stepping in, a companion addressed by name, a camp, a trial, a way out of town. Only the
interpreted lines used to be logged (by the audit, logs/turns.jsonl), so a line an intercept took left no trace. Now every typed
line is one row here with `handled_by` naming what took it, and an interpreted line carries every interpreter call made for it in
full (the request as the model saw it, the catalogues shown and left out, the plan read back), keyed by `turn` so it joins
logs/llm_calls.jsonl and the audit file. tools/replay.py --promote turns such a row into a replay case without loss.

The session summary (logs/sessions.jsonl, one line per session): how many lines each handler took, every model task's calls,
failures and attempts (llm/gateway.py TALLY), the written fallbacks used, and the refusals by kind. A change to the interpreter is
measured against these over real play, not against a feeling.

Both files are trimmed like the others (config.LOG_MAX_MB, LOG_KEEP_ENTRIES), so a long campaign never grows them without bound.

(f385) A row is written when its turn ends, with what the turn showed the player (`shown`: every passage, speech, note, ledger line
and question asked back, in order, with its kind), when the turn began (`started`) and how long it took (`turn_seconds`), and any
passage written twice (`rewrites`: why, and whether the draft or the rewrite was shown). Without them the third playthrough's logs
could not say what the player saw: notes, coins and refusals were missing, and a turn with two narration calls did not say which one
was printed. A # command or pane button that changed something (the clock, the place, the coin) or told the player anything in the
story's column is a row too, `handled_by: "command"`; a pane that only redraws a view is not: a pinned pane re-runs its command after
every turn, and those are not things the player did."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import config

COUNTS: dict[str, int] = {}          # handled_by -> lines this session
_writes = 0
_lock = threading.Lock()
_open: dict | None = None            # (f385) the turn being played: its rows wait here for what it showed
SHOWN = 0                            # (f385) things shown since the start: a turn that moved it not at all said nothing
SHOWN_KINDS = {"narrate": "narration", "say": "speech", "npc_says": "speech", "dialogue": "speech", "note": "note", "wait": "wait",
               "ledger": "ledger", "combat_numbers": "numbers"}


def enabled() -> bool:
    return bool(getattr(config, "TURN_LOG", True))


def path() -> Path:
    return Path(getattr(config, "TURN_LOG_PATH", "logs/turns.jsonl"))


def record(turn: int, text: str, handled_by: str, **fields) -> None:
    """One typed line: `handled_by` is the intercept that took it ("errand", "mentor", "trial", "camp", "exit"...), "combat" in a
    fight, or "interpret" when the model read it (then the audit's fields and every interpreter call ride along)."""
    COUNTS[handled_by] = COUNTS.get(handled_by, 0) + 1
    if not enabled():
        return
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "turn": turn, "handled_by": handled_by, "text": text, **fields}
    if _open is not None:
        _open["rows"].append(entry)
        return
    _write(entry)


def _write(entry: dict) -> None:
    global _writes
    try:
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            _writes += 1
            if _writes % 50 == 1:
                _trim(p)
    except OSError:
        pass


def begin(console=None) -> None:
    """(f385) A turn starts: rows wait for its end, and what the console prints is kept for them."""
    global _open
    if console is not None:
        tap(console)
    _open = {"started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "t0": time.perf_counter(), "rows": [], "shown": [],
             "rewrites": []}


def end(rolled_back: bool = False, command: dict | None = None, failure: str = "", crash: str = "") -> None:
    """(f385) The turn is over: its rows are written, the last carrying what was shown, when it began and how long it took. `command`
    is a # command's row (its text, and whether it changed anything), written only when it did something or told the player
    something in the story's column. (f437) `failure`: why a turn rolled back, when a model call it needed failed; the row says the model
    failed, which is never a refusal of what the player typed. (f449) `crash`: the turn rolled back because the game itself raised; the
    row says so (crashed), apart from the model's failures, and logs/crash.log holds the traceback."""
    global _open
    t, _open = _open, None
    if t is None or not enabled():
        return
    rows = t["rows"]
    if command is not None:
        told = any(s["kind"] != "note" or not command.get("view") for s in t["shown"])     # a view's own listing is not a thing done
        if not (command.get("changed") or told or crash):                                  # (f449) a fault always leaves its row
            return
        COUNTS["command"] = COUNTS.get("command", 0) + 1
        rows = rows or [{"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "turn": command.get("turn"),
                         "handled_by": "command", "text": command.get("text", ""), "changed": command.get("changed", [])}]
    if not rows:
        if not t["shown"]:
            return
        rows = [{"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "handled_by": "unrecorded", "text": ""}]
    rows[-1].update(started=t["started"], turn_seconds=round(time.perf_counter() - t["t0"], 2), shown=t["shown"])
    if t["rewrites"]:
        rows[-1]["rewrites"] = t["rewrites"]
    if rolled_back:
        rows[-1]["rolled_back"] = True
        if failure:
            rows[-1]["model_failed"] = failure[:200]
        if crash:
            rows[-1]["crashed"] = crash[:200]                  # (f449) the game's own fault, not the model's
    for r in rows:
        _write(r)


def shown(kind: str, text: str) -> None:
    """(f385) Something the player was shown this turn."""
    global SHOWN
    if not (text or "").strip():
        return
    SHOWN += 1
    if _open is not None:
        _open["shown"].append({"kind": kind, "text": text.strip()})


def rewrite(task: str, why: list[str], kept: str) -> None:
    """(f385) A passage was written twice: why, and which one the player read ('draft' or 'rewrite')."""
    if _open is not None:
        _open["rewrites"].append({"task": task, "why": why, "shown": kept})


def tap(console) -> None:
    """(f385) Wraps the console's story-column functions so what they print is kept for the turn's row. Whatever is installed now is
    wrapped (the terminal's, a test's, a night run's), and only once."""
    for name, kind in SHOWN_KINDS.items():
        fn = getattr(console, name, None)
        if fn is None or getattr(fn, "_turnlog", False):
            continue
        def wrapped(*a, _fn=fn, _name=name, _kind=kind, **k):
            shown(_kind, _shown_text(_name, a, k))
            return _fn(*a, **k)
        wrapped._turnlog = True
        setattr(console, name, wrapped)


def _shown_text(name: str, a: tuple, k: dict) -> str:
    """The words as the player read them, with the speaker's name."""
    if name == "say":
        text, who = (a + ("", ""))[:2]
        return f"{k.get('speaker', who)}: {k.get('text', text)}" if (k.get("speaker", who)) else str(k.get("text", text))
    if name == "npc_says":
        label, speech, gesture = (a + ("", "", ""))[:3]
        return f'({label} {gesture})\n{label}: "{speech}"' if gesture else f'{label}: "{speech}"'
    if name == "dialogue":
        before, speaker, speech, after = (a + ("", "", "", ""))[:4]
        return "\n".join(x for x in (before, f'{speaker}: "{speech}"', after) if x and x.strip())
    if name == "combat_numbers":
        return "\n".join(str(l) for l in (a[0] if a else k.get("lines", [])))
    return str(a[0] if a else next(iter(k.values()), ""))


def _trim(p: Path) -> None:
    try:
        from llm.gateway import trim_log
        trim_log(p)
    except Exception:
        pass


def session_stats() -> dict:
    """What this session's lines went to, and how the model did on each task."""
    tasks: dict[str, dict] = {}
    fallbacks = 0
    try:
        from llm import gateway
        tasks = {t: dict(v) for t, v in gateway.TALLY.items()}
        fallbacks = len(gateway.FALLBACKS)
    except Exception:
        pass
    kinds: dict[str, int] = {}
    try:
        from engine import refusals
        for r in refusals.SESSION:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    except Exception:
        pass
    return {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "lines": dict(COUNTS), "tasks": tasks,
            "fallbacks": fallbacks, "refusals": kinds}


def write_session_stats() -> None:
    """One line for the session in logs/sessions.jsonl; nothing when nothing was typed (a tool run, a session that never started)."""
    if not COUNTS:
        return
    try:
        p = Path(getattr(config, "SESSION_STATS_PATH", "logs/sessions.jsonl"))
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(session_stats(), ensure_ascii=False) + "\n")
        _trim(p)
    except OSError:
        pass
