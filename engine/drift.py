"""Drift (f331): the world settling and shifting between pulses, with no model call.

The pulse (engine/pulse.py) makes things happen; drift is what happens to them afterwards. Feelings nobody stirs ease toward neutral
and are forgotten; a mood the world gave someone fades; a person whose motive ended finds a new one from their traits after a while;
prices lean up while trouble runs at a town and danger leans up in its wild places, and both lean back when it ends; travelling trades
move along the roads to the next town; a town's groups slowly forget the stranger. Every rule and number is in data/rules/pulse.yaml
under drift.

A pass runs once a game day on its own clock (world_state drift_last), outside the pulse's event budget, and does a bounded amount of
work however big the campaign has grown: people are looked at a chunk per pass, round robin, and what eases is measured by the game
time gone, not by the passes run, so a long absence is many days of change for little computation. The player is never loaded or saved
here: standing lives on the player's record, which the scene holds and saves at the end of the turn, so a pass returns the player
deltas and the scene applies them (scenes/world.py run_pulse)."""
from __future__ import annotations

import random

from engine import pulselog
from ui import console


def rules() -> dict:
    from engine.pulse import P
    return P.get("drift") or {}


def interval() -> int:
    return rules().get("every_hours", 24) * 60


def catch_up(store, world, state: dict, now: int, rng: random.Random) -> dict:
    """Run the passes due since the last. Returns the player deltas for the scene to apply: {"standing": [(town, group, delta, day)]}."""
    D = rules()
    if not D:
        return {}
    step = interval()
    last = state.get("drift_last")
    if last is None:
        state["drift_last"] = now
        return {}
    due = (now - last) // step
    if due <= 0:
        return {}
    most = D.get("most_passes", 30)
    skipped = max(0, due - most)
    deltas: dict = {}
    t = last + skipped * step
    for _ in range(min(due, most)):
        t += step
        one_pass(store, world, state, t, rng, deltas)
    state["drift_last"] = last + due * step
    return deltas


def one_pass(store, world, state: dict, t: int, rng: random.Random, deltas: dict) -> None:
    notes = []
    n = people(store, world, state, t, rng)
    if n:
        notes.append(n)
    n = situations(store, world, state, t)
    if n:
        notes.append(n)
    n = travellers(store, world, state, t, rng)
    if n:
        notes.append(n)
    n = standing(store, state, t, deltas)
    if n:
        notes.append(n)
    if notes:
        pulselog.note("drift", "; ".join(notes))


# ---------- people: feelings ease, moods fade, motives return

def people(store, world, state: dict, t: int, rng: random.Random) -> str:
    """A chunk of the living, round robin: relations nobody has stirred ease by the days gone, moods past their time clear, and a person
    whose motive ended may take up another."""
    D = rules()
    size = D.get("people_per_pass", 40)
    ids = [r.id for r in store.npc_rows(gone=False)]
    if not ids:
        return ""
    start = state.get("drift_cursor", 0) % len(ids)
    chunk = (ids + ids)[start:start + size][:len(ids)]
    state["drift_cursor"] = (start + size) % len(ids)
    R, M, V = D.get("relations", {}), D.get("moods", {}), D.get("motives", {})
    settle, per_day = R.get("settle_after_days", 7) * 1440, R.get("per_day", 1.0)
    eased = faded = moved = ended = 0
    for npc in store.load_npcs(chunk):
        changed = False
        for oid, r in list(npc.relations.items()):
            since = r.get("since", 0)
            if per_day <= 0 or t - since < settle:
                continue
            frm = max(r.get("eased", since), since + settle)
            days = (t - frm) / 1440
            if days <= 0:
                continue
            score = r.get("score", 0)
            step = min(abs(score), per_day * days)
            score = score - step if score > 0 else score + step
            r["score"], r["eased"] = round(score), t
            if abs(r["score"]) < 1:
                del npc.relations[oid]                              # forgotten: nothing left to keep
            changed = True
            eased += 1
        if npc.mood:
            if npc.mood_until <= 0:
                npc.mood_until = t + M.get("days", 6) * 1440        # a mood from before moods had clocks gets one now
                changed = True
            elif t >= npc.mood_until:
                npc.mood, npc.mood_until = "", 0
                changed = True
                faded += 1
        if not npc.motive and npc.motive_done_at >= 0 and t - npc.motive_done_at >= V.get("cooldown_days", 12) * 1440:
            if rng.random() < V.get("chance", 0.5):
                npc.motive = motive_for(npc, world, V, rng)
                npc.motive_done_at = -1
                npc.motive_since = t
                moved += 1
            else:
                npc.motive_done_at = t
            changed = True
        elif npc.motive and npc.tier == "background" and V.get("lasts_days"):      # (f334) a goal nobody watched runs its course
            if not npc.motive_since:
                npc.motive_since = t                                              # a goal from before clocks were kept starts its now
                changed = True
            elif t - npc.motive_since >= V["lasts_days"] * 1440:
                motive_ends(npc, store, world, V, M, t, rng)
                changed = True
                ended += 1
        if changed:
            store.save_npc(npc)
    bits = [f"{eased} feelings eased" if eased else "", f"{faded} moods faded" if faded else "", f"{moved} took up a new motive" if moved else "",
            f"{ended} saw a motive through" if ended else ""]
    return ", ".join(b for b in bits if b)


