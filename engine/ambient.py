"""Ambient happenings (f331): the ordinary day of a town, chosen by the engine with no model call.

A situation (engine/pulse.py) is something happening; ambient is the day it happens on: market day, a funeral after a death, the watch
out when the stranger is wanted, harvest and planting, a thin market when prices are high, a town keeping to its walls when the roads
are dangerous. The rules are in data/rules/ambient.yaml. The lines join HAPPENING HERE (engine/truth.py) beside the situations' own,
so the narrator and every speaker see the same day; the narrator is told each once, as with any happening.

since() is the other half: when the player comes back to a town after a while away, the plain changes the world made there in the
meantime, built from the world's state and handed to the narrator once."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
A = yaml.safe_load((ROOT / "data" / "rules" / "ambient.yaml").read_text(encoding="utf-8"))
WORKING = ("morning", "midday", "afternoon")


def lines(store, world, place_id: str, now: int, player=None) -> list[str]:
    """The ambient lines for this place today, in rule order; nothing at a wild place."""
    from engine import clock, pulse, towns, truth
    town = pulse.town_of(world, place_id)
    place = world.places.get(town)
    if place is None or place.danger or not world.peoples_at(town):
        return []
    day = clock.day(now)
    places = towns.town_places(world, town)
    state = None
    scale = truth.scale_of(world, place)
    out = []
    for rule in A.get("rules") or []:
        when = rule.get("when") or {}
        if rule.get("scales") and scale not in rule["scales"]:
            continue
        fmt = {"town": place.name}
        hit = True
        for cond, arg in when.items():
            if cond == "market_day":
                hit = (day + sum(map(ord, town))) % int(arg) == 0 and clock.period(now) in WORKING
            elif cond == "funeral":
                name = towns._lost_lately(store, world, places, now, int(arg))
                hit = bool(name)
                fmt["name"] = name
            elif cond == "heat":
                from engine import law
                hit = player is not None and law.current_heat(player, town, day) >= int(arg)
            elif cond == "season":
                hit = clock.season(now) == arg
            elif cond == "days":
                d = (day - 1) % pulse.P["seasons"]["days_each"] + 1
                hit = int(arg[0]) <= d <= int(arg[1])
            elif cond == "roles":
                hit = any(r in world.places[pid].residents for pid in places for r in arg)
            elif cond in ("prices_at_least", "danger_at_least"):
                state = state if state is not None else store.load_world_state()
                hit = towns._effect_total(state, cond.split("_")[0], places, now) >= int(arg)
            else:
                hit = False
            if not hit:
                break
        if not hit:
            continue
        rng = random.Random(f"{town}:{rule['id']}:{day}")
        text = rng.choice(rule["lines"])
        try:
            text = text.format(**fmt).replace("{Town}", place.name)
        except (KeyError, IndexError):
            continue
        if text.startswith(place.name.lower()):
            text = place.name + text[len(place.name):]
        out.append(text)
    return out


def since(store, world, town: str, then: int, now: int) -> list[str]:
    """What changed at this town while the player was away, in plain lines for the narrator: situations begun and ended, and what still
    leans on prices and danger. Empty when the player was not away long enough, or nothing changed."""
    from engine import clock, pulse, towns
    S = A.get("since") or {}
    if then is None or now - then < S.get("min_days", 1) * 1440 or town not in world.places:
        return []
    state = store.load_world_state()
    if not state:
        return []
    places = towns.town_places(world, town)
    out = []
    for th in state.get("threads", []):
        if th["place"] in places and th.get("made", 0) > then:
            out.append(f"begun since: {th['title']} - {th['stages'][0]['description']}")
    for h in state.get("history", []):
        if h.get("place") in places and h.get("minute", 0) > then:
            out.append(f"ended since: {h['text']}")
    prices = towns._effect_total(state, "prices", places, now)
    danger = towns._effect_total(state, "danger", places, now)
    if abs(prices) >= 10:
        out.append(f"prices here are {'up' if prices > 0 else 'down'} {abs(prices)}% on what they were")
    if danger >= 25:
        out.append(f"the land about is more dangerous than it was (danger up {danger}%)")
    if not out:
        return []
    away = clock.describe_duration(now - then)
    cond = towns.condition(store, world, town, now)
    head = f"SINCE THE PLAYER WAS LAST HERE ({away} ago)" + (f", the town now {cond.name}" if cond.name != "calm" else "") + ":"
    return [head + " " + "; ".join(out[-S.get("most", 4):]) + "."]
