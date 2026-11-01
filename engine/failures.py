"""(f437) What the player reads when the game could not take a turn. When a model call the turn needs fails every try, the turn is rolled
back (scenes/world.py turn, and a pane button's command): nothing happened, nothing is lost, and the player is told so in the narrator's
own words, never as machinery ("the model couldn't produce a usable answer") and never in the same words twice running. The lines are in
data/rules/failures.yaml. This is where the rebuild's Stage 3 puts its "presentation that survives failure": the plain lines that tell an
outcome that stood when its passage could not be written."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml
from engine import streams

F = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "failures.yaml").read_text(encoding="utf-8"))
MACHINERY = re.compile(r"\b(model|llm|json|error|errors|answer|server|ollama|crash|failed|failure)\b", re.I)
_last: dict[str, str] = {}


def not_taken(rng: random.Random | None = None) -> str:
    """A line for a turn the game could not take: never the one shown last."""
    lines = F["turn_not_taken"]
    pick = [l for l in lines if l != _last.get("turn_not_taken")] or lines
    line = (rng or streams.get("scene")).choice(pick)
    _last["turn_not_taken"] = line
    return line


def lines() -> list[str]:
    """Every line a turn not taken can show (the night tool counts them as failed turns)."""
    return list(F["turn_not_taken"])


def problems(data: dict | None = None) -> list[str]:
    """For engine/data_check.py: enough lines, all different, none of them machinery."""
    d = F if data is None else data
    got = d.get("turn_not_taken") if isinstance(d, dict) else None
    if not isinstance(got, list) or len(got) < 6 or not all(isinstance(l, str) and l.strip() for l in got):
        return ["failures.yaml turn_not_taken: needs at least 6 lines of text"]
    bad = []
    if len({l.strip().lower() for l in got}) != len(got):
        bad.append("failures.yaml turn_not_taken: a line is there twice")
    for l in got:
        hit = MACHINERY.search(l)
        if hit:
            bad.append(f"failures.yaml turn_not_taken: '{l}' speaks of the machinery ('{hit.group(0)}'); say it in the world's words")
    return bad
