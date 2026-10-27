"""(f348) Moments: something going on when the player walks in, chosen by the engine with no model call. data/rules/moments.yaml.

A possibility, not a habit. On arriving somewhere the engine rolls once for that place and period of the day, at the chance for the
kind of place, after the place's own cooldown and the town's gap; a moment then lasts its minutes and ends by itself. While it is on,
its line sits under HAPPENING HERE for the narrator (told once, as any happening) and for everyone who speaks; the people here do what
the moment has them doing (engine/doings.py); a visitor, if it brings one, is a real person who can be spoken to and leaves when it
ends; an effect may land on the player as they come in; the town keeps a memory of it. Nothing here waits on the model: the narrator
dresses the arrival, the townsfolk answer in the middle of it."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from ui import console

ROOT = Path(__file__).resolve().parent.parent
M = yaml.safe_load((ROOT / "data" / "rules" / "moments.yaml").read_text(encoding="utf-8"))


def active(store, place_id: str, now: int) -> dict | None:
    st = store.load_place(place_id)
    m = st.moment
    return m if m and m.get("until", 0) > now else None


def lines_at(store, place_id: str, now: int) -> list[str]:
    """The moment's line for HAPPENING HERE, while it lasts."""
    m = active(store, place_id, now)
    return [m["line"]] if m else []


def _fmt(text: str, ws, visitor_label: str = "") -> str:
    from engine import pulse
    town = pulse.town_of(ws.world, ws.player.location)
    out = text.replace("{place}", ws.place.name).replace("{town}", ws.world.places[town].name if town in ws.world.places else ws.place.name)
    out = out.replace("{visitor}", visitor_label or "a visitor")
    return out[:1].upper() + out[1:]


def _town_last(ws, town: str) -> int:
    """The minute the town's last moment began, at any of its places; -1 for never."""
    from engine import towns
    last = -1
    for pid in towns.town_places(ws.world, town):
        try:
            last = max(last, ws.store.load_place(pid).moment_last)
        except Exception:
            pass
    return last


def _within(now: int, last: int, hours: float) -> bool:
    """Is `last` (a minute, or -1 for never) within this many hours of now?"""
    return last >= 0 and now - last < hours * 60


def choose(ws, rng: random.Random, present: int) -> dict | None:
    """A moment that fits this place, this period, this many people, and the player's standing."""
    from engine import clock, law, pulse
    period = clock.period(ws.minutes)
    town = pulse.town_of(ws.world, ws.player.location)
    opts = []
    for spec in M.get("moments") or []:
        if ws.place.type not in spec.get("where", []) or (spec.get("when") and period not in spec["when"]):
            continue
        if present < spec.get("needs_people", 1):
            continue
        needs = spec.get("needs") or {}
        if "heat" in needs:
            try:
                if law.current_heat(ws.player, town, clock.day(ws.minutes)) < needs["heat"]:
                    continue
            except Exception:
                continue
        opts.append(spec)
    if not opts:
        return None
    return rng.choices(opts, weights=[float(s.get("weight", 1)) for s in opts])[0]


def on_enter(ws) -> None:
    """On arrival: a moment still on carries on (its visitor back in the room after a reload); one that ended while the player was away
    is closed; otherwise one roll for this place and period."""
    from engine import clock, pulse
    pid = ws.player.location
    st = ws.store.load_place(pid)
    now = ws.minutes
    if st.moment and st.moment.get("until", 0) > now:
        if st.moment.get("visitor") and not any(n.id == st.moment["visitor"] for n in ws.residents) and ws.store.npc_exists(st.moment["visitor"]):
            v = ws.store.load_npc(st.moment["visitor"])
            if not v.gone:
                ws.residents.append(v)
        ws.refresh_present()
        return
    if st.moment:
        end(ws, st)
    if ws.place.danger or not ws.world.peoples_at(pid) or ws.combat:
        return
    key = f"{clock.day(now)}:{clock.period(now)}"
    if st.moment_roll == key:
        return
    st.moment_roll = key
    ws.store.save_place(st)
    chance = float((M.get("chance") or {}).get(ws.place.type, 0))
    town = pulse.town_of(ws.world, pid)
    if _within(now, st.moment_last, M.get("cooldown_hours", 36)) or _within(now, _town_last(ws, town), M.get("town_gap_hours", 12)):
        return
    rng = random.Random(f"{ws.store.meta.seed}:moment:{pid}:{key}")
    if chance <= 0 or rng.random() >= chance:
        return
    spec = choose(ws, rng, len(ws.present))
    if spec:
        start(ws, spec, rng)


