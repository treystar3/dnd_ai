"""The pulse: the world moving on its own, away from the player.

Every few game hours the world pulses. Most pulses are quiet. An eventful one either moves a person's motive a
step forward, or starts a situation (a "thread") somewhere. Threads unfold in stages over time, then end - dealt
with by someone, or running their course and leaving their fallout. Everything mechanical goes through effects
the engine knows how to apply; everything else becomes history and news that people carry along the roads.

World state is saved per campaign in world_state.json:
  last (minute of the last pulse), threads, news, history, effects, cooldowns, campaign (id of the running one)
"""

import random
import uuid
from pathlib import Path

import yaml

from engine import clock, events
from engine import pulse_prompts as pp
from llm.contracts import MotiveStep, ThreadProposal
from llm.gateway import LLMError, generate
from ui import console

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "pulse.yaml").read_text(encoding="utf-8"))
INTERVAL = P["interval_hours"] * 60


def empty_state(now: int) -> dict:
    return {"last": now, "threads": [], "news": [], "history": [], "effects": [], "cooldowns": {}, "campaign": "",
            "deeds": [], "spawns": [], "camps": [], "vacancies": {}, "player_events": [], "cataclysms": 0, "cataclysm_end": 0}


# ---------- reading the world's state ----------

def active_effects(state: dict, now: int, kind: str, place: str) -> list[dict]:
    return [e for e in state.get("effects", []) if e["kind"] == kind and e["place"] == place and e["until"] > now]


def known(world, place_id) -> bool:
    """A real place of the world - not a stop on the road, which exists only while the player stands on it."""
    p = world.places.get(place_id or "")
    return bool(p) and p.type != "road"


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
    state = store.load_world_state()
    hits = active_effects(state, now, "closed", place_id)
    return hits[0]["text"] if hits else ""


def happenings_at(store, world, place_id: str, now: int) -> list[str]:
    """What can be seen of the world's situations here right now."""
    state = store.load_world_state()
    town = town_of(world, place_id)
    out = []
    for t in state.get("threads", []):
        if t["status"] == "active" and t["place"] in (place_id, town):
            out.append(t["stages"][t["stage"]]["description"])
    for e in state.get("effects", []):
        if e["kind"] == "closed" and e["place"] == place_id and e["until"] > now:
            out.append(f"The way is closed: {e['text']}")
    return out


def news_for(store, world, npc, now: int, limit: int = 5) -> list[str]:
    """News this person has heard: it must have reached where they are, and be news their circles would carry."""
    state = store.load_world_state()
    groups = set(npc.knowledge_groups) | {"everyone"}
    keep = P["news"]["keep_days"] * 1440
    heard = []
    for n in reversed(state.get("news", [])):
        if now - n["minute"] > keep or not (set(n["groups"]) & groups):
            continue
        if n["minute"] + travel_delay(world, n["origin"], npc.location) <= now:
            heard.append(n["text"])
        if len(heard) >= limit:
            break
    return heard


def travel_delay(world, origin: str, where: str) -> int:
    if origin not in world.places or where not in world.places:
        return 0
    if origin == where or town_of(world, origin) == town_of(world, where):
        return 0
    found = world.path(origin, where)
    if not found:
        return 10 ** 9
    return round(found[1] * P["news"]["hours_per_walking_hour"])


# ---------- the clock ----------

def catch_up(store, world, catalog, now: int) -> None:
    """Run every pulse between the last one and now. Timers always run; new events are capped per call."""
    state = store.load_world_state() or empty_state(now)
    if "last" not in state:
        state["last"] = now
    budget = P["max_new_events_per_action"]
    rng = random.Random(f"{store.meta.seed}:pulse:{state['last']}")
    changed = False
    while state["last"] + INTERVAL <= now:
        state["last"] += INTERVAL
        t = state["last"]
        changed |= tick_threads(store, world, catalog, state, t, rng)
        if state.get("camps"):
            events.expire_camps(store, world, state, t)
        if budget <= 0:
            continue
        # one big-event slot (a campaign, or at high level a cataclysm) opens now and then; one at a time
        slot_chance = P["interval_hours"] / (events.E["campaign"]["every_days"] * 24)
        if not state.get("campaign") and rng.random() < slot_chance:
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
            done = move_motive(store, world, catalog, state, t, rng)
        else:
            done = start_thread(store, world, catalog, state, t, rng)
        if done:
            budget -= 1
            changed = True
    store.save_world_state(state)


