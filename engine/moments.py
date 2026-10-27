"""(f348) Moments: something going on when the player walks in. data/rules/moments.yaml holds the shapes; the model writes the moment.

A possibility, not a habit. On arriving somewhere the engine rolls once for that place and period of the day, at the chance for the
kind of place, after the place's own cooldown and the town's gap; it draws a shape (a performer, a quarrel, a gathering, a crowd...),
seen shapes less often, and makes one model call (engine/moment_prompts.py, llm/contracts.py MomentProposal) for what the moment is:
this place, this hour, these people, and never like any moment this playthrough has seen (world_state moments_seen). A moment then
lasts its minutes and ends by itself. While it is on, its line sits under HAPPENING HERE for the narrator (told once, as any happening)
and for everyone who speaks; the people here do what the moment has them doing (engine/doings.py); a visitor, if the shape brings one,
is a real person who can be spoken to and leaves when it ends; a mishap may land on the player as they come in; the town keeps the
memory the model wrote. The written moment under each shape is the fallback when the model fails."""
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


def seen_list(store) -> list[dict]:
    """Every moment this playthrough has had: {"shape", "title", "line", "place", "minute"}."""
    return list((store.load_world_state() or {}).get("moments_seen") or [])


def choose(ws, rng: random.Random, present: int) -> dict | None:
    """A shape that fits this place, this period, this many people, and the player's standing; one seen before draws less often."""
    import collections
    from engine import clock, law, pulse
    period = clock.period(ws.minutes)
    town = pulse.town_of(ws.world, ws.player.location)
    times = collections.Counter(s.get("shape") for s in seen_list(ws.store))
    opts = []
    for spec in M.get("shapes") or []:
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
    return rng.choices(opts, weights=[float(s.get("weight", 1)) / (1 + times[s["id"]]) for s in opts])[0]


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


def compose(ws, shape: dict, visitor_role: str, rng: random.Random):
    """The model's moment for this shape, here and now, or None when it fails every try (the caller falls back to the written one)."""
    from engine import moment_prompts as mp, truth
    from llm.contracts import MomentProposal
    from llm.gateway import LLMError, generate
    seen = seen_list(ws.store)
    known = truth.scene_of(ws).known_words()
    request = mp.moment_request(ws, shape, visitor_role, seen[-int(M.get("remember", 40)):])
    ctx = {"roles": sorted({n.role for n in ws.present}), "visitor": bool(visitor_role),
           "mishap": any(e.get("kind") == "hurt" for e in shape.get("effects") or []),
           "given": mp.MOMENT_SYSTEM + "\n" + request, "known": known,
           "seen": [s.get("line", "") for s in seen], "titles": [s.get("title", "") for s in seen]}
    try:
        return generate("moment", mp.MOMENT_SYSTEM, request, MomentProposal, temperature=0.9, max_tokens=700, retries=2,
                        validation_context=ctx, relaxed_context=dict(ctx, seen=[], titles=[]))
    except LLMError:
        return None


def written(shape: dict):
    """The shape's written moment, in the proposal's form, for when the model fails."""
    import types
    w = shape.get("written") or {}
    v = w.get("visitor") or {}
    return types.SimpleNamespace(title=w.get("title", shape["id"]), line=w.get("line", shape.get("brief", "")),
                                 doings=[types.SimpleNamespace(who=d["who"], doing=d["doing"]) for d in w.get("doings") or []],
                                 visitor_epithet=v.get("epithet", ""), visitor_look=v.get("look", ""), visitor_doing=v.get("doing", ""),
                                 mishap=w.get("mishap", ""), memory=w.get("memory", ""), written=True)