def motive_ends(npc, store, world, V: dict, M: dict, t: int, rng: random.Random) -> None:
    """(f334) A background person's goal ends without a model call: made or not, by the rule's chance; the town remembers it in a line
    (engine/matters.py town_note), the person carries a mood for a while, and the cooldown starts toward the next."""
    from engine import matters
    O = V.get("outcomes") or {}
    made = rng.random() < V.get("made_chance", 0.5)
    lines = O.get("made" if made else "failed") or ["{name}, the {role}, saw their goal through." if made else "{name}, the {role}, gave up on their goal."]
    role = npc.role.replace("_", " ")
    motive = npc.motive.strip().rstrip(".")
    matters.town_note(store, world, npc.location, rng.choice(lines).format(name=npc.name, role=role, motive=motive), t)
    moods = O.get("mood_made" if made else "mood_failed")
    if moods:
        npc.mood, npc.mood_until = rng.choice(moods), t + M.get("days", 6) * 1440
    npc.motive, npc.motive_since, npc.motive_done_at = "", 0, t


def motive_for(npc, world, V: dict, rng: random.Random) -> str:
    seeds = V.get("seeds") or {}
    pool = next((seeds[tr] for tr in npc.traits if tr in seeds), None) or seeds.get("default") or ["to get by"]
    from engine import pulse
    town = pulse.town_of(world, npc.location)
    name = world.places[town].name if town in world.places else "town"
    return rng.choice(pool).format(role=npc.role.replace("_", " "), town=name)


# ---------- situations: prices and danger lean while trouble runs

def situations(store, world, state: dict, t: int) -> str:
    """Re-lay the lean of every running situation: prices at its town, danger in the town's wild places, by its kind and severity.
    The rows are the drift's own (cause drift) and short-lived, so they end soon after the situation does."""
    D = rules().get("situations") or {}
    if not D:
        return ""
    from engine import threads, towns, pulse
    state["effects"] = [e for e in state.get("effects", []) if e.get("cause") != "drift"]
    until = t + D.get("days", 2) * 1440
    cap = D.get("cap", 25)
    lean: dict[tuple, dict] = {}
    for th in [x for x in state.get("threads", []) if x["status"] == "active"]:
        p = world.pressures.get(th.get("pressure") or "")
        kind = p.kind if p else th.get("kind", "")
        scale = threads.T["severity_scale"].get(th.get("severity", 2), 1.0)
        town = pulse.town_of(world, th["place"])
        if town not in world.places:
            continue
        dp = round(D.get("prices", {}).get(kind, 0) * scale)
        if dp and world.peoples_at(town) and not world.places[town].danger:
            row = lean.setdefault(("prices", town), {"kind": "prices", "place": town, "value": 0, "until": until, "cause": "drift", "thread": th["id"]})
            row["value"] += dp
        dd = round(D.get("danger", {}).get(kind, 0) * scale)
        if dd:
            wilds = [pid for pid in towns.town_places(world, town) if world.places[pid].danger] or ([th["place"]] if world.places[th["place"]].danger else [])
            for pid in wilds:
                row = lean.setdefault(("danger", pid), {"kind": "danger", "place": pid, "value": 0, "until": until, "cause": "drift", "thread": th["id"]})
                row["value"] += dd
    for row in lean.values():
        row["value"] = max(-cap, min(cap, row["value"]))
        state["effects"].append(row)
    return f"{len(lean)} places lean with the situations running" if lean else ""