FINISHED_KEPT = 30


# ---------- threads ----------

def start_thread(store, world, catalog, state, t, rng, tier: str | None = None, pressure_id: str = "", place_id: str = "") -> bool:
    """Start a situation. pressure_id / place_id force the seed and the place (used by tools/pulse_preview.py)."""
    plain = [k for k in P["tiers"] if k not in ("campaign", "cataclysm")]
    tier = tier or rng.choices(plain, weights=[P["tiers"][k]["weight"] for k in plain])[0]
    rule = P["tiers"][tier]
    cooldown = P["pressure_cooldown_days"] * 1440
    pressures = [p for p in world.pressures.values() if t - state["cooldowns"].get(p.id, -10 ** 9) > cooldown]
    if tier == "campaign" and events.E["campaign"]["prefer_marked"]:
        marked = [p for p in pressures if p.campaign]
        pressures = marked or pressures
    if pressure_id:
        pressure = world.pressures[pressure_id]
        place = world.places.get(pressure.place) or region_town(world, pressure.place, rng)
    elif place_id:
        here = [p for p in pressures if p.place == place_id]
        pressure = rng.choices(here, weights=[p.weight for p in here])[0] if here else None
        place = world.places.get(place_id)
    elif pressures and (tier == "campaign" or rng.random() < 0.75):
        pressure = rng.choices(pressures, weights=[p.weight for p in pressures])[0]
        place = world.places.get(pressure.place) or region_town(world, pressure.place, rng)
    else:
        pressure = None
        towns = [p for p in world.places.values() if not p.parent and p.type not in ("dungeon", "road") and known(world, p.id)]
        place = rng.choice(towns)
    if not place:
        return False
    big = tier in events.BIG
    thread_id = uuid.uuid4().hex[:8]
    system = pp.THREAD_SYSTEM + (pp.BIG_EXTRA if big else "")
    extra = ""
    if big:
        extra = f"\nPLAYER LEVEL: {events.player_level(store)}"
    try:
        proposal = generate(
            "pulse_thread", system,
            f"TIER: {tier}\nSTAGES: {rule['stages']}\n" + context_for_place(store, world, catalog, state, place, t, big=big) + extra,
            ThreadProposal, temperature=0.95, max_tokens=2400 if big else 1800, validation_context={"stages": rule["stages"]},
        )
    except LLMError as e:
        console.debug(f"pulse: no situation this time ({e})")
        return False
    if not known(world, proposal.place):
        proposal.place = place.id
    days = rng.randint(*rule["days"])
    span = days * 1440
    times = [t + round(span * i / rule["stages"]) for i in range(rule["stages"])] + [t + span]
    thread = {"id": thread_id, "title": proposal.title, "tier": tier, "place": proposal.place,
              "pressure": pressure.id if pressure else "", "stage": 0, "times": times, "status": "active",
              "stages": [s.model_dump() for s in proposal.stages], "fallout": proposal.fallout.model_dump(),
              "resolution": proposal.resolution, "made": t,
              "groups": [g for g in proposal.groups if g in world.knowledge_groups] or ["everyone"],
              "reward_hint": list(pressure.reward) if pressure else [], "paths": [], "scope_places": [],
              "triumph": proposal.triumph.model_dump() if proposal.triumph else None,
              "boss_lines": proposal.boss_lines.model_dump(exclude={"captain_intro"}) if proposal.boss_lines and tier == "campaign" else None}
    state["threads"].append(thread)
    if pressure:
        state["cooldowns"][pressure.id] = t
    if tier == "campaign":
        state["campaign"] = thread["id"]
    add_news(state, proposal.news, proposal.place, t, thread["groups"])
    apply_effects(store, world, catalog, state, proposal.stages[0].effects, tier, t, thread["title"], thread_id=thread_id)
    posted = False
    if proposal.contract and proposal.contract.what:
        posted = post_contract(store, world, proposal.contract, thread, t)
    if big:
        thread["paths"] = events.build_paths(store, world, state, proposal.paths, thread, posted)
        thread["scope_places"] = sorted({e.place for st in proposal.stages for e in st.effects if e.place in world.places})
    console.debug(f"pulse: [{tier}] {proposal.title} at {proposal.place}")
    return True


