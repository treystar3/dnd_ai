"""Scores how well each stat and trigger suits a class, using the suits tags in data/rules/.

The best fits are given to the passive generator as guidance. Nothing is forbidden:
an unusual concept can still get an unusual passive, it just isn't the default.
"""

import re

from core.rules import MECHANICS, STATS, TRIGGERS, Suits
from llm.contracts import ClassInterpretation

ARCHETYPE_MATCH = 2
THEME_MATCH = 3
FIT_THRESHOLD = 2
EXCLUDED = -10


def _class_text(interp: ClassInterpretation) -> str:
    parts = [interp.custom_class, interp.combat_identity, " ".join(interp.themes), interp.summary]
    return " ".join(parts).lower()


def _base_score(suits: Suits, interp: ClassInterpretation, text: str) -> int:
    score = 0
    if interp.archetype.value in suits.archetypes:
        score += ARCHETYPE_MATCH
    matches = sum(1 for k in suits.themes if re.search(rf"\b{re.escape(k.lower())}", text))
    score += THEME_MATCH * min(3, matches)
    return score


def stat_scores(interp: ClassInterpretation) -> dict[str, int]:
    text = _class_text(interp)
    scores = {}
    for s in STATS.values():
        score = _base_score(s.suits, interp, text)
        if s.category == "companion":
            score += 4 if (interp.uses_companions or getattr(interp, "summoner", False)) else EXCLUDED
        if interp.focus == "social" and s.category in ("social", "knowledge"):
            score += 2
        if interp.focus == "combat" and s.category == "combat":
            score += 1
        scores[s.id] = score
    return scores


def trigger_scores(interp: ClassInterpretation) -> dict[str, int]:
    text = _class_text(interp)
    scores = {}
    for t in TRIGGERS.values():
        score = _base_score(t.suits, interp, text)
        if t.id == "with_companion_present":
            score += 4 if (interp.uses_companions or getattr(interp, "summoner", False)) else EXCLUDED
        if interp.focus == "social" and t.noncombat:
            score += 2
        scores[t.id] = score
    return scores


def best_fits(scores: dict[str, int], limit: int = 8) -> list[str]:
    ranked = sorted((s for s in scores.items() if s[1] >= FIT_THRESHOLD), key=lambda x: -x[1])
    return [name for name, _ in ranked[:limit]]


def excluded(scores: dict[str, int]) -> list[str]:
    return [name for name, score in scores.items() if score <= EXCLUDED + 5]


def mechanic_scores(interp: ClassInterpretation) -> dict[str, int]:
    text = _class_text(interp)
    scores = {}
    for m in MECHANICS.values():
        score = _base_score(m.suits, interp, text)
        if m.companion_only:
            score += 4 if (interp.uses_companions or getattr(interp, "summoner", False)) else EXCLUDED
        if interp.focus == "social" and m.kind == "world":
            score += 2
        scores[m.id] = score
    return scores

