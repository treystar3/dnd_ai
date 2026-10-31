"""(f351) The room changes while the player is in it.

Why: between arrival and leaving the world stood still on the page. People came and went on their role's hours, the weather turned on its
seeded chain, the period changed, people moved on to other doings and moments ended, and none of it was told unless the player looked or
the narrator happened to be called. Now the scene keeps a snapshot of the place at the end of each turn (snapshot) and the next turn, if
the player is still there and the narrator has not written that turn, one change is told in a line of the engine's own (tick): the
weather turning, the hour, a moment ending, someone coming in or going out, someone moving on to something else. One line a turn at
most, and lines about people keep a gap, so it reads as a place with a life of its own and never as a ticker. The lines are
data/rules/stay.yaml."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "stay.yaml").read_text(encoding="utf-8"))


def snapshot(ws) -> dict:
    """What the place is like now, as far as a stay line could notice."""
    from engine import clock, moments, weather
    loc = ws.player.location
    m = moments.active(ws.store, loc, ws.minutes) if loc in ws.world.places else None
    return {"place": loc, "turn": ws.store.meta.turn,
            "present": {n.id: (n.label(), n.activity or "") for n in ws.present
                        if n.id not in (getattr(ws.player, "prisoners", None) or {})},      # the player's prisoners move with the player: not the room's
            "partner": getattr(ws, "partner", None).id if getattr(ws, "partner", None) else "",
            "weather": weather.condition(ws.store.meta.seed, ws.minutes)["id"], "period": clock.period(ws.minutes),
            "moment": (m or {}).get("id", ""), "moment_title": (m or {}).get("title", "")}


def reset(ws) -> None:
    """A new place, or a fight: the next turn starts from here."""
    ws.__dict__["_stay"] = snapshot(ws)


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def tick(ws, narrated: bool = False, rng: random.Random | None = None) -> str:
    """The one change worth a line since the last turn here, or ''. `narrated`: the narrator wrote this turn (its passage is the update)."""
    prev = ws.__dict__.get("_stay")
    now = snapshot(ws)
    ws.__dict__["_stay"] = now
    if not prev or prev["place"] != now["place"] or ws.combat or narrated or getattr(ws, "halted", False):
        return ""
    rng = rng or random.Random()
    L = S["lines"]
    inside = ws.place.type in S.get("indoors", [])
    turn = ws.store.meta.turn
    last_people = ws.__dict__.get("_stay_people_turn", -99)
    gap_ok = turn - last_people >= int(S.get("gap_turns", 3))
    if now["weather"] != prev["weather"]:
        line = (S.get("weather_in" if inside else "weather") or {}).get(now["weather"], "")   # (f423) "Fog comes in." was said in the bar
        if line:
            return line
    if prev["moment"] and not now["moment"]:
        ends = next((sh.get("ends", "") for sh in __import__("engine.moments", fromlist=["M"]).M["shapes"] if sh["id"] == prev["moment"]), "")
        if ends:
            return _cap(ends.replace("{title}", prev["moment_title"]))
    came = [i for i in now["present"] if i not in prev["present"]]
    went = [i for i in prev["present"] if i not in now["present"] and i != prev["partner"]]
    if came and gap_ok:
        label, doing = now["present"][came[0]]
        line = rng.choice(L["arrive_in" if inside else "arrive_out"])
        if "{doing}" in line and not doing:
            line = L["arrive_in" if inside else "arrive_out"][0]
        ws.__dict__["_stay_people_turn"] = turn
        return _cap(line.format(label=label, doing=doing.rstrip(".")))
    if went and gap_ok:
        label, _ = prev["present"][went[0]]
        ws.__dict__["_stay_people_turn"] = turn
        return _cap(rng.choice(L["leave_in" if inside else "leave_out"]).format(label=label))
    if now["period"] != prev["period"]:
        return (S.get("periods") or {}).get(now["period"], "")
    moved = [i for i in now["present"] if i in prev["present"] and i != now["partner"] and now["present"][i][1] != prev["present"][i][1] and now["present"][i][1]]
    if moved and gap_ok and not now["moment"]:
        label, doing = now["present"][moved[0]]
        ws.__dict__["_stay_people_turn"] = turn
        return _cap(rng.choice(L["doing"]).format(label=label, doing=doing.rstrip(".")))
    return ""


def problems(weather_ids: set[str], periods: set[str], place_types: set[str] = ()) -> list[str]:
    """place_types is not checked against `indoors`: a hut or a cabin the player finds is a kind of place the world file does not list."""
    bad = []
    for head in ("weather", "weather_in"):
        for k in (S.get(head) or {}):
            if k not in weather_ids:
                bad.append(f"stay.yaml {head}: '{k}' is not a weather condition")
    for k in (S.get("periods") or {}):
        if k not in periods:
            bad.append(f"stay.yaml periods: '{k}' is not a period of the day")
    for k, v in (S.get("lines") or {}).items():
        if not v or any("{label}" not in x for x in v):
            bad.append(f"stay.yaml lines.{k}: every line names {{label}}")
    return bad