def region_town(world, region_id: str, rng):
    """A scenario aimed at a whole region lands in one of its settlements."""
    if region_id not in world.regions:
        return None
    towns = [p for p in world.places.values() if p.region == region_id and not p.parent and not p.danger
             and p.type not in ("dungeon", "road", "home")]
    return rng.choice(towns) if towns else None


def tick_threads(store, world, catalog, state, t, rng) -> bool:
    changed = False
    for th in [x for x in state["threads"] if x["status"] == "active"]:
        while th["status"] == "active" and th["stage"] + 1 < len(th["stages"]) and t >= th["times"][th["stage"] + 1]:
            th["stage"] += 1
            stage = th["stages"][th["stage"]]
            apply_effects(store, world, catalog, state, stage["effects"], th["tier"], t, th["title"], raw=True, thread_id=th["id"])
            add_news(state, stage["description"], th["place"], t, th["groups"])
            if th["tier"] == "cataclysm":
                events.on_stage(store, world, catalog, state, th, t, rng)
            elif th["tier"] in events.BIG:
                events.sync_paths(state, th)
            changed = True
        if th["status"] == "active" and t >= th["times"][-1]:
            if rng.random() < P["tiers"][th["tier"]]["resolved_by_others"]:
                who = resolver(store, world, th, rng)
                end_thread(store, state, th, "resolved", f"{th['title']} - settled by {who}.", t)
                th["result"] = "others"
            else:
                fall = th["fallout"]
                apply_effects(store, world, catalog, state, fall["effects"], th["tier"], t, th["title"], raw=True, thread_id=th["id"])
                end_thread(store, state, th, "ended", f"{th['title']} - {fall['description']}", t)
                th["result"] = "ignored"
                if th["tier"] == "cataclysm":
                    events.after_ignored(store, world, state, th, t)
            if th["tier"] == "cataclysm":
                state["cataclysm_end"] = t
            changed = True
    return changed


def resolver(store, world, th, rng) -> str:
    """Who dealt with it, off-screen. Guild contractors sometimes, and it marks them."""
    if rng.random() < 0.4:
        for nid in store.list_npcs():
            n = store.load_npc(nid)
            if n.role == "guild_contractor" and not n.gone:
                n.mood = rng.choice([f"proud, after settling {th['title'].lower()}",
                                     f"nursing a fresh wound from {th['title'].lower()}",
                                     f"flush with coin from {th['title'].lower()}"])
                store.save_npc(n)
                return f"{n.name}, a guild contractor"
    place = world.places[th["place"]]
    return "the watch" if place.residents.get("guard") or place.residents.get("watch_captain") else \
        f"the people of {place.name}"


def end_thread(store, state, th, status: str, line: str, t: int) -> None:
    th["status"] = status
    if state.get("campaign") == th["id"]:
        state["campaign"] = ""
    state["history"].append({"minute": t, "text": line, "place": th["place"]})
    state["history"] = state["history"][-200:]
    done = [x for x in state.get("threads", []) if x["status"] != "active"]
    if len(done) > FINISHED_KEPT:
        drop = {x["id"] for x in done[:-FINISHED_KEPT]}
        state["threads"] = [x for x in state["threads"] if x["id"] not in drop]
    add_news(state, line, th["place"], t, th["groups"])


def post_contract(store, world, offer, thread, t) -> bool:
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
    movers = [n for n in (store.load_npc(i) for i in store.list_npcs())
              if n.tier != "background" and n.motive and not n.gone and known(world, n.location)
              and t - last.get(n.id, -10 ** 9) >= gap]
    if not movers:
        return False
    npc = rng.choice(movers)
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
    apply_effects(store, world, catalog, state, step.effects, "normal", t, f"{npc.name}'s doings")
    npc = store.load_npc(npc.id)
    npc.motive = (step.next_motive.strip() or npc.motive) if step.status == "continuing" else ""
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
                  thread_id: str = "") -> None:
    for e in effects:
        e = e if raw else e.model_dump()
        try:
            if e["kind"] in ("spawn", "camp", "seal"):
                events.apply_big(store, world, catalog, state, e, tier, t, cause, thread_id)
                continue
            apply_one(store, world, catalog, state, e, tier, t, cause)
        except Exception as err:  # an effect the world can't honor is simply dropped
            console.debug(f"pulse: dropped effect {e.get('kind')} ({err})")