def start(ws, spec: dict, rng: random.Random | None = None) -> dict:
    """Begin a moment here now: the record on the place, the visitor made, the people's doings and mood, the effect on the player."""
    from engine import pools
    rng = rng or random.Random()
    pid = ws.player.location
    st = ws.store.load_place(pid)
    now = ws.minutes
    until = now + int(spec["lasts"])
    visitor, label = None, ""
    if spec.get("visitor"):
        visitor = make_visitor(ws, st, spec["visitor"], rng)
        label = visitor.label()
    m = {"id": spec["id"], "title": spec["title"], "since": now, "until": until, "line": _fmt(spec["line"], ws, label),
         "doings": spec.get("doings") or {}, "visitor": visitor.id if visitor else "", "end": spec.get("end") or {}}
    st.moment, st.moment_last = m, now
    ws.store.save_place(st)
    if spec.get("mood"):
        for n in ws.present:
            n.mood, n.mood_until = spec["mood"], until
            ws.store.save_npc(n)
    ws.refresh_present()                                           # the doings the moment gives everyone
    c = ws.player.character
    for e in spec.get("effects") or []:
        if e.get("kind") == "hurt" and rng.random() < float(e.get("chance", 0)):
            top = pools.maximum(c, "health")
            c.health = max(1.0, pools.current(c, "health") - top * float(e.get("pct", 0)) / 100)
            ws.__dict__.setdefault("_arrival_lines", []).append(e.get("line", "Something hits the player as they come in."))
            console.ledger("You come in at the wrong moment and come away bruised.")
    if ws.weight_hint in (None, "brief", "normal"):
        ws.weight_hint = "rich"                                    # a moment is worth room, even on a return visit
    console.debug(f"moment at {pid}: {spec['id']} until minute {until}" + (f", visitor {visitor.name}" if visitor else ""))
    return m


def make_visitor(ws, st, spec: dict, rng: random.Random):
    """Someone from elsewhere, made as a real person of this place for the while."""
    from npc import life, names
    from npc.models import NPC
    from npc.traits import assign_traits, npc_rng
    pid = ws.player.location
    peoples = ws.world.peoples_at(pid) or {"human": 1}
    people = spec.get("people") if spec.get("people") and spec["people"] != "any" else rng.choices(list(peoples), weights=list(peoples.values()))[0]
    name, gender = names.pick(people, ws.store.npc_names(), rng)
    npc = NPC(id=life._unique_id(ws.store, name), name=name, gender=gender, people=people, role=spec["role"], location=pid,
              epithet=spec.get("epithet", ""), description=spec.get("description", ""), activity=spec.get("doing", ""))
    if ws.catalog:
        assign_traits(npc, ws.catalog, npc_rng(ws.store.meta.seed, npc.id))
    life.inner_life(npc, ws.store, ws.world)
    ws.store.save_npc(npc)
    st.residents.append(npc.id)
    ws.residents.append(npc)
    return npc


def tick(ws) -> None:
    """A moment that has run its minutes ends."""
    st = ws.store.load_place(ws.player.location)
    if st.moment and st.moment.get("until", 0) <= ws.minutes:
        end(ws, st)


def end(ws, st) -> None:
    """The moment ends: the visitor takes the road, the town keeps a memory, the people go back to their own doings."""
    from engine import pulse
    m = st.moment or {}
    if m.get("visitor") and ws.store.npc_exists(m["visitor"]):
        v = ws.store.load_npc(m["visitor"])
        v.gone = "took the road on"
        ws.store.save_npc(v)
        st.residents = [r for r in st.residents if r != v.id]
        ws.residents = [n for n in ws.residents if n.id != v.id]
    st.moment = {}
    ws.store.save_place(st)
    memory = (m.get("end") or {}).get("memory", "")
    if memory:
        town = pulse.town_of(ws.world, st.id)
        tp = ws.store.load_place(town) if town != st.id else st
        tp.memory = (tp.memory + [{"text": _fmt(memory, ws), "minute": ws.minutes}])[-30:]
        ws.store.save_place(tp)
    for n in ws.present:
        if n.mood_until and n.mood_until <= ws.minutes:
            n.mood, n.mood_until = "", 0
    console.debug(f"moment ended at {st.id}: {m.get('id')}")
    if ws.player.location == st.id:
        ws.refresh_present()


def problems(roles: set[str], place_types: set[str], periods: set[str]) -> list[str]:
    bad = []
    for t in (M.get("chance") or {}):
        if t not in place_types:
            bad.append(f"moments.yaml chance: '{t}' is no place's type")
    for k in ("cooldown_hours", "town_gap_hours"):
        if not isinstance(M.get(k), (int, float)) or M[k] < 0:
            bad.append(f"moments.yaml {k}: needs a number of hours")
    ids = [s.get("id") for s in M.get("moments") or []]
    if len(ids) != len(set(ids)):
        bad.append("moments.yaml: a moment id is used twice")
    for s in M.get("moments") or []:
        n = s.get("id", "?")
        for t in s.get("where") or []:
            if t not in place_types:
                bad.append(f"moments.yaml {n}: where '{t}' is no place's type")
        for w in s.get("when") or []:
            if w not in periods:
                bad.append(f"moments.yaml {n}: when '{w}' is not a period of the day")
        if not isinstance(s.get("lasts"), int) or s["lasts"] <= 0:
            bad.append(f"moments.yaml {n}: lasts must be minutes above zero")
        if not str(s.get("line", "")).strip():
            bad.append(f"moments.yaml {n}: needs a line")
        v = s.get("visitor")
        if v and v.get("role") not in roles:
            bad.append(f"moments.yaml {n}: visitor role '{v.get('role')}' is not a role in roles.yaml")
        for r in ((s.get("doings") or {}).get("roles") or {}):
            if r not in roles:
                bad.append(f"moments.yaml {n}: doings.roles '{r}' is not a role in roles.yaml")
        for e in s.get("effects") or []:
            if e.get("kind") not in ("hurt",):
                bad.append(f"moments.yaml {n}: effect kind '{e.get('kind')}' is not one the engine applies")
        for k in (s.get("needs") or {}):
            if k not in ("heat",):
                bad.append(f"moments.yaml {n}: needs '{k}' is not a condition the engine knows")
    return bad
