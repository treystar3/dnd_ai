"""The pulse: the world moving on its own, away from the player.

Every few game hours the world pulses. Most pulses are quiet. An eventful one either moves a person's motive a
step forward, or starts a situation (a "thread") somewhere. Threads unfold in stages over time, then end - dealt
with by someone, or running their course and leaving their fallout. Everything mechanical goes through effects
the engine knows how to apply; everything else becomes history and news that people carry along the roads.

World state is the world_state row of the campaign's save (storage/campaign.py):
  last (minute of the last pulse), threads, news, history, effects, cooldowns, campaign (id of the running one), drift_last (f331).

Who writes a situation (f331): the ordinary tiers (pulse.yaml tiers engine: true) are built by the engine from data/rules/threads.yaml
with no model call, complete at birth, and re-told in the world's words when the player comes where they are (engine/threads.py); the
rare and campaign tiers are the model's. Between pulses the drift (engine/drift.py) settles what they left.
"""

import random
import uuid
from pathlib import Path

import yaml

from engine import clock, events, pulselog
from engine import pulse_prompts as pp
from llm.contracts import MotiveStep, ThreadProposal
from llm.gateway import LLMError, generate
from ui import console

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "pulse.yaml").read_text(encoding="utf-8"))
INTERVAL = P["interval_hours"] * 60


def empty_state(now: int) -> dict:
    return {"last": now, "threads": [], "news": [], "history": [], "effects": [], "cooldowns": {}, "campaign": "",
            "deeds": [], "spawns": [], "camps": [], "vacancies": {}, "player_events": [], "cataclysms": 0, "cataclysm_end": 0, "drift_last": now}


# ---------- reading the world's state ----------

def active_effects(state: dict, now: int, kind: str, place: str) -> list[dict]:
    return [e for e in state.get("effects", []) if e["kind"] == kind and e["place"] == place and e["until"] > now]


def known(world, place_id) -> bool:
    """A real place of the world - not a stop on the road, which exists only while the player stands on it."""
    p = world.places.get(place_id or "")
    return bool(p) and p.type != "road"


def home_town(world, place_id: str) -> str:
    """(f366) The town the pulse measures from: a place's town, or for a road made for one journey (type road, no parent) the end it is
    nearer. A night run's player was on such roads at three ticks in a row, and each tick tried to start a situation at the road itself,
    which no template fits."""
    p = world.places.get(place_id)
    if p is not None and p.type == "road" and not p.parent and p.connects:
        return town_of(world, min(p.connects, key=lambda k: p.connects[k]))
    return town_of(world, place_id)


def town_of(world, place_id: str) -> str:
    """The settlement a place belongs to (its top parent), or the place itself."""
    p = world.places.get(place_id)
    while p and p.parent and p.parent in world.places:
        p = world.places[p.parent]
    return p.id if p else place_id


def price_factor(store, world, place_id: str, now: int) -> float:
    town = town_of(world, place_id)
    state = store.load_world_state()
    return 1 + sum(e["value"] for e in active_effects(state, now, "prices", town)) / 100


def danger_factor(store, place_id: str, now: int) -> float:
    state = store.load_world_state()
    return max(0.0, 1 + sum(e["value"] for e in active_effects(state, now, "danger", place_id)) / 100)


def closed_reason(store, place_id: str, now: int) -> str:
    """Why the way through a place is shut to the player now, or ''. (f386) Never a barring the player made themselves: they barred it
    against others, and can unbar it (a night's run was shut out of the guild house for twenty turns by its own leaning on a wall)."""
    state = store.load_world_state()
    hits = [e for e in active_effects(state, now, "closed", place_id) if e.get("cause") != "improvised"]
    return hits[0]["text"] if hits else ""


def closed_until(store, place_id: str, now: int) -> int:
    """(f390) The minute the way through this place opens again (the last closure on it to lift), or 0 when it is open."""
    state = store.load_world_state()
    return max((e["until"] for e in active_effects(state, now, "closed", place_id) if e.get("cause") != "improvised"), default=0)


def way_out(world, here: str) -> set[str]:
    """(f390) The places a closure cannot bar to someone standing at `here`: the place itself, every place it lies within, and the one a
    dead end opens onto (a dungeon's mouth opens only onto the wild above it). A closure stops people going in; it never shuts in whoever
    is already there. A night's run spent four hours at the mouth of a mine whose only way out was a wild a world event had closed."""
    out = set()
    p = world.places.get(here)
    while p is not None and p.id not in out:
        out.add(p.id)
        links = list(getattr(p, "connects", None) or {})
        if len(links) == 1:
            out.add(links[0])
        p = world.places.get(p.parent) if p.parent else None
    return out