def apply_one(store, world, catalog, state, e: dict, tier: str, t: int, cause: str) -> None:
    kind, lim = e["kind"], P["effects"]
    days = max(1, min(lim["max_days"], e.get("days") or 3))
    npc = store.load_npc(e["npc"]) if e.get("npc") and store.npc_exists(e["npc"]) else None
    if npc and npc.gone:
        return
    if kind == "relation" and npc and e.get("other") and store.npc_exists(e["other"]):
        r = npc.relations.get(e["other"], {"score": 0, "feeling": ""})
        r["score"] = max(-100, min(100, r["score"] + max(lim["relation"]["min"], min(lim["relation"]["max"], e["value"]))))
        r["feeling"] = e.get("text") or r["feeling"]
        npc.relations[e["other"]] = r
        store.save_npc(npc)
    elif kind == "mood" and npc and e.get("text"):
        npc.mood = e["text"]
        store.save_npc(npc)
    elif kind == "move" and npc and known(world, e.get("place")):
        if world.places[e["place"]].danger or not world.peoples_at(e["place"]):
            return
        move_npc(store, npc, e["place"])
    elif kind == "leave" and npc:
        met = npc.tier != "background"
        if npc.protected or npc.role in P["protected_roles"] or (met and tier not in P["may_remove_met"]):
            return
        remove_npc(store, world, npc, e.get("text") or "gone away", t)
    elif kind == "arrive" and known(world, e.get("place")) and e.get("role") in world.roles:
        if world.places[e["place"]].danger or not world.peoples_at(e["place"]):
            return
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
                                 "until": t + days * 1440, "cause": cause})
    elif kind == "closed" and known(world, e.get("place")):
        state["effects"].append({"kind": "closed", "place": e["place"], "value": 0, "until": t + days * 1440,
                                 "text": e.get("text") or cause, "cause": cause})
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
    state["effects"] = [x for x in state["effects"] if x["until"] > t - 1440]


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


def remove_npc(store, world, npc, how: str, t: int) -> None:
    """Take someone out of the story - and tie off everything the player had with them."""
    npc.gone = how
    npc.work_offer = npc.quest_offer = None
    store.save_npc(npc)
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


def add_news(state, text: str, origin: str, t: int, groups: list[str]) -> None:
    if text and text.strip():
        state.setdefault("news", []).append({"text": text.strip(), "origin": origin, "minute": t, "groups": groups})
        state["news"] = state["news"][-300:]


# ---------- context for the model ----------

def context_for_place(store, world, catalog, state, place, t, big: bool = False) -> str:
    town = town_of(world, place.id)
    threads = [f"{x['title']} ({x['place']})" for x in state["threads"] if x["status"] == "active"][-8:]
    history = [h["text"] for h in state["history"][-6:]]
    pressures = [p.description for p in world.pressures.values() if p.place in (place.id, town)]
    group = world.locals_group(place.id)
    facts = [f.text for f in world.lore.values() if group in f.known_by][:4]
    people = []
    for nid in store.list_npcs():
        n = store.load_npc(nid)
        if not n.gone and town_of(world, n.location) == town:
            people.append(f"{n.id}: {n.name}, {n.role.replace('_', ' ')}{' (' + n.mood + ')' if n.mood else ''}")
    roads = "; ".join(f"{r.id}: {r.from_} - {r.to}" for r in world.roads.values())
    return pp.place_context(world, store, place, t, clock.season(t), threads, history, pressures, facts,
                            people[:20], list(world.knowledge_groups), sorted(catalog.traits) if catalog else [], roads,
                            creatures=events.creature_menu(world, place.id) if big else "",
                            roles=events.role_menu(world) if big else "")