def start(ws, shape: dict, rng: random.Random | None = None, use_model: bool = True) -> dict:
    """Begin a moment of this shape here now: the model's moment (or the written one), the record on the place, the visitor made, the
    people's doings and mood, the mishap on the player, and the moment added to what this playthrough has seen."""
    from engine import pools
    rng = rng or random.Random()
    pid = ws.player.location
    st = ws.store.load_place(pid)
    now = ws.minutes
    until = now + int(shape["lasts"])
    visitor_role = rng.choice(list(shape["visitor"].get("roles") or ["traveling_player"])) if shape.get("visitor") else ""
    prop = compose(ws, shape, visitor_role, rng) if use_model else None
    if prop is None:
        prop = written(shape)
    visitor = None
    if visitor_role:
        visitor = make_visitor(ws, st, {"role": visitor_role, "epithet": prop.visitor_epithet, "description": prop.visitor_look,
                                        "doing": prop.visitor_doing, "people": (shape.get("visitor") or {}).get("people", "any")}, rng)
    doings = {"roles": {}}
    for d in prop.doings:
        if d.who == "everyone":
            doings["all"] = d.doing.strip().rstrip(".")
        else:
            doings["roles"][d.who] = d.doing.strip().rstrip(".")
    if visitor_role and (prop.visitor_doing or "").strip():
        doings["roles"][visitor_role] = prop.visitor_doing.strip().rstrip(".")      # the visitor does their own thing, not the room's
    line = _fmt(prop.line.strip(), ws)
    m = {"id": shape["id"], "title": prop.title.strip(), "since": now, "until": until, "line": line, "doings": doings,
         "visitor": visitor.id if visitor else "", "end": {"memory": prop.memory.strip()}, "written": bool(getattr(prop, "written", False))}
    st.moment, st.moment_last = m, now
    ws.store.save_place(st)
    from engine import pulse
    state = ws.store.load_world_state() or pulse.empty_state(now)         # never a partial state: the pulse's shape, with the moment added
    state["moments_seen"] = (state.get("moments_seen") or []) + [{"shape": shape["id"], "title": m["title"], "line": line, "place": pid, "minute": now}]
    ws.store.save_world_state(state)
    if shape.get("mood"):
        for n in ws.present:
            n.mood, n.mood_until = shape["mood"], until
            ws.store.save_npc(n)
    ws.refresh_present()                                           # the doings the moment gives everyone
    c = ws.player.character
    for e in shape.get("effects") or []:
        if e.get("kind") == "hurt" and rng.random() < float(e.get("chance", 0)):
            top = pools.maximum(c, "health")
            c.health = max(1.0, pools.current(c, "health") - top * float(e.get("pct", 0)) / 100)
            ws.__dict__.setdefault("_arrival_lines", []).append(prop.mishap.strip() or "Something hits the player as they come in.")
            console.ledger("You come in at the wrong moment and come away bruised.")
    if ws.weight_hint in (None, "brief", "normal"):
        ws.weight_hint = "rich"                                    # a moment is worth room, even on a return visit
    console.debug(f"moment at {pid}: {shape['id']} '{m['title']}'{' (written)' if m['written'] else ''} until minute {until}"
                  + (f", visitor {visitor.name}" if visitor else ""))
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
    ids = [s.get("id") for s in M.get("shapes") or []]
    if len(ids) != len(set(ids)):
        bad.append("moments.yaml: a shape id is used twice")
    for s in M.get("shapes") or []:
        n = s.get("id", "?")
        if not str(s.get("brief", "")).strip():
            bad.append(f"moments.yaml {n}: needs a brief for the model")
        w = s.get("written") or {}
        if not (w.get("title") and w.get("line") and w.get("memory")):
            bad.append(f"moments.yaml {n}: needs a written moment (title, line, memory) to fall back on")
        for d in w.get("doings") or []:
            if d.get("who") != "everyone" and d.get("who") not in roles:
                bad.append(f"moments.yaml {n}: written doings.who '{d.get('who')}' is not a role in roles.yaml")
        if s.get("visitor") and not (w.get("visitor") or {}).get("epithet"):
            bad.append(f"moments.yaml {n}: a shape with a visitor needs a written visitor to fall back on")
        if any(e.get("kind") == "hurt" for e in s.get("effects") or []) and not w.get("mishap"):
            bad.append(f"moments.yaml {n}: a shape that can hurt needs a written mishap to fall back on")
        for t in s.get("where") or []:
            if t not in place_types:
                bad.append(f"moments.yaml {n}: where '{t}' is no place's type")
        for w in s.get("when") or []:
            if w not in periods:
                bad.append(f"moments.yaml {n}: when '{w}' is not a period of the day")
        if not isinstance(s.get("lasts"), int) or s["lasts"] <= 0:
            bad.append(f"moments.yaml {n}: lasts must be minutes above zero")
        v = s.get("visitor")
        if v and not all(r in roles for r in (v.get("roles") or [])):
            bad.append(f"moments.yaml {n}: a visitor role is not a role in roles.yaml")
        if v and not v.get("roles"):
            bad.append(f"moments.yaml {n}: visitor needs roles")
        for e in s.get("effects") or []:
            if e.get("kind") not in ("hurt",):
                bad.append(f"moments.yaml {n}: effect kind '{e.get('kind')}' is not one the engine applies")
        for k in (s.get("needs") or {}):
            if k not in ("heat",):
                bad.append(f"moments.yaml {n}: needs '{k}' is not a condition the engine knows")
    return bad
