"""Refusals (f321): every time the game fails to act on a line the player typed, it is a bug with a budget. Each one is written to
logs/refusals.jsonl with the line, where it happened and why, counted for the session (#refusals), and - where the world can - turned
into a one-line question asked in character instead of a system note.

Kinds: audit_failed (the plan could not be made sense of twice), audit_unsure (f332: the plan was flagged as risky and the check itself
could not be made, so it did not run), talk_whom (words said to no one in particular with several people here), model_down (a call gave up
and a written fallback was used), clarify_failed (the question was asked, and the answer still could not be read), undone (f332: a line
named more things than the game does at once, and the rest were not done)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import config
from ui import console

ROOT = Path(__file__).resolve().parent.parent
SESSION: list[dict] = []


def note(kind: str, text: str, why: str = "", place: str = "", turn: int = -1, asked: str = "") -> None:
    row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "turn": turn, "kind": kind, "text": text, "why": why,
           "place": place, "asked": asked}
    SESSION.append(row)
    console.debug(f"refusal ({kind}): {text[:80]!r} - {why[:120]}")
    if not getattr(config, "REFUSALS_LOG", True):
        return
    try:
        path = ROOT / getattr(config, "REFUSALS_LOG_PATH", "logs/refusals.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def summary() -> str:
    if not SESSION:
        return "No refusals this session."
    lines = [f"{len(SESSION)} refusal(s) this session (logs/refusals.jsonl keeps them all):"]
    for r in SESSION[-12:]:
        lines.append(f"  turn {r['turn']}: [{r['kind']}] {r['text'][:60]!r}" + (f" - asked: {r['asked'][:60]!r}" if r["asked"] else f" - {r['why'][:80]}"))
    return "\n".join(lines)
