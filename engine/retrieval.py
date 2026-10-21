"""Finding people and places for a prompt: one place that every caller goes through, so the way it is done can change underneath without
the callers knowing. The order is always the same: a structural question to the database first (who is in this town, who has the player
met, who has this role), which hands back a small set from the index without parsing a record; then, when the words matter, a ranking by
meaning or by shared words over that set; then a bounded result. Nothing here reads the whole campaign and filters in Python: a town's
people are asked for by the places in that town, a named person by the names in the words.

What is returned is index rows (storage.campaign.NPCRow): enough to list, name and filter; load_npcs() for the whole record of the few
that are wanted."""
from __future__ import annotations

import re


def town_places(world, town: str) -> list[str]:
    """Every place id inside a settlement (the town itself and all its parts), so 'who is in this town' is one indexed query."""
    from engine import mapview
    return [pid for pid in world.places if mapview.top_of(world, pid) == town]


def people_in_town(store, world, town: str, gone: bool | None = False) -> list:
    return store.npc_rows(location=town_places(world, town), gone=gone)


def people_at(store, place_id: str, gone: bool | None = False, exclude: tuple = ()) -> list:
    return store.npc_rows(location=place_id, gone=gone, exclude=list(exclude))


def community_places(world, group: str) -> list[str]:
    """Every place whose locals belong to this community (the group a place or its town names)."""
    return [pid for pid in world.places if world.locals_group(pid) == group]


def community(store, world, group: str, exclude: tuple = ()) -> list:
    """Everyone (living or gone) whose home is in this community."""
    return store.npc_rows(location=community_places(world, group), gone=None, exclude=list(exclude)) if group else []


def met_elsewhere(store, present_ids: list[str]) -> list:
    """Everyone the player has met who is not here."""
    return store.npc_rows(met_player=True, exclude=list(present_ids))


def named_in(store, text: str, exclude: tuple = ()) -> list:
    """People whose name (full, or a first name of 5+ letters that only one person has) appears in the words, from the index's names."""
    text = " ".join((text or "").split())
    if not text:
        return []
    rows = [r for r in store.npc_rows(exclude=list(exclude)) if r.name]
    firsts: dict[str, int] = {}
    for r in rows:
        f = r.name.split()[0].lower()
        firsts[f] = firsts.get(f, 0) + 1
    low = text.lower()
    words = set(re.findall(r"[a-z]+", low))
    out = []
    for r in rows:
        first = r.name.split()[0]
        if first.lower() not in words and r.name.lower() not in low:
            continue                                      # a cheap test on the words first; the pattern only for those that could match
        pats = [re.escape(r.name)] + ([re.escape(first)] if len(first) >= 5 and firsts[first.lower()] == 1 else [])
        if re.search(r"\b(?:" + "|".join(pats) + r")\b", text, re.I):
            out.append(r)
    return out


def with_role(store, roles, gone: bool | None = False, not_tier: str | None = None, min_trust: int | None = None) -> list:
    return store.npc_rows(role=list(roles) if not isinstance(roles, str) else roles, gone=gone, not_tier=not_tier, min_trust=min_trust)


def by_meaning(text: str, rows: list, label, k: int, floor: float) -> list:
    """The few rows whose label is closest in meaning to the words (relevance.pick), in that order."""
    from engine import relevance
    if not rows or not (text or "").strip():
        return []
    labels = {label(r): r for r in rows}
    return [labels[l] for l in relevance.pick(text, list(labels), k, floor=floor) if l in labels]
