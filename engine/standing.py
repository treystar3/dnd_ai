"""Standing: how the groups of each town regard the player (guards, merchants, outlaws...), and the rumors that carry it between towns.

The numbers are hidden; the player sees a word. A deed someone saw changes standing in that town at once and becomes news. News
reaches other towns after the usual travel delay (engine/pulse.py), and when the player arrives there it moves standing too, weaker
the further it came. Nothing here talks to a model or to the screen. All numbers are in data/rules/standing.yaml."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import pulse

S = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "standing.yaml").read_text(encoding="utf-8"))
GROUPS, SP, DEEDS, FX = S["groups"], S["spread"], S["deeds"], S["effects"]


# ---------- the numbers ----------

def value(player, town: str, group: str, day: int) -> float:
    rec = player.standing.get(town, {}).get(group)
    return float(rec[0]) if rec else 0.0


def add(player, town: str, group: str, delta: float, day: int) -> float:
    v = max(-100.0, min(100.0, value(player, town, group, day) + delta))
    if abs(v) < 0.05:
        player.standing.get(town, {}).pop(group, None)
    else:
        player.standing.setdefault(town, {})[group] = [round(v, 2), day]
    return v


def word(v: float) -> str:
    for threshold, name in S["words"]:
        if v >= threshold:
            return name
    return S["words"][-1][1]


def step(table: list, v: float) -> float:
    """The first entry of a table (strongest first) that v reaches: a positive threshold from above, a negative one from below."""
    for threshold, out in table:
        if (threshold > 0 and v >= threshold) or (threshold < 0 and v <= threshold):
            return out
    return 0


def tithe_weight(copper: int) -> float:
    """How much a tithe of this size counts, or 0 if it is too small to matter."""
    import math
    T = S["tithe"]
    floor = T["min_gold"] * 10000
    if copper < floor:
        return 0.0
    return min(T["cap"], T["base"] + T["per_doubling"] * math.log2(copper / floor))


def price_factor(player, town: str, day: int) -> float:
    return 1 + step(FX["price"], value(player, town, "merchants", day))


def heat_shift(player, town: str, day: int) -> float:
    return step(FX["heat_shift"], value(player, town, "guards", day))


def trust_shift(player, town: str, npc_groups: list[str], day: int) -> int:
    mine = [value(player, town, g, day) for g in npc_groups if g in GROUPS]
    return round(sum(mine) / len(mine) * FX["trust_per_point"]) if mine else 0


def standings(player, town: str, day: int) -> list[tuple[str, str]]:
    """(group, word) for every group that has an opinion of the player here."""
    return [(g, word(value(player, town, g, day))) for g in GROUPS if abs(value(player, town, g, day)) >= 1]


def strongest(player, town: str, day: int) -> list[tuple[str, float]]:
    found = [(g, value(player, town, g, day)) for g in GROUPS]
    found = [x for x in found if abs(x[1]) >= FX["arrival_threshold"]]
    return sorted(found, key=lambda x: -abs(x[1]))[:FX["arrival_notes"]]


# ---------- deeds into news ----------

def carriers(world, witnesses: list, kind: str) -> list[str]:
    """The groups that pass a deed on: the groups of whoever saw it, the deed's own carriers, and everyone if a non-guard saw."""
    groups = set(DEEDS[kind].get("carriers", []))
    for n in witnesses:
        role = world.roles.get(n.role)
        groups |= set(getattr(n, "knowledge_groups", []) or (role.knowledge_groups if role else []))
        if n.role not in ("guard", "watch_captain", "royal_guard"):
            groups.add("everyone")
    if DEEDS[kind].get("public"):
        groups.add("everyone")
    return sorted(groups)


