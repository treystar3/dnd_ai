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
Pane buttons and # commands are not rows: a pinned pane re-runs its command after every turn, and those are not lines the player
typed."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import config

COUNTS: dict[str, int] = {}          # handled_by -> lines this session
_writes = 0
_lock = threading.Lock()


def enabled() -> bool:
    return bool(getattr(config, "TURN_LOG", True))


def path() -> Path:
    return Path(getattr(config, "TURN_LOG_PATH", "logs/turns.jsonl"))


def record(turn: int, text: str, handled_by: str, **fields) -> None:
    """One typed line: `handled_by` is the intercept that took it ("errand", "mentor", "trial", "camp", "exit"...), "combat" in a
    fight, or "interpret" when the model read it (then the audit's fields and every interpreter call ride along)."""
    global _writes
    COUNTS[handled_by] = COUNTS.get(handled_by, 0) + 1
    if not enabled():
        return
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "turn": turn, "handled_by": handled_by, "text": text, **fields}
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
