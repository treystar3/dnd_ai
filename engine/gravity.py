"""How heavy a topic is, and when a topic of that weight may come up.

Everything personal a hire could talk about has a weight: light (a food they love, a song from childhood), personal (a rival, money owed, a
sibling), heavy (a death, a fear, a shame, a regret). The weight is decided where the topic is made, never guessed afterwards:

  * a detail written at hire - judged as it is written, by what it says; its subject's weight (data/rules/quirks.yaml detail_kinds)
    when that judgement is missing
  * something they said about themselves in play - the extractor's judgement, once, when it is kept (engine/canon.py)
  * something a pair went through together - the event that recorded it (scenes/banter_actions.py pair_event)

Unasked, a topic comes up by the moment (data/world/banter.yaml gravity): small talk on arrival is light, a quiet rest can turn personal,
and a heavy thing is raised only with someone trusted, not often, and most readily after a loss. Asked, a heavier topic needs to be closer in
meaning to what was said before it comes in (engine/context.py select)."""
from __future__ import annotations

import random

LEVELS = ("light", "personal", "heavy")
DEFAULT = "personal"


def _G() -> dict:
    from engine import banter
    return banter.B["banter"]["gravity"]


def level(g: str | None) -> str:
    return g if g in LEVELS else DEFAULT


def of_detail(member: dict, i: int) -> str:
    """The weight of their i-th detail: as judged when it was written, by what it says; else the weight of the subject it was written to."""
    from engine import quirks
    judged = member.get("detail_weights") or []
    if i < len(judged) and judged[i] in LEVELS:
        return judged[i]
    kinds = member.get("detail_kinds") or []
    if i >= len(kinds):
        return DEFAULT
    if i == 0 and kinds[0] == quirks.Q["detail_first"]:
        return level(quirks.Q.get("detail_first_gravity"))
    return level(quirks.Q["detail_kinds"].get(kinds[i]))


def details(member: dict) -> list[tuple[str, str]]:
    """Their details, each with its weight."""
    return [(d, of_detail(member, i)) for i, d in enumerate(member.get("details") or [])]


def moment(kind: str, after_loss: bool) -> str:
    """Which row of the unasked table this moment is."""
    if after_loss:
        return "after_loss"
    return {"rest": "rest", "travel": "arrival"}.get(kind, "ease")


def heavy_allowed(member: dict, now: int) -> bool:
    """A heavy thing may come up unasked: they trust the player enough, and have not raised one lately."""
    from engine import party as rules
    G = _G()
    names = [name for _, name in rules.P["bond"]["tiers"]]
    if names.index(rules.bond_tier(member)) < names.index(G["heavy_needs"]):
        return False
    at = member.get("heavy_at")
    return at is None or now - at >= G["heavy_gap_days"] * 1440


def unasked(moment_: str, g: str) -> float:
    return float(_G()["unasked"].get(moment_, _G()["unasked"]["ease"]).get(level(g), 0))


def choose(items: list[tuple[str, str]], moment_: str, rng: random.Random, member: dict | None = None, now: int = 0) -> tuple[str, str] | None:
    """One (topic, weight) to raise unasked, drawn by how fitting its weight is to the moment; None if nothing fits."""
    weighted = []
    for text, g in items:
        w = unasked(moment_, g)
        if g == "heavy" and member is not None and not heavy_allowed(member, now):
            w = 0
        if w > 0:
            weighted.append((w, text, g))
    if not weighted:
        return None
    _, text, g = rng.choices(weighted, weights=[w for w, _, _ in weighted])[0]
    return text, g


def share(moment_: str, g: str) -> float:
    """How a topic of this weight competes with the other things that could bring talk up now: 1 for the moment's most fitting weight."""
    row = _G()["unasked"].get(moment_, _G()["unasked"]["ease"])
    top = max(row.values()) or 1
    return unasked(moment_, g) / top


def raised(member: dict, g: str, now: int) -> None:
    if g == "heavy":
        member["heavy_at"] = now


def asked_margin(g: str) -> float:
    return float(_G()["asked_margin"].get(level(g), 0))
