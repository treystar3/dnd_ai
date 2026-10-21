"""What the action interpreter is shown: only what the player's words could be about, instead of the whole world.

The interpreter reads a typed line into actions. It used to be handed every place in the world (190), everyone the player had ever
met, every ware, recipe and ability: 5,400 tokens a turn, growing with every discovery and acquaintance, and a long list for a small
model to pick one id out of. The engine already resolves most of it afterwards (engine/exits for ways out, nearest_alike for "the
smithy"), so the interpreter only needs the candidates that could be meant:

  places    the places of this town, the ways out of it, any place the words name (its own name or its town's), and the few whose
            names are closest in meaning to the words
  people    those met and elsewhere whom the words name or come close to
  catalogues (wares, abilities, pack, recipes, buyers, stash) only when the words are about that kind of thing - judged by meaning
            against one sentence saying what that kind of thing is, the way every topic is judged - or name something in it

Nothing here is a list of trigger words: names come from the world and the player's own things, and "about buying" is a meaning
check. Numbers live in data/rules/interpret.yaml."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

import config
from engine import relevance

ROOT = Path(__file__).resolve().parent.parent
I = yaml.safe_load((ROOT / "data" / "rules" / "interpret.yaml").read_text(encoding="utf-8"))
GENERIC = set(I["generic_words"])


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 3 and w not in GENERIC}


def names_in(text: str, name: str) -> bool:
    """Do the words name this thing? A shared word of four letters or more that is not a generic one ('hall', 'inn')."""
    return bool(words(text) & words(name))


def about(text: str, kind: str) -> bool:
    """Are the words about this kind of thing (buying, crafting, using an item...)? By meaning against the one sentence that says what
    the kind is (interpret.yaml about); by shared words when the helper model is not there."""
    sentence = I["about"].get(kind, "")
    return bool(sentence) and bool(relevance.pick(text, [sentence], 1, floor=I["about_floor"]))


def places(world, here: str, text: str) -> list[tuple[str, str]]:
    """(id, name) of the places the interpreter may send the player to, most certain first: anything the words name, this town, the
    ways out of it, the nearest places of a kind the words name, what is inside the neighbouring towns, then the closest by meaning.
    Only the last two tiers are cut when the list is long."""
    from engine import mapview
    W = world.places
    if here not in W:
        return [(p.id, p.name) for p in W.values()]
    top = mapview.top_of(world, here)
    g = mapview.graph(world)
    nbrs = list(g.get(top, {}))
    low = set(re.findall(r"[a-z]+", (text or "").lower()))
    sure: dict[str, None] = {}
    for pid, p in W.items():                              # anywhere the words name, or whose town they name
        if pid == here:
            continue
        town = W.get(mapview.top_of(world, pid))
        if names_in(text, p.name) or pid in low or (town is not None and town.id != pid and names_in(text, town.name) and p.type in I["named_town_types"]):
            sure[pid] = None
    for pid, p in W.items():                              # this town and everything in it
        if pid != here and (pid == top or mapview.top_of(world, pid) == top):
            sure[pid] = None
    for nb in nbrs:                                       # the ways out
        sure[nb] = None
    kinds = {p.type for p in W.values()} & low           # "the smithy", "an inn": the nearest few places of that kind, wherever they are
    if kinds:
        far = mapview.travel_times(g, top)
        for kind in sorted(kinds):
            near = sorted((p for p in W.values() if p.type == kind and p.id != here and p.id not in sure),
                          key=lambda p: far.get(mapview.top_of(world, p.id), 10 ** 9))
            for p in near[:I["nearest_of_kind"]]:
                sure[p.id] = None
    rest: dict[str, None] = {}
    for pid, p in W.items():                              # what is inside each neighbouring town ("the market" from the fields)
        if pid != here and pid not in sure and mapview.top_of(world, pid) in nbrs and p.type in I["named_town_types"]:
            rest[pid] = None
    others = {p.name: pid for pid, p in W.items() if pid != here and pid not in sure and pid not in rest and p.type != "road"}
    if others and words(text):                            # and the few closest in meaning to the words, when they are close at all
        for name in relevance.pick(text, list(others), I["places_by_meaning"], floor=I["place_floor"]):
            rest[others[name]] = None
    room = max(0, I["most_places"] - len(sure))
    ids = list(sure) + list(rest)[:room]
    return [(pid, W[pid].name) for pid in ids]


def people_elsewhere(rows, text: str) -> list:
    """Of everyone met who is not here, those the words name (name, epithet or role) or come close to; at most a few."""
    rows = list(rows)
    if not rows:
        return []
    named = [r for r in rows if names_in(text, r.name) or (r.epithet and names_in(text, r.epithet))
             or names_in(text, r.role.replace("_", " ")) or r.id in (text or "").lower().split()]
    keep = {r.id: r for r in named}
    rest = [r for r in rows if r.id not in keep]
    if rest and words(text) and len(keep) < I["most_people"]:
        labels = {f"{r.label()}, {r.role.replace('_', ' ')}": r for r in rest}
        for lab in relevance.pick(text, list(labels), I["people_by_meaning"], floor=I["person_floor"]):
            keep[labels[lab].id] = labels[lab]
    return list(keep.values())[:I["most_people"]]


def catalogue(text: str, kind: str, items: list[str], always_if_short: int = 0) -> list[str]:
    """A catalogue (wares, abilities, the pack...) goes in whole when the words are about that kind of thing or name something in it,
    or when it is short enough not to matter; otherwise it is left out and the interpreter is told so."""
    items = [i for i in items if i]
    if not items:
        return []
    if len(items) <= always_if_short:
        return items
    if about(text, kind) or any(names_in(text, i) for i in items):
        return items
    return []
