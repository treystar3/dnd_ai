"""(f364) The content guard: the line the game draws around what the model may write, checked on every answer at the gateway.

Why: a store's rules for live-generated content ask what keeps illegal or harmful content off the page, and for a way to flag what gets
through. The game's answer is this check (data/rules/guard.yaml, whole words and phrases by category) on every text field of every answer
before it is accepted, the written fallback when a rewrite does not clear it, a row in the refusals log for each hit, and the #report
command (scenes/audit_actions.py) that saves what the player saw with the calls behind it. The player's own words are not judged here;
the tasks that only read them are skipped."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
G = yaml.safe_load((ROOT / "data" / "rules" / "guard.yaml").read_text(encoding="utf-8"))


def _pattern(words: list) -> re.Pattern:
    parts = []
    for w in words:
        w = str(w).strip().lower()
        if not w:
            continue
        core = re.escape(w).replace(r"\ ", r"\s+")
        parts.append(rf"\b{core}" + (r"\w*" if not " " in w and len(w) >= 8 else r"\b"))   # a long stem ('masturbat') matches its forms
    return re.compile("|".join(parts) or r"(?!x)x", re.I)


PATTERNS: dict[str, re.Pattern] = {cat: _pattern((spec or {}).get("words") or []) for cat, spec in (G.get("categories") or {}).items()}
ALLOWED: dict[str, re.Pattern | None] = {cat: (re.compile("|".join(f"(?:{a})" for a in (spec or {}).get("allow") or []), re.I) if (spec or {}).get("allow") else None)
                                        for cat, spec in (G.get("categories") or {}).items()}   # (f370) a hit that begins an allowed phrase is the innocent sense
SKIP = set(G.get("skip_tasks") or [])


def strings_of(value) -> list[str]:
    """Every string inside an answer: a pydantic model, a dict, a list, or a string."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings_of(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in strings_of(v)]
    return []


def check(texts) -> tuple[str, str]:
    """(category, the words matched) for the first hit in these texts, or ('', '')."""
    for t in texts:
        if not t:
            continue
        for cat, pat in PATTERNS.items():
            allow = ALLOWED.get(cat)
            for m in pat.finditer(t):
                if allow is not None and allow.match(t, m.start()):
                    continue
                return cat, m.group(0)
    return "", ""


def reason(category: str) -> str:
    spec = (G.get("categories") or {}).get(category) or {}
    return spec.get("reason") or "that is outside what the game writes: find other words"


def guarded(task: str) -> bool:
    return task not in SKIP


def problems() -> list[str]:
    bad = []
    cats = G.get("categories") or {}
    if not cats:
        bad.append("guard.yaml: needs at least one category")
    for cat, spec in cats.items():
        if not (spec or {}).get("words"):
            bad.append(f"guard.yaml {cat}: needs words")
        if not (spec or {}).get("reason"):
            bad.append(f"guard.yaml {cat}: needs a reason to send back to the model")
    return bad