def report(store, world, player, kind: str, town: str, place_name: str, who: str, minute: int, day: int,
           witnesses: list | None = None, item: str = "", weight: float = 1.0, seed: int | str = 0) -> dict | None:
    """A deed the world saw: standing moves here at once, and it becomes news. Returns the news item, or None if nothing was seen."""
    rule = DEEDS[kind]
    if not rule.get("public") and not witnesses:
        return None
    if world.places[town].danger:
        return None
    state = store.load_world_state() or pulse.empty_state(minute)
    news = state.setdefault("news", [])
    nid = f"{kind}-{minute}-{len(news)}"
    twisted = random.Random(f"{seed}:twist:{nid}").uniform(0, 100) < SP["twist_chance"]
    fmt = dict(who=who, place=place_name, item=item or "something")
    true_text, told = rule["text"].format(**fmt), rule["twisted"].format(**fmt)
    entry = {"text": told if twisted else true_text, "origin": town, "minute": minute, "groups": carriers(world, witnesses or [], kind),
             "deed": {"id": nid, "kind": kind, "weight": weight, "twisted": twisted, "true": true_text, "who": who}}
    news.append(entry)
    state["news"] = pulse.cap_news(news)
    store.save_world_state(state)
    for group, delta in rule["deltas"].items():
        add(player, town, group, delta * weight, day)
    player.standing_seen.setdefault(nid, {})[town] = {}      # felt here already
    return entry


def reached(world, entry: dict, town: str, now: int) -> bool:
    keep = pulse.P["news"]["keep_days"] * 1440
    return now - entry["minute"] <= keep and entry["minute"] + pulse.travel_delay(world, entry["origin"], town) <= now


def far_factor(world, entry: dict, town: str) -> float:
    days = pulse.travel_delay(world, entry["origin"], town) / 1440
    return SP["far_factor"] * 0.5 ** (days / SP["half_distance_days"])


def arrivals(store, world, player, town: str, now: int, day: int) -> list[tuple[str, float]]:
    """Deed news that has reached this town since the player was last here moves standing now. Returns (group, change) for notes."""
    if world.places[town].danger:
        return []
    state = store.load_world_state() or {}
    changes: dict[str, float] = {}
    live = set()
    from engine import world_perks
    c = getattr(player, "character", None)
    if world_perks.unseen(c):
        return []                                        # Nobody: the news is told, but never of the face in front of them
    for entry in state.get("news", []):
        deed = entry.get("deed")
        if not deed:
            continue
        live.add(deed["id"])
        seen = player.standing_seen.setdefault(deed["id"], {})
        famous = world_perks.famous_here(c, world, entry["origin"], town)
        if town in seen or not (famous or reached(world, entry, town, now)):
            continue
        heard = set(entry["groups"])
        near = 1.0 if famous else far_factor(world, entry, town)
        mult = near * deed["weight"] * (SP["twist_factor"] if deed["twisted"] else 1)
        exact = near * deed["weight"]
        applied = {}
        for group, delta in DEEDS[deed["kind"]]["deltas"].items():
            if "everyone" not in heard and group not in heard:
                continue
            amount = delta * mult
            if abs(amount) < SP["minimum"]:
                continue
            add(player, town, group, amount, day)
            applied[group] = round(amount, 2)
            changes[group] = changes.get(group, 0) + amount
            if deed["twisted"]:
                applied[f"{group}:x"] = round(amount - delta * exact, 2)      # the part that is exaggeration, taken back if corrected
        seen[town] = applied
    for nid in [k for k in player.standing_seen if k not in live]:
        del player.standing_seen[nid]
    return sorted(changes.items(), key=lambda x: -abs(x[1]))


# ---------- rumors ----------

def about_you(store, world, town: str, now: int) -> list[dict]:
    """The tales about the player that have reached this town, newest first."""
    state = store.load_world_state() or {}
    found = [e for e in state.get("news", []) if e.get("deed") and reached(world, e, town, now)]
    return sorted(found, key=lambda e: -e["minute"])


def correct(store, player, entry_id: str, now: int) -> bool:
    """The tale is set straight: its text is the truth again, and what the exaggeration did in far towns is taken back."""
    state = store.load_world_state() or {}
    for entry in state.get("news", []):
        deed = entry.get("deed")
        if deed and deed["id"] == entry_id and deed["twisted"]:
            deed["twisted"] = False
            entry["text"] = deed["true"]
            day = now // 1440
            for town, applied in player.standing_seen.get(entry_id, {}).items():
                for key, extra in applied.items():
                    if key.endswith(":x"):
                        add(player, town, key[:-2], -extra, day)
            for town in player.standing_seen.get(entry_id, {}):
                player.standing_seen[entry_id][town] = {k: v for k, v in player.standing_seen[entry_id][town].items() if not k.endswith(":x")}
            store.save_world_state(state)
            return True
    return False