# ---------- travellers: the trades that move

def travellers(store, world, state: dict, t: int, rng: random.Random) -> str:
    """Now and then a travelling trade the player has not met moves along the roads to a neighbouring town."""
    D = rules().get("travellers") or {}
    roles = D.get("roles") or []
    if not roles or rng.random() >= D.get("chance", 0.4):
        return ""
    from engine import pulse, threads
    log = state.setdefault("travelled", {})                   # npc id -> {"at": minute, "from": town}: the last move, so they go on, not back
    gap = D.get("every_days", 6) * 1440
    rows = [r for r in store.npc_rows(role=roles, gone=False, met_player=False) if t - (log.get(r.id) or {}).get("at", -10 ** 9) >= gap]
    rng.shuffle(rows)
    for r in rows[:5]:
        npc = store.load_npc(r.id)
        if npc.protected or npc.anchor or npc.concern_from:
            continue
        town = pulse.town_of(world, npc.location)
        if town not in world.places:
            continue
        came_from = (log.get(npc.id) or {}).get("from")
        options = [d for d in threads.neighbours_of(world, town) if d != town and d != came_from] or threads.neighbours_of(world, town)
        if not options:
            continue
        dest = rng.choice(options)
        pulse.move_npc(store, npc, dest)
        log[npc.id] = {"at": t, "from": town}
        for k in [k for k in log if not store.npc_exists(k)]:
            del log[k]
        console.debug(f"drift: {npc.name}, {npc.role}, has moved on to {world.places[dest].name}")
        return f"{npc.name} ({npc.role.replace('_', ' ')}) moved on to {world.places[dest].name}"
    return ""


# ---------- the player's standing: towns forget

def standing(store, state: dict, t: int, deltas: dict) -> str:
    """Standing nobody has moved for a while eases toward neutral: a delta per town and group for the scene to apply, with the day the
    record was last moved, so the clock on it is not reset by the easing itself."""
    D = rules().get("standing") or {}
    per_day = D.get("per_day", 0)
    if per_day <= 0 or not store.player_exists():
        return ""
    from engine import clock
    player = store.load_player()
    day = clock.day(t)
    after = D.get("after_days", 21)
    out = deltas.setdefault("standing", [])
    n = 0
    for town, groups in player.standing.items():
        for group, rec in groups.items():
            v, since = float(rec[0]), int(rec[1])
            if day - since < after or abs(v) < 0.05:
                continue
            already = sum(d for tn, g, d, _ in out if tn == town and g == group)
            left = v + already
            if abs(left) < 0.05:
                continue
            step = min(abs(left), per_day)
            out.append((town, group, -step if left > 0 else step, since))
            n += 1
    return f"{n} standings eased" if n else ""


def apply_player(player, deltas: dict) -> None:
    """The scene applies what a pass returned to the record it holds (f331)."""
    from engine import standing as st
    for town, group, delta, day in deltas.get("standing", []):
        st.add(player, town, group, delta, day)


def problems(trait_ids=()) -> list[str]:
    D = rules()
    bad = []
    if not D:
        return bad
    for k in ("every_hours", "most_passes", "people_per_pass", "relations", "moods", "motives", "situations", "standing"):
        if k not in D:
            bad.append(f"pulse.yaml drift: needs {k}")
    seeds = (D.get("motives") or {}).get("seeds") or {}
    if "default" not in seeds:
        bad.append("pulse.yaml drift.motives.seeds: needs default")
    for tr in seeds:
        if tr != "default" and trait_ids and tr not in trait_ids:
            bad.append(f"pulse.yaml drift.motives.seeds: '{tr}' is not a trait in data/traits.yaml")
    return bad
