"""Towns with identity (f316): a town's profile, and its condition read off the world's state.

The profile (data/world/towns/<id>.yaml, loaded by world/loader.py) says what a town is like and what it is called: its character,
its landmarks and districts, the trouble underneath, its calendar. The condition - calm, uneasy, mourning, hungry, festive,
prospering, besieged (data/rules/towns.yaml) - is never stored: it is read each time from the situations running at the town, the
effects they left, who was lost lately, and the town's own holidays. Everyone reads it through the truth layer (engine/truth.py), so
the narrator, the people, the party and the interpreter never disagree about the state the town is in."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
R = yaml.safe_load((ROOT / "data" / "rules" / "towns.yaml").read_text(encoding="utf-8"))


@dataclass
class Condition:
    name: str = "calm"
    why: str = ""                 # what made it so, in a few words (for the debug line and the town facet)
    hint: str = ""                # how it shows in the streets (the narrator's cue; every speaker's line)
    crowd: str = ""               # the crowd line while it holds, or '' for the time of day's own


def profile(world, place_id: str):
    """The profile of the town this place belongs to, or None."""
    return world.town(place_id)


def festival_today(world, place_id: str, now: int) -> str:
    """The name of the holiday on today, from the town's own calendar, or ''."""
    from engine import clock, pulse
    t = profile(world, place_id)
    if not t or not t.festivals:
        return ""
    s = pulse.P["seasons"]
    day = clock.day(now)
    season = s["order"][((day - 1) // s["days_each"]) % len(s["order"])]
    day_in = (day - 1) % s["days_each"] + 1
    for f in t.festivals:
        if f.season == season and f.day <= day_in < f.day + f.days:
            return f.name
    return ""


def _effect_total(state: dict, kind: str, places: set[str], now: int) -> int:
    return sum(e["value"] for e in state.get("effects", []) if e["kind"] == kind and e["place"] in places and e["until"] > now)


def _threads_at(world, state: dict, places: set[str]) -> list[tuple[dict, str]]:
    """Active situations at the town, each with the kind of pressure that started it ('' when none did)."""
    out = []
    for th in state.get("threads", []):
        if th["status"] == "active" and th["place"] in places:
            p = world.pressures.get(th.get("pressure") or "")
            out.append((th, p.kind if p else th.get("kind", "")))         # (f323) the writer names the kind when no pressure seeded it
    return out


def _lost_lately(store, world, places: set[str], now: int, days: int) -> str:
    """The name of someone of the town taken out of the story within these days, where the manner of it reads as a death; else ''."""
    from engine import relevance
    for row in reversed(store.journal_tail(20, kind="npc_gone")):
        if now - row["minute"] > days * 1440:
            continue
        data = row.get("data") or {}
        if data.get("place") not in places:
            continue
        how = data.get("how") or ""
        if how and relevance.pick(how, [R["death_reads_as"]], 1):
            return row.get("text", "").split(" is gone")[0]
    return ""


def town_places(world, town: str) -> set[str]:
    """The places whose state is the town's: its own, and the wild places on its doorstep (connected within nearby_minutes, not towns
    themselves) - wolves in the wood beside it are the town's trouble too."""
    from engine import pulse
    places = {pid for pid in world.places if pulse.town_of(world, pid) == town}
    near = R.get("nearby_minutes", 60)
    links = dict(world.places[town].connects)
    for pid, p in world.places.items():                               # a link is written on one side only
        if town in p.connects and pid not in links:
            links[pid] = p.connects[town]
    for other, minutes in links.items():
        p = world.places.get(other)
        if p is not None and minutes <= near and not p.parent and p.type not in ("town", "city", "village"):
            places.add(other)
    return places


def condition(store, world, place_id: str, now: int) -> Condition:
    """The town's condition right now, by the first rule of data/rules/towns.yaml that holds."""
    from engine import pulse
    town = pulse.town_of(world, place_id)
    if town not in world.places or world.places[town].danger:
        return Condition()
    places = town_places(world, town)
    state = store.load_world_state()
    threads = _threads_at(world, state, places)
    danger = _effect_total(state, "danger", places, now)
    prices = _effect_total(state, "prices", places, now)
    lost = None
    for rule in R["rules"]:
        name, why = rule["condition"], ""
        if "danger_at_least" in rule and danger >= rule["danger_at_least"]:
            why = f"danger on the roads and in the fields up {danger}%"
        elif "prices_at_least" in rule and prices >= rule["prices_at_least"]:
            why = f"prices up {prices}%"
        elif "prices_at_most" in rule and prices <= rule["prices_at_most"]:
            why = f"prices down {-prices}%"
        elif "thread_kinds" in rule:
            hit = next((th for th, kind in threads if kind in rule["thread_kinds"] and th["tier"] in rule.get("thread_tiers", [th["tier"]])), None)
            if hit:
                why = hit["title"]
        elif "lost_within_days" in rule:
            if lost is None:
                lost = _lost_lately(store, world, places, now, rule["lost_within_days"])
            if lost:
                why = f"{lost} lost lately"
        elif "fell_within_days" in rule:                                   # (f324) the town fell to a cataclysm
            fell = state.get("fallen", {}).get(town)
            if fell is not None and now - fell <= rule["fell_within_days"] * 1440:
                why = f"fell {max(1, (now - fell) // 1440)} days ago"
        elif rule.get("festival"):
            f = festival_today(world, place_id, now)
            if f:
                why = f
        if why:
            c = R["conditions"][name]
            return Condition(name, why, c.get("hint", ""), c.get("crowd", ""))
    return Condition()


def resident_lines(world, place_id: str, cond: Condition | None) -> list[str]:
    """What the people of a town are told about it when they are made or deepened (npc/prompts): the character, the condition, the
    trouble underneath. Nothing for a place with no profile."""
    t = profile(world, place_id)
    if not t:
        return []
    L = R["resident_lines"]
    out = []
    if t.character:
        out.append(L["character"].format(character=" ".join(t.character.split())))
    if cond and cond.name != "calm" and cond.hint:
        out.append(L["condition"].format(hint=cond.hint, name=cond.name) + mourned(cond))
    if t.trouble:
        out.append(L["trouble"].format(trouble=" ".join(t.trouble)))
    return out


def mourned(cond) -> str:
    """(f423) Who a mourning town mourns, so its people and the narrator can name them: before, a town grieved for no one in particular."""
    if cond is None or cond.name != "mourning" or not cond.why.endswith(" lost lately"):
        return ""
    return f" The one mourned: {cond.why.removesuffix(' lost lately')}."


def thread_lines(world, place_id: str, big: bool = False) -> list[str]:
    """What the writer of the world's situations is told about the town: its character and the trouble underneath; its secret only for a
    big situation."""
    t = profile(world, place_id)
    if not t:
        return []
    out = []
    if t.character:
        out.append("THE TOWN: " + " ".join(t.character.split()))
    if t.trouble:
        out.append("WHAT IS WRONG UNDERNEATH: " + " ".join(t.trouble))
    if big and t.secret:
        out.append("THE TOWN'S SECRET (a big situation may turn on it; nobody says it aloud): " + " ".join(t.secret.split()))
    return out


def landmarks_at(world, place_id: str) -> list:
    """The named things that stand at this place, or - at the town's top place - anywhere in the town."""
    t = profile(world, place_id)
    if not t:
        return []
    if place_id == t.id:
        return list(t.landmarks)
    return [l for l in t.landmarks if l.where == place_id]