def happenings_at(store, world, place_id: str, now: int) -> list[str]:
    """What can be seen of the world's situations here right now."""
    state = store.load_world_state()
    town = town_of(world, place_id)
    out = []
    from engine import threads
    for t in state.get("threads", []):
        if t["status"] == "active" and (t["place"] in (place_id, town) or (t.get("town") and t["town"] == town)):   # (f357) a threat at the wild is about its town
            out.append(t["stages"][t["stage"]]["description"])
            since = t["times"][t["stage"]] if t.get("times") and t["stage"] < len(t["times"]) else t.get("made", now)
            sign = threads.signs_for(t, (now - since) // 1440)                                # (f356) on its second day and after, a sign in turn
            if sign:
                out.append(sign)
    for e in state.get("effects", []):
        if e["kind"] == "closed" and e["place"] == place_id and e["until"] > now:
            out.append(f"The player has barred the way here themselves, and can unbar it: {e['text']}" if e.get("cause") == "improvised"
                       else f"The way is closed: {e['text']}")                                # (f386) theirs, said as theirs
    return out


def news_window(state: dict, world, place_id: str, now: int, limit: int = 8, key: str = "", groups: set | None = None) -> list[dict]:
    """(f356) The news to show at this place now: the newest two that have reached it, then a draw by freshness (and this town's own
    news first) among the rest, seeded by the day and `key` so the window turns over each day and differs between speakers, instead of
    the same five newest lines for a day or more. `groups`: only news those circles carry."""
    keep = P["news"]["keep_days"] * 1440
    reached = [n for n in state.get("news", []) if now - n["minute"] <= keep and (groups is None or set(n["groups"]) & groups)
               and n["minute"] + travel_delay(world, n["origin"], place_id) <= now]
    if len(reached) <= limit:
        return list(reversed(reached))
    newest = reached[-2:]
    rest = reached[:-2]
    town = town_of(world, place_id)
    rng = random.Random(f"{key}:news:{place_id}:{clock.day(now)}")
    picked = []
    pool = list(rest)
    while pool and len(picked) < limit - 2:
        weights = [(1.0 / (1 + (now - n["minute"]) / 1440)) * (1.5 if town_of(world, n["origin"]) == town else 1.0) for n in pool]
        n = rng.choices(pool, weights=weights)[0]
        picked.append(n)
        pool.remove(n)
    return list(reversed(newest)) + sorted(picked, key=lambda n: -n["minute"])


def news_for(store, world, npc, now: int, limit: int = 5) -> list[str]:
    """News this person has heard: it must have reached where they are, and be news their circles would carry; the window turns over
    by the day (news_window)."""
    state = store.load_world_state()
    groups = set(npc.knowledge_groups) | {"everyone"}
    return [news_text(n, now) for n in news_window(state, world, npc.location, now, limit, key=f"{store.meta.seed}:{getattr(npc, 'id', 'here')}", groups=groups)]


def travel_delay(world, origin: str, where: str) -> int:
    if origin not in world.places or where not in world.places:
        return 0
    if origin == where or town_of(world, origin) == town_of(world, where):
        return 0
    found = world.path(origin, where)
    if not found:
        return 10 ** 9
    return round(found[1] * P["news"]["hours_per_walking_hour"])


def within_reach(store, world, state: dict, t: int) -> list[dict]:
    """(f354) The live situations at the player's town or within near_minutes' walk of it."""
    if not store.player_exists():
        return []
    here = home_town(world, store.load_player().location)
    if here not in world.places:
        return []
    PL = P.get("placement", {})
    dist = events.distances(world, here)
    near = {p.id for p in world.places.values() if not p.parent and dist.get(p.id, 10 ** 9) <= PL.get("near_minutes", 600)} | {here}
    return [th for th in state.get("threads", []) if th["status"] == "active" and (th["place"] in near or town_of(world, th["place"]) in near)]


def engine_roll(store, world, catalog, state: dict, t: int, rng: random.Random) -> bool:
    """(f354) The engine's own situation within reach of the player this tick: by the roll, or after a quiet day, never past most_live."""
    ER = P.get("engine_roll") or {}
    if not ER:
        return False
    live = within_reach(store, world, state, t)
    if live:
        state.pop("reach_quiet_since", None)
    else:
        state.setdefault("reach_quiet_since", t)
    quiet = not live and t - state.get("reach_quiet_since", t) >= ER.get("quiet_hours", 24) * 60
    roll = rng.random()
    if len(live) >= ER.get("most_live", 2) or not (quiet or roll < float(ER.get("chance", 0.4))):
        return False
    LAST["made_by"] = ""
    if start_thread(store, world, catalog, state, t, rng, made_by="engine", band_weights=ER.get("bands")):
        state.pop("reach_quiet_since", None)
        return True
    return False


# ---------- the clock ----------

def catch_up(store, world, catalog, now: int) -> dict:
    """Run every pulse between the last one and now. Timers always run; new events are capped per call. Then the drift (engine/drift.py,
    f331) settles what the pulses left, on its own clock; what it owes the player's record is returned for the scene to apply."""
    state = store.load_world_state() or empty_state(now)
    if "last" not in state:
        state["last"] = now
    budget = P["max_new_events_per_action"]                             # model calls the pulse may make while the player does one thing
    engine_budget = P.get("max_engine_events_per_action", 8)            # (f353) the engine's own situations cost no call: a looser cap of their own
    rng = random.Random(f"{store.meta.seed}:pulse:{state['last']}")
    changed = False
    while state["last"] + INTERVAL <= now:
        state["last"] += INTERVAL
        t = state["last"]
        pulselog.begin(t)
        changed |= tick_threads(store, world, catalog, state, t, rng)
        if state.get("camps"):
            events.expire_camps(store, world, state, t)
        if engine_budget > 0 and start_queued(store, world, catalog, state, t, rng):          # (f358) what follows from an ending
            engine_budget -= 1
            changed = True
        from engine import consequences
        if engine_budget > 0 and consequences.tick(store, world, catalog, state, t, rng):    # (f359) the town answers the stranger's deeds
            engine_budget -= 1
            changed = True
        if engine_budget > 0 and engine_roll(store, world, catalog, state, t, rng):          # (f354) the engine's own, within reach
            engine_budget -= 1
            changed = True
        if budget <= 0 and engine_budget <= 0:
            continue
        # one big-event slot (a campaign, or at high level a cataclysm) opens now and then; one at a time
        slot_chance = P["interval_hours"] / (events.E["campaign"]["every_days"] * 24)
        if not state.get("campaign") and rng.random() < slot_chance and budget > 0:
            done = False
            if events.cataclysm_due(state, t, events.player_level(store), rng):
                done = events.start_cataclysm(store, world, catalog, state, t, rng)
            if not done:
                done = start_thread(store, world, catalog, state, t, rng, tier="campaign")
            if done:
                budget -= 1
                changed = True
            continue
        if rng.random() >= P["eventful_chance"]:
            continue
        kind = rng.choices(list(P["kinds"]), weights=list(P["kinds"].values()))[0]
        if kind == "motive":
            from engine import motives
            engine_made = bool(motives.M.get("engine", True))
            if (budget <= 0 and not engine_made) or (engine_budget <= 0 and engine_made):
                continue
            done = move_motive(store, world, catalog, state, t, rng)
            if done and engine_made:
                engine_budget -= 1
            elif done:
                budget -= 1
        else:
            LAST["made_by"] = ""
            done = start_thread(store, world, catalog, state, t, rng, allow=(budget > 0, engine_budget > 0))
            if done and LAST["made_by"] == "engine":
                engine_budget -= 1
            elif done:
                budget -= 1
        if done:
            changed = True
    from engine import drift
    deltas = drift.catch_up(store, world, state, now, random.Random(f"{store.meta.seed}:drift:{state.get('drift_last', now)}"))
    pulselog.close()
    store.save_world_state(state)
    return deltas


FINISHED_KEPT = 30
LAST = {"made_by": ""}            # who made the situation start_thread started last: 'engine' or 'model' (read by catch_up for the budget)


# ---------- threads ----------

def thread_row_text(tier: str, engine: bool, title: str, place_name: str, days: int, stages: int) -> str:
    """The world log's line for a situation starting: the place named once (most engine titles already carry it)."""
    where = "" if place_name.lower() in title.lower() else f" at {place_name}"
    return f"[{tier}{', engine-built' if engine else ''}] {title}{where} - starts, {days} days, {stages} stages"


def start_thread(store, world, catalog, state, t, rng, tier: str | None = None, pressure_id: str = "", place_id: str = "", made_by: str = "",
                 allow: tuple[bool, bool] = (True, True), band_weights: dict | None = None, template: str = "", severity_shift: int = 0,
                 pressure=None, door: str = "") -> bool:
    """Start a situation. pressure_id / place_id force the seed and the place (used by tools/pulse_preview.py). made_by forces who writes it:
    'engine' (data/rules/threads.yaml) or 'model'; by default the tier decides (pulse.yaml tiers engine: true), and a tier the model writes
    falls back to the engine's own when the model gives nothing usable (f331). allow (f353): (the model may be called, the engine may build),
    from the two budgets; a tier whose maker is not allowed this action does not start (a model tier falls back to the engine when it may)."""
    plain = [k for k in P["tiers"] if k not in ("campaign", "cataclysm")]
    tier = tier or rng.choices(plain, weights=[P["tiers"][k]["weight"] for k in plain])[0]
    rule = P["tiers"][tier]
    may_model, may_engine = allow
    if not made_by:
        if rule.get("engine") and not may_engine:
            return False
        if not rule.get("engine") and not may_model:
            if rule.get("fallback") == "engine" and may_engine:
                made_by = "engine"
            else:
                return False
    cooldown = P["pressure_cooldown_days"] * 1440
    pressures = [p for p in world.pressures.values() if t - state["cooldowns"].get(p.id, -10 ** 9) > cooldown]
    if tier == "campaign" and events.E["campaign"]["prefer_marked"]:
        marked = [p for p in pressures if p.campaign]
        pressures = marked or pressures
    if pressure is not None:                                         # (f359) a pressure-shaped record of the engine's own (a consequence of the player's deeds)
        place = world.places.get(pressure.place)
        template = template or pressure.template
    elif pressure_id:
        pressure = world.pressures[pressure_id]
        place = world.places.get(pressure.place) or region_town(world, pressure.place, rng)
    elif place_id:
        here = [p for p in pressures if p.place == place_id]
        pressure = rng.choices(here, weights=[p.weight for p in here])[0] if here else None
        place = world.places.get(place_id)
    elif tier == "campaign" and pressures:
        pressure, place = place_by_band(store, world, pressures, rng, must_pressure=True)      # (f324) a campaign near the player, falling outward
    else:
        pressure, place = place_by_band(store, world, pressures, rng, band_weights=band_weights)   # (f323) mostly where the player is, sometimes anywhere
    if not place:
        return False
    big = tier in events.BIG
    thread_id = uuid.uuid4().hex[:8]
    from engine import threads, truth
    proposal, info = None, None
    engine_made = made_by == "engine" or (not made_by and rule.get("engine"))
    if not engine_made:
        system = pp.THREAD_SYSTEM + (pp.BIG_EXTRA if big else "")
        extra = ""
        if big:
            extra = f"\nPLAYER LEVEL: {events.player_level(store)}"
        try:
            proposal = generate(
                "pulse_thread", system,
                f"TIER: {tier}\nSTAGES: {rule['stages']}\n" + context_for_place(store, world, catalog, state, place, t, big=big) + extra,
                ThreadProposal, temperature=0.95, max_tokens=2400 if big else 1800,
                validation_context={"stages": rule["stages"], "known": truth.world_words(world)},      # (f323) nothing named that the world does not have
            )
        except LLMError as e:
            if rule.get("fallback") != "engine" or made_by == "model":
                console.debug(f"pulse: no situation this time ({e})")
                pulselog.note("miss", f"tried to start a {tier} situation at {place.name}: the model gave nothing usable ({e})")
                return False
            console.debug(f"pulse: the model gave nothing usable ({e}); the engine builds the situation itself")
    if proposal is None:                                             # (f331) the engine's own
        built = threads.build(store, world, state, place, pressure, tier, rng, t, template=template, severity_shift=severity_shift)
        if not built:
            pulselog.note("miss", f"tried to start a {tier} situation at {place.name}: no template fits the place")
            return False
        proposal, info = built
    if not known(world, proposal.place):
        proposal.place = place.id
    if not known(world, proposal.place):                             # (f376) a stop on the road is gone once the player walks on: a situation
        proposal.place = home_town(world, proposal.place)            # placed there broke the world's tick when it ended, every turn after
        if not known(world, proposal.place):
            return False
    days = rng.randint(*rule["days"])
    span = days * 1440
    times = [t + round(span * i / rule["stages"]) for i in range(rule["stages"])] + [t + span]
    thread = {"id": thread_id, "title": proposal.title, "tier": tier, "place": proposal.place, "kind": proposal.kind,
              "pressure": pressure.id if pressure else "", "stage": 0, "times": times, "status": "active",
              "stages": [s.model_dump() for s in proposal.stages], "fallout": proposal.fallout.model_dump(),
              "resolution": proposal.resolution, "made": t,
              "groups": [g for g in proposal.groups if g in world.knowledge_groups] or ["everyone"],
              "reward_hint": list(pressure.reward) if pressure else [], "paths": [], "scope_places": [],
              "triumph": proposal.triumph.model_dump() if proposal.triumph else None,
              "boss_lines": proposal.boss_lines.model_dump(exclude={"captain_intro"}) if proposal.boss_lines and tier == "campaign" else None,
              "made_by": "engine" if info else "model", "told": not info}                 # (f331) who wrote it; an engine-built one is re-told when met
    LAST["made_by"] = thread["made_by"]
    if info:
        thread.update(template=info["template"], severity=info["severity"], words=info["words"], streets=info.get("streets") or [],   # (f357)
                      town=(info.get("ids") or {}).get("town", ""))                               # the town it is about (a threat sits at the wild)
        if thread["town"] and not known(world, thread["town"]):                                    # (f376) never a stop on the road
            thread["town"] = town_of(world, proposal.place)
    thread["contract"] = proposal.contract.model_dump() if proposal.contract and proposal.contract.what else None
    state["threads"].append(thread)
    if pressure and pressure.id in world.pressures:
        state["cooldowns"][pressure.id] = t
    if tier == "campaign":
        state["campaign"] = thread["id"]
    add_news(state, proposal.news, proposal.place, t, thread["groups"], thread=thread_id)
    here = home_town(world, store.load_player().location) if store.player_exists() else ""
    row = pulselog.note("thread", thread_row_text(tier, bool(info), proposal.title, world.places[proposal.place].name, days, rule["stages"]),
                        tier=tier, place=proposal.place, town=town_of(world, proposal.place), made_by=thread["made_by"], here=here,
                        reach=any(x["id"] == thread_id for x in within_reach(store, world, state, t)))
    apply_effects(store, world, catalog, state, proposal.stages[0].effects, tier, t, thread["title"], thread_id=thread_id, row=row)
    from engine import matters                                      # (f317) the door the player meets it through, and what it carries
    reputation = store.load_player().reputation.get(town_of(world, proposal.place), 0) if store.player_exists() else 0
    matters.attach(store, world, state, thread, proposal, reputation, rng, t, door=door)
    posted = False
    if thread["contract"] and thread["door"] in ("board", "board_more"):
        posted = post_contract(store, world, proposal.contract, thread, t, plain=thread["hidden"])
    thread["posted"] = posted
    thread["paths"] = events.build_paths(store, world, state, proposal.paths, thread, posted and not thread["hidden"])
    if big and not thread["paths"]:                                  # a big event the model left with no checkable way to end it gets one
        events.ensure_a_way(store, world, state, thread, t, rng)
    if big:
        thread["scope_places"] = sorted({e.place for st in proposal.stages for e in st.effects if e.place in world.places})
    console.debug(f"pulse: [{tier}] {proposal.title} at {proposal.place}")
    return True


def start_campaign_for(store, world, catalog, state, t, rng, town: str, door: str = "") -> bool:
    """(f363) A campaign earned by play: of the scenarios not on cooldown, the marked ones first (events.yaml prefer_marked), those of the
    player's own region first and the nearest of those, written by the model as every campaign is, through the door given. False when
    none can start (nothing to draw, or the model gave nothing usable: a campaign has no engine fallback)."""
    if town not in world.places:
        return False
    cooldown = P["pressure_cooldown_days"] * 1440
    pressures = [p for p in world.pressures.values() if t - state["cooldowns"].get(p.id, -10 ** 9) > cooldown]
    marked = [p for p in pressures if p.campaign] or pressures
    if not marked:
        return False
    region = world.places[town].region

    def place_of(p) -> str:
        if p.place in world.places:
            return p.place
        rt = region_town(world, p.place, rng) if p.place in world.regions else None
        return rt.id if rt else ""

    def dist(p) -> int:
        pid = place_of(p)
        found = world.path(town, pid) if pid and pid != town else (([town], 0) if pid == town else None)
        return found[1] if found else 10 ** 9
    mine = [p for p in marked if (p.place in world.places and world.places[p.place].region == region) or p.place == region]
    best = min(mine or marked, key=dist)
    return start_thread(store, world, catalog, state, t, rng, tier="campaign", pressure_id=best.id, door=door)


def place_by_band(store, world, pressures: list, rng: random.Random, must_pressure: bool = False, band_weights: dict | None = None):
    """(f323) Where a new situation goes: a band drawn by pulse.yaml placement - the player's own town, its neighbours, its region, or
    anywhere - then a pressure in that band when there is one (most of the time), else one of its towns. The world keeps moving where
    nobody watches, but the calls the player waits through are mostly ones they will meet. must_pressure (a campaign, f324): the band
    must hold a pressure, else the next band out is tried, so the biggest events are the likeliest to be met."""
    PL = P.get("placement", {})
    towns = [p for p in world.places.values() if not p.parent and p.type not in ("dungeon", "road") and known(world, p.id) and not p.danger]
    here = home_town(world, store.load_player().location) if store.player_exists() else ""
    if here not in world.places or not PL:
        pressure = rng.choices(pressures, weights=[p.weight for p in pressures])[0] if pressures and rng.random() < 0.75 else None
        return pressure, (world.places.get(pressure.place) or region_town(world, pressure.place, rng)) if pressure else rng.choice(towns)
    dist = events.distances(world, here)
    region = world.places[here].region
    bands = {"here": [here],
             "near": [p.id for p in towns if p.id != here and dist.get(p.id, 10 ** 9) <= PL.get("near_minutes", 600)],
             "region": [p.id for p in towns if p.id != here and p.region == region and dist.get(p.id, 10 ** 9) > PL.get("near_minutes", 600)],
             "far": [p.id for p in towns if p.id != here and p.region != region and dist.get(p.id, 10 ** 9) > PL.get("near_minutes", 600)]}
    weights = {b: (band_weights or PL["bands"]).get(b, 0) for b in bands if bands[b]}
    weights = {b: w for b, w in weights.items() if w > 0} or {b: PL["bands"].get(b, 0) for b in bands if bands[b]}   # (f354) the engine's own bands
    band = rng.choices(list(weights), weights=list(weights.values()))[0]
    order = ["here", "near", "region", "far"]
    ids = set(bands[band])
    regions = {world.places[i].region for i in ids}
    in_band = lambda ids_, regs_: [pr for pr in pressures if pr.place in ids_ or town_of(world, pr.place) in ids_ or (pr.place in world.regions and pr.place in regs_)]
    mine = in_band(ids, regions)
    if must_pressure:
        for b in order[order.index(band):] + order[:order.index(band)]:
            ids_b = set(bands[b])
            mine = in_band(ids_b, {world.places[i].region for i in ids_b})
            if mine:
                ids, regions = ids_b, {world.places[i].region for i in ids_b}
                break
        if not mine:
            mine = list(pressures)
    if mine and (must_pressure or rng.random() < PL.get("pressure_share", 0.75)):
        pressure = rng.choices(mine, weights=[pr.weight for pr in mine])[0]
        place = world.places.get(pressure.place) or region_town(world, pressure.place, rng)
        if place is not None and town_of(world, place.id) not in ids and place.id not in ids:
            place = world.places[rng.choice(sorted(ids))]
        return pressure, place
    return None, world.places[rng.choice(sorted(ids))]


def region_town(world, region_id: str, rng):
    """A scenario aimed at a whole region lands in one of its settlements."""
    if region_id not in world.regions:
        return None
    towns = [p for p in world.places.values() if p.region == region_id and not p.parent and not p.danger
             and p.type not in ("dungeon", "road", "home")]
    return rng.choice(towns) if towns else None


def start_queued(store, world, catalog, state: dict, t: int, rng: random.Random) -> bool:
    """(f358) A follow-on whose delay has run starts now, at its place, from its template, with its severity shift (and the pressure's heat)."""
    due = [q for q in state.get("queued", []) if q.get("after", 0) <= t]
    if not due:
        return False
    q = due[0]
    state["queued"] = [x for x in state.get("queued", []) if x is not q]
    LAST["made_by"] = ""
    ok = start_thread(store, world, catalog, state, t, rng, tier=q.get("tier") if q.get("tier") in P["tiers"] and q.get("tier") not in events.BIG else None,
                      pressure_id=q.get("pressure") or "", place_id="" if q.get("pressure") else q.get("place", ""), made_by="engine",
                      template=q.get("template", ""), severity_shift=int(q.get("severity", 0)))
    if ok and state.get("threads"):
        state["threads"][-1]["follows"] = q.get("from", "")
        pulselog.note("chain", f"{state['threads'][-1]['title']} follows from {q.get('from', '')}", place=q.get("place", ""))
    return ok


def tick_threads(store, world, catalog, state, t, rng) -> bool:
    changed = False
    from engine import matters, threads
    for th in [x for x in state["threads"] if x["status"] == "active"]:
        if th.get("door") and matters.reopen(store, world, state, th, t):
            changed = True
        while th["status"] == "active" and th["stage"] + 1 < len(th["stages"]) and t >= th["times"][th["stage"] + 1]:
            th["stage"] += 1
            stage = th["stages"][th["stage"]]
            row = pulselog.note("stage", f"{th['title']} - stage {th['stage'] + 1}/{len(th['stages'])}: {stage['description'][:140]}", place=th["place"])
            apply_effects(store, world, catalog, state, stage["effects"], th["tier"], t, th["title"], raw=True, thread_id=th["id"], row=row)
            add_news(state, stage["description"], th["place"], t, th["groups"], thread=th["id"])
            if th["tier"] == "cataclysm":
                events.on_stage(store, world, catalog, state, th, t, rng)
            elif th["tier"] in events.BIG:
                events.sync_paths(state, th)
            changed = True
        if th["status"] == "active" and t >= th["times"][-1]:
            if rng.random() < P["tiers"][th["tier"]]["resolved_by_others"]:
                who = resolver(store, world, th, rng)
                pulselog.note("end", f"{th['title']} - settled by {who}", how="settled", place=th["place"], tier=th["tier"])
                end_thread(store, state, th, "resolved", f"{th['title']} - settled by {who}.", t)
                th["result"] = "others"
                threads.follow_up(state, th, "settled", rng, t)                                 # (f358) what may come of it
                matters.town_note(store, world, th["place"], f"{th['title']}: settled by {who}", t)       # (f323) the town's own history
            else:
                fall = th["fallout"]
                row = pulselog.note("end", f"{th['title']} - left alone, so the fallout lands: {fall['description'][:140]}", how="ignored", place=th["place"], tier=th["tier"])
                end_thread(store, state, th, "ended", f"{th['title']} - {fall['description']}", t)        # lifts what the stages laid...
                apply_effects(store, world, catalog, state, fall["effects"], th["tier"], t, th["title"], raw=True, thread_id=th["id"], row=row)   # ...and the fallout stays
                th["result"] = "ignored"
                threads.follow_up(state, th, "ignored", rng, t)                                 # (f358) ignored, it may get worse
                if (th.get("summons") == "met" or th.get("answered")) and store.player_exists():      # (f317) they were asked, and let it be
                    pl = store.load_player()
                    matters.remember(store, world, th, "ignored", pl.character.name, t, store.meta.turn)
                if th["tier"] == "cataclysm":
                    events.after_ignored(store, world, state, th, t)
            if th["tier"] == "cataclysm":
                state["cataclysm_end"] = t
            changed = True
    return changed


def resolver(store, world, th, rng) -> str:
    """Who dealt with it, off-screen: one of the town's anchors when one fits (f323), a guild contractor sometimes, else the watch or
    the people. Whoever it was remembers it, and so does the town."""
    from engine import retrieval
    from npc.models import Memory
    town = town_of(world, th["place"])
    anchors = [n for n in store.load_npcs([r.id for r in retrieval.people_in_town(store, world, town)]) if n.anchor]
    if anchors and rng.random() < P.get("anchor_settles", 0.5):
        n = rng.choice(anchors)
        n.memories.append(Memory(day=clock.day(th["times"][-1]), turn=-1, text=f"I dealt with {th['title'].lower()} myself, in the end.", importance=2))
        store.save_npc(n)
        return f"{n.name}, the {n.role.replace('_', ' ')}"
    if rng.random() < 0.4:
        for n in store.load_npcs([r.id for r in store.npc_rows(role="guild_contractor", gone=False)][:1]):     # the first, as before
            n.mood = rng.choice([f"proud, after settling {th['title'].lower()}",
                                 f"nursing a fresh wound from {th['title'].lower()}",
                                 f"flush with coin from {th['title'].lower()}"])
            store.save_npc(n)
            return f"{n.name}, a guild contractor"
    place = world.places.get(th["place"])
    if place is None:                                                # (f376) a place that is gone (an old save's stop on the road)
        return "the people thereabouts"
    return "the watch" if place.residents.get("guard") or place.residents.get("watch_captain") else \
        f"the people of {place.name}"


def lift(state: dict, th: dict, t: int) -> None:
    """What a situation laid on the world goes with it when it ends, however it ends: its danger, closures and prices end now, its
    creatures stop appearing, its camps break up within two days. By the thread's id (f331); by title for effects from before ids were
    kept. Called by end_thread, so a thread settled by others or left to run out is lifted like one the player ended (events.finish)."""
    for e in state.get("effects", []):
        mine = e.get("thread") == th["id"] if e.get("thread") else e.get("cause") == th["title"]
        if mine and e["kind"] in ("danger", "closed", "prices"):
            e["until"] = min(e["until"], t)
    for s in state.get("spawns", []):
        if s.get("thread") == th["id"]:
            s["defeated"] = True
    for camp in state.get("camps", []):
        if camp.get("thread") == th["id"]:
            camp["until"] = min(camp["until"], t + 2 * 1440)


def end_thread(store, state, th, status: str, line: str, t: int) -> None:
    lift(state, th, t)
    th["status"] = status
    th["ended_at"] = t
    if state.get("campaign") == th["id"]:
        state["campaign"] = ""
    state["history"].append({"minute": t, "text": line, "place": th["place"]})
    state["history"] = state["history"][-200:]
    done = sorted([x for x in state.get("threads", []) if x["status"] != "active"], key=lambda x: x.get("ended_at", x.get("made", 0)))
    if len(done) > FINISHED_KEPT:                     # the finished records kept are the ones that ended last - never the one ending now,
        drop = {x["id"] for x in done[:-FINISHED_KEPT]}   # which used to be first out when it was the oldest made (a cataclysm, every time)
        state["threads"] = [x for x in state["threads"] if x["id"] not in drop]
    add_news(state, line, th["place"], t, th["groups"], thread=th["id"])


def post_contract(store, world, offer, thread, t, plain: bool = False) -> bool:
    """plain (f317): the posting reads as an ordinary job, with nothing in the title to say what is behind it."""
    from engine import quests
    halls = [p.id for p in world.places.values() if p.type == "guild"]
    if not halls:
        return False
    where = thread.get("place")
    near = [(world.path(h, where)[1], h) for h in halls if where in world.places and world.path(h, where)]
    gid = min(near)[1] if near else halls[0]
    q = quests.map_offer(world, store, offer, "guild", "the guild", t, guild=True)
    if not q:
        return False
    q["thread"] = thread["id"]
    if not plain:
        q["title"] = f"{q['title']} ({thread['title']})"
    q["multiplier"] = q.get("multiplier", 1) * events.pulse_mult(thread["tier"])
    gs = store.load_place(gid)
    gs.board.append(q)
    store.save_place(gs)
    return True


# ---------- motives ----------

def move_motive(store, world, catalog, state, t, rng) -> bool:
    gap = P["motives"]["step_days"] * 1440
    last = state.setdefault("motive_last", {})
    movers = store.load_npcs([r.id for r in store.npc_rows(not_tier="background", motive=True, gone=False)
                              if known(world, r.location) and t - last.get(r.id, -10 ** 9) >= gap])
    if not movers:
        return False
    npc = rng.choice(movers)
    from engine import motives
    if motives.M.get("engine", True):                                   # (f360) the engine's own step: no call
        last[npc.id] = t
        return motives.move(store, world, state, npc, t, rng)
    place = world.places[npc.location]
    request = (f"PERSON: {npc.id} - {npc.name}, {npc.people} {npc.role.replace('_', ' ')}\n"
               f"PERSONALITY: {npc.personality}\nTRAITS: {', '.join(npc.traits)}\nWORRY: {npc.concern}\n"
               f"MOTIVE: {npc.motive}\nMOOD LATELY: {npc.mood or 'ordinary'}\n"
               f"FEELINGS ABOUT OTHERS: {relations_text(store, npc) or 'nothing strong'}\n"
               + context_for_place(store, world, catalog, state, place, t))
    try:
        step = generate("pulse_motive", pp.MOTIVE_SYSTEM, request, MotiveStep, temperature=0.9, max_tokens=900)
    except LLMError as e:
        console.debug(f"pulse: {npc.name}'s life holds still ({e})")
        return False
    last[npc.id] = t
    row = pulselog.note("motive", f"{npc.name}: {step.happened} [{step.status}]", place=npc.location)
    apply_effects(store, world, catalog, state, step.effects, "normal", t, f"{npc.name}'s doings", row=row)
    npc = store.load_npc(npc.id)
    npc.motive = (step.next_motive.strip() or npc.motive) if step.status == "continuing" else ""
    if step.status != "continuing":
        npc.motive_done_at = t                                      # (f331) after a while a new one may take hold (engine/drift.py)
    from npc.models import Memory
    npc.memories.append(Memory(day=clock.day(t), turn=-1, text=f"(my own life) {step.happened}"))
    store.save_npc(npc)
    if step.gossip.strip():
        add_news(state, step.gossip.strip(), npc.location, t, [world.locals_group(npc.location) or "everyone"])
    state["history"].append({"minute": t, "text": f"{npc.name}: {step.happened}", "place": npc.location})
    console.debug(f"pulse: {npc.name} - {step.happened} [{step.status}]")
    return True


def relations_text(store, npc) -> str:
    parts = []
    for oid, r in npc.relations.items():
        if store.npc_exists(oid):
            parts.append(f"{store.load_npc(oid).name} ({r['score']:+d}: {r['feeling']})")
    return "; ".join(parts)


# ---------- effects ----------

def apply_effects(store, world, catalog, state, effects, tier: str, t: int, cause: str, raw: bool = False,
                  thread_id: str = "", row: dict | None = None) -> None:
    for e in effects:
        e = e if raw else e.model_dump()
        result = "applied"
        try:
            if e["kind"] in ("spawn", "camp", "seal"):
                events.apply_big(store, world, catalog, state, e, tier, t, cause, thread_id)
            else:
                result = apply_one(store, world, catalog, state, e, tier, t, cause, thread_id) or "applied"
        except Exception as err:  # an effect the world can't honor is simply dropped
            console.debug(f"pulse: dropped effect {e.get('kind')} ({err})")
            result = f"dropped: {err}"
        if row is not None:
            try:
                pulselog.effect(row, pulselog.describe(e, store, world), result)
            except Exception:
                pass


def apply_one(store, world, catalog, state, e: dict, tier: str, t: int, cause: str, thread_id: str = "") -> str:
    """Apply one effect. Returns what happened, in words, for the debug log. A lasting effect (prices, danger, closed) is recorded with
    the thread that made it (f331), so ending the thread lifts exactly its own."""
    kind, lim = e["kind"], P["effects"]
    days = max(1, min(lim["max_days"], e.get("days") or 3))
    npc = store.load_npc(e["npc"]) if e.get("npc") and store.npc_exists(e["npc"]) else None
    if npc and npc.gone:
        return "skipped: they are already gone"
    if kind == "relation" and npc and e.get("other") and store.npc_exists(e["other"]):
        r = npc.relations.get(e["other"], {"score": 0, "feeling": ""})
        r["score"] = max(-100, min(100, r["score"] + max(lim["relation"]["min"], min(lim["relation"]["max"], e["value"]))))
        r["feeling"] = e.get("text") or r["feeling"]
        r["since"] = t                                               # (f331) feelings nobody stirs ease with time (engine/drift.py)
        npc.relations[e["other"]] = r
        store.save_npc(npc)
    elif kind == "mood" and npc and e.get("text"):
        npc.mood = e["text"]
        npc.mood_until = t + P.get("drift", {}).get("moods", {}).get("days", 6) * 1440      # (f331) a mood the world gave fades
        store.save_npc(npc)
    elif kind == "move" and npc and known(world, e.get("place")):
        if world.places[e["place"]].danger or not world.peoples_at(e["place"]):
            return "skipped: a dangerous or empty place"
        move_npc(store, npc, e["place"])
    elif kind == "leave" and npc:
        met = npc.tier != "background"
        if npc.protected or npc.role in P["protected_roles"] or (met and tier not in P["may_remove_met"]):
            return "skipped: they are protected"
        remove_npc(store, world, npc, e.get("text") or "gone away", t)
    elif kind == "arrive" and known(world, e.get("place")) and e.get("role") in world.roles:
        if world.places[e["place"]].danger or not world.peoples_at(e["place"]):
            return "skipped: a dangerous or empty place"
        ps = store.load_place(e["place"])
        ps.extra_roles[e["role"]] = ps.extra_roles.get(e["role"], 0) + 1
        store.save_place(ps)
    elif kind == "trait" and npc and catalog and tier in P["may_change_traits"]:
        from npc.traits import change_trait
        if e.get("remove") in npc.traits and e.get("add") in catalog.traits and e["add"] not in npc.traits:
            change_trait(npc, catalog, e["remove"], e["add"], cause, clock.day(t))
            store.save_npc(npc)
    elif kind in ("prices", "danger") and (known(world, e.get("place")) or (kind == "danger" and e.get("place") in world.roads)):
        lo, hi = lim[kind]["min"], lim[kind]["max"]
        place = town_of(world, e["place"]) if kind == "prices" else e["place"]
        state["effects"].append({"kind": kind, "place": place, "value": max(lo, min(hi, e["value"])),
                                 "until": t + days * 1440, "cause": cause, "thread": thread_id})
    elif kind == "closed" and known(world, e.get("place")):
        state["effects"].append({"kind": "closed", "place": e["place"], "value": 0, "until": t + days * 1440,
                                 "text": e.get("text") or cause, "cause": cause, "thread": thread_id})
    elif kind == "mark" and known(world, e.get("place")) and e.get("text"):
        ps = store.load_place(e["place"])
        ps.marks = (ps.marks + [e["text"]])[-12:]
        store.save_place(ps)
    elif kind == "loot" and known(world, e.get("place")):
        from engine import inventory, loot
        place = world.places[e["place"]]
        level = (place.danger or place.trade_level)[0]
        ps = store.load_place(e["place"])
        rng = random.Random(f"{t}:{e['place']}")
        inventory.leave_on_ground(ps, loot.make_drop(level, loot.roll_rarity(rng), rng), t)
        store.save_place(ps)
    elif kind == "lead" and known(world, e.get("place")) and e.get("text"):
        from engine import discovery
        data = store.load_discoveries()
        if discovery.add_lead(data, e["place"], e["text"], t, random.Random(f"{t}:lead:{e['place']}")):
            store.save_discoveries(data)
            add_news(state, e["text"], e["place"], t, [g for g in e.get("groups", []) if g in world.knowledge_groups] or ["everyone"])
    elif kind == "fact" and e.get("text"):
        add_news(state, e["text"], e.get("place") or "", t,
                 [g for g in e.get("groups", []) if g in world.knowledge_groups] or ["everyone"])
    else:
        return "ignored: the person or place it names is unknown, or the change is not allowed here"
    state["effects"] = [x for x in state["effects"] if x["until"] > t - 1440]
    return "applied"


def move_npc(store, npc, place_id: str) -> None:
    old = store.load_place(npc.location)
    old.residents = [r for r in old.residents if r != npc.id]
    store.save_place(old)
    new = store.load_place(place_id)
    if npc.id not in new.residents:
        new.residents.append(npc.id)
        store.save_place(new)
    npc.location = place_id
    store.save_npc(npc)


def remove_npc(store, world, npc, how: str, t: int, dead: bool | None = None, mourned: bool | None = None) -> None:
    """Take someone out of the story - and tie off everything the player had with them. (f430) `dead` says whether it was a death, so
    a town grieves only for its dead: the f425 night hung black cloth for three captives who had slipped their bonds, the meaning of
    'got away' read as a death. `mourned` False: the town does not grieve them whatever became of them (an outlaw held captive). Left
    None (a model's own words for it), the words are read for a death as before."""
    npc.gone = how
    npc.work_offer = npc.quest_offer = None
    store.save_npc(npc)
    store.journal(t, "npc_gone", "", npc.id, f"{npc.name} is gone: {how}", {"how": how, "place": npc.location, "dead": dead, "mourned": mourned})
    ps = store.load_place(npc.location)
    ps.residents = [r for r in ps.residents if r != npc.id]
    store.save_place(ps)
    if not store.player_exists():
        return
    player = store.load_player()
    c = player.character
    for q in list(player.quests):
        if q.get("issuer") == npc.id or (q.get("kind") == "deliver" and q.get("to_name") and q["to_name"] in npc.name):
            player.quests.remove(q)
            c.key_items = [k for k in c.key_items if k.id != f"quest_{q['id']}"]
            c.item_history.append(f"{q['title']} - it came to nothing. {npc.name}: {how} (day {clock.day(t)}).")
    for order in list(player.commissions):
        if order["npc"] == npc.id:
            player.commissions.remove(order)
            c.item_history.append(f"Your commission from {npc.name} was never finished. {npc.name}: {how} "
                                  f"(day {clock.day(t)}).")
    store.save_player(player)


NEWS_KEEP = 300


def cap_news(news: list) -> list:
    """The news list kept to NEWS_KEEP items: the oldest plain gossip goes first, so a tale of the player's deeds (engine/standing.py)
    is still there to move standing when it reaches a far town."""
    if len(news) <= NEWS_KEEP:
        return news
    over = len(news) - NEWS_KEEP
    out = []
    for n in news:                                             # drop the oldest entries without a deed, as many as needed
        if over and not n.get("deed"):
            over -= 1
            continue
        out.append(n)
    return out[-NEWS_KEEP:]


def add_news(state, text: str, origin: str, t: int, groups: list[str], thread: str = "") -> None:
    """A piece of news. `thread` (f331) ties it to the situation it is about, so arrival can find a situation's own news. The same
    news from the same place while the first telling is still news is one tale told again, not a second row: the row counts its
    tellings (`times`, read by news_text) and becomes the newest. A tale of the player's deeds (engine/standing.py, `deed`) is never
    folded: each one moves standing where it arrives."""
    if not (text and text.strip()):
        return
    text = text.strip()
    news = state.setdefault("news", [])
    keep = P["news"]["keep_days"] * 1440
    for i, n in enumerate(news):
        if n["text"] == text and n["origin"] == origin and not n.get("deed") and t - n["minute"] <= keep:
            n["times"] = int(n.get("times", 1)) + 1
            n["minute"] = t
            n["groups"] = list(dict.fromkeys(list(n["groups"]) + list(groups)))
            if thread:
                n["thread"] = thread
            news.append(news.pop(i))
            state["news"] = cap_news(news)
            return
    row = {"text": text, "origin": origin, "minute": t, "groups": groups}
    if thread:
        row["thread"] = thread
    news.append(row)
    state["news"] = cap_news(news)


COUNTS = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def news_text(n: dict, now: int | None = None) -> str:
    """A news row as it is told: a tale told more than once says so, for two days after the last telling (f356); then it is just the tale."""
    times = int(n.get("times", 1) or 1)
    if times < 2 or (now is not None and now - n.get("minute", now) > 2 * 1440):
        return n["text"]
    return f"{n['text']} Again." if times == 2 else f"{n['text']} That makes {COUNTS.get(times, str(times))} times."


# ---------- context for the model ----------

def context_for_place(store, world, catalog, state, place, t, big: bool = False) -> str:
    town = town_of(world, place.id)
    threads = [f"{x['title']} ({x['place']})" for x in state["threads"] if x["status"] == "active"][-8:]
    history = [h["text"] for h in state["history"][-6:]]
    pressures = [p.description for p in world.pressures.values() if p.place in (place.id, town)]
    from engine import towns, matters, deeds
    town_lines = towns.thread_lines(world, place.id, big)                  # (f316) the town's character, trouble and (for a big one) secret
    cond = towns.condition(store, world, place.id, t)                      # (f323) the state the town is in, what is settled, what the stranger did
    if cond.name != "calm":
        town_lines.append(f"THE TOWN IS {cond.name.upper()} ({cond.why}): what you write must fit that.")
    settled = matters.town_memory(store, world, place.id, t)
    if settled:
        town_lines.append("SETTLED LATELY (it stays settled; do not start the same trouble again): " + "; ".join(settled))
    region = world.places[town].region if town in world.places else place.region
    mine = [deeds.describe(d) for d in deeds.since(state, t - P.get("deeds_days", 30) * 1440)
            if d.get("kind") != "offense" and world.places.get(d.get("place") or "") and world.places[d["place"]].region == region][-6:]
    if mine:
        town_lines.append("WHAT THE STRANGER HAS DONE IN THESE PARTS (the world reacts to it; the stranger is never a character in what you write): "
                          + "; ".join(mine))
    group = world.locals_group(place.id)
    facts = [f.text for f in world.lore.values() if group in f.known_by][:4]
    from engine import retrieval
    people = [f"{n.id}: {n.name}, {n.role.replace('_', ' ')}{' (' + n.mood + ')' if n.mood else ''}" for n in retrieval.people_in_town(store, world, town)]
    roads = "; ".join(f"{r.id}: {r.from_} - {r.to}" for r in world.roads.values())
    return pp.place_context(world, store, place, t, clock.season(t), threads, history, pressures, facts,
                            people[:20], list(world.knowledge_groups), sorted(catalog.traits) if catalog else [], roads,
                            creatures=events.creature_menu(world, place.id),
                            roles=events.role_menu(world) if big else "", town_lines=town_lines)
