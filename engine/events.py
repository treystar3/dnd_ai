"""Big events: what campaigns and cataclysms put into the world, how the player can end them, and what ending one is worth.

The pulse (engine/pulse.py) starts and ages situations. This module is the layer for the large ones:

  * spawns, camps and seals - physical changes (a creature that haunts a zone, a camp that sets up, a place that is shut off)
  * resolution paths - real ways to end an event, checked against the deeds ledger (engine/deeds.py)
  * the judge - one short model call that can recognise an ending nobody planned, from the ledger alone
  * the grand reward - what the world gives a player who ends a campaign or cataclysm
  * allies - people of the realm who fight beside the player against an event's boss
  * cataclysms - the rare, world-shaking tier: spread by the map, towns that fall, people who die, homes that ruin

The engine decides every number; the model only names and tells. Rules live in data/rules/events.yaml.
"""

import heapq
import random
import uuid
from pathlib import Path

import yaml

from engine import clock, deeds
from engine import pulse_prompts as pp
from llm.contracts import CataclysmProposal, JudgeVerdict
from llm.gateway import LLMError, generate
from ui import console

ROOT = Path(__file__).resolve().parent.parent
E = yaml.safe_load((ROOT / "data" / "rules" / "events.yaml").read_text(encoding="utf-8"))
C = E["cataclysm"]
BIG = ("rare", "campaign", "cataclysm")


def _pulse():
    from engine import pulse          # pulse imports this module; import it lazily to avoid a cycle
    return pulse


# ---------- the map ----------

def settlements(world) -> list:
    """Places people live: top-level, no danger, with residents."""
    return [p for p in world.places.values()
            if not p.parent and p.type not in ("dungeon", "road", "home") and not p.danger and p.residents and _pulse().known(world, p.id)]


def distances(world, origin: str) -> dict[str, int]:
    """Walking minutes from origin to every reachable place."""
    best = {origin: 0}
    queue = [(0, origin)]
    while queue:
        cost, cur = heapq.heappop(queue)
        if cost > best[cur]:
            continue
        for nxt in world.neighbors(cur):
            new = cost + world.travel_minutes(cur, nxt)
            if new < best.get(nxt, float("inf")):
                best[nxt] = new
                heapq.heappush(queue, (new, nxt))
    return best


def zones(world) -> list:
    return [p for p in world.places.values() if p.danger and p.type != "road" and not p.parent]


def nearest_zone(world, place_id: str, level: int | None = None, rng: random.Random | None = None):
    """The danger zone nearest a place (the place itself if it is one). With a level, prefer zones whose band is near it."""
    p = world.places.get(place_id)
    if p and p.danger:
        return p
    dist = distances(world, place_id)
    found = [(dist.get(z.id, 10 ** 9) + (abs(((z.danger[0] + z.danger[1]) // 2) - level) * 60 if level else 0), z.id)
             for z in zones(world)]
    found.sort()
    return world.places[found[0][1]] if found else None


def creature_menu(world, place_id: str, limit: int = 28) -> str:
    """Creature ids the model may name for a place: those that live in the nearest danger zone (or nearby ones)."""
    from engine.encounters import CREATURE_RULES
    zone = nearest_zone(world, place_id)
    out, seen = [], set()
    cands = world.creature_candidates(zone.id, CREATURE_RULES["rarity_weight"]) if zone else []
    for c, _ in sorted(cands, key=lambda cw: -cw[1]):
        if c.id not in seen and len(out) < limit:
            seen.add(c.id)
            out.append(f"{c.id}: {c.name} L{c.levels[0]}-{c.levels[1]}")
    return "; ".join(out)


def role_menu(world) -> str:
    skip = {"guild_clerk", "guild_master", "guild_instructor", "guild_contractor", "quartermaster", "land_agent", "relic_dealer"}
    return ", ".join(sorted(r for r in world.roles if r not in skip))[:900]


def player_level(store) -> int:
    try:
        return store.load_player().character.level if store.player_exists() else 1
    except Exception:
        return 1


# ---------- spawns, camps, seals ----------

def add_spawn(store, world, state, thread_id: str, place_id: str, creature_id: str, boss: bool, t: int, days: int = 0,
              level: int | None = None, live_from: int | None = None, name: str = "", need: int = 3, **extra) -> dict | None:
    """Put a creature into a zone. A town is not a zone: the spawn goes to the nearest zone instead."""
    c = world.bestiary.get(creature_id)
    if not c:
        return None
    zone = nearest_zone(world, place_id, level)
    if not zone:
        return None
    s = {"id": uuid.uuid4().hex[:8], "thread": thread_id, "place": zone.id, "creature": c.id, "boss": bool(boss),
         "level": level, "name": name or (f"the {c.name.lower()}" if boss else c.name.lower()), "need": 1 if boss else need,
         "kills": 0, "defeated": False, "from": live_from if live_from is not None else t,
         "until": (live_from if live_from is not None else t) + (days or E["spawn"]["days"]) * 1440}
    s.update(extra)            # hp_mult (health as a multiple of a normal creature), after (spawn ids that must fall first), side, npc
    state.setdefault("spawns", []).append(s)
    return s


def live_spawns(state: dict, now: int, thread_id: str = "", place: str = "") -> list[dict]:
    done = {s["id"] for s in state.get("spawns", []) if s["defeated"]}
    return [s for s in state.get("spawns", [])
            if not s["defeated"] and s["from"] <= now < s["until"] and all(a in done for a in s.get("after", []))
            and (not thread_id or s["thread"] == thread_id) and (not place or s["place"] == place)]


def pick_spawn(store, place_id: str, rng: random.Random, now: int) -> dict | None:
    """Maybe turn an encounter at this place into one of the event's creatures."""
    state = store.load_world_state()
    if not state or not state.get("spawns"):
        return None
    here = live_spawns(state, now, place=place_id)
    if not here:
        return None
    bosses = [s for s in here if s["boss"]]
    if bosses and rng.random() < E["spawn"]["boss_chance"]:
        return rng.choice(bosses)
    others = [s for s in here if not s["boss"]]
    if others and rng.random() < E["spawn"]["chance"]:
        return rng.choice(others)
    return None


def spawn_fighters(world, s: dict, rng: random.Random, player_lvl: int):
    """(creature, fighters) for a spawn encounter."""
    from engine import combat
    c = world.bestiary[s["creature"]]
    place = world.places[s["place"]]
    if s["level"]:
        lvl = s["level"]
    elif s["boss"]:
        lvl = place.danger[1] + E["spawn"]["boss_over_band"]
    else:
        lvl = rng.randint(*place.danger)
    count = 1 if s["boss"] else rng.randint(1, E["spawn"]["max_group"])
    fighters = []
    for i in range(count):
        name = s["name"] if s["boss"] else s["name"] + (f" {i + 1}" if count > 1 else "")
        f = combat.fighter_from_creature(c, lvl if s["boss"] else max(1, lvl + rng.randint(-2, 2)),
                                         "boss" if s["boss"] else ("elite" if i == 0 else "normal"),
                                         f"e{i + 1}", name, "near")
        f.spawn = s["id"]
        if s["boss"]:
            scale = s.get("hp_mult", E["spawn"]["boss_health"]) / combat.RULES["creatures"]["rank"]["boss"]["health"]
            f.max_hp = f.hp = max(1, round(f.max_hp * scale))
            if s.get("tier"):
                from engine import bosses
                f.boss = bosses.make(s.get("kit") or bosses.kit_for(c.category), s["tier"], s["name"], s.get("lines"))
        fighters.append(f)
    return c, fighters


def on_kills(store, dead, now: int, world=None) -> list[dict]:
    """Count kills of event creatures. Returns spawns just defeated."""
    tagged = [e for e in dead if getattr(e, "spawn", "")]
    if not tagged:
        return []
    state = store.load_world_state()
    won = []
    for e in tagged:
        s = next((x for x in state.get("spawns", []) if x["id"] == e.spawn), None)
        if not s or s["defeated"]:
            continue
        s["kills"] += 1
        if s["kills"] >= s["need"]:
            s["defeated"] = True
            won.append(s)
    store.save_world_state(state)
    for s in won:
        if s.get("npc") and world is not None and store.npc_exists(s["npc"]):
            n = store.load_npc(s["npc"])
            if not n.gone:
                _pulse().remove_npc(store, world, n, "fell at the head of the war host", now)
                _vacancy(store, world, n, now, random.Random())
    return won


def add_camp(store, world, state, thread_id: str, place_id: str, role: str, t: int, days: int = 0) -> bool:
    if role not in world.roles or place_id not in world.places or not world.peoples_at(place_id):
        return False
    ps = store.load_place(place_id)
    state.setdefault("camps", []).append({"thread": thread_id, "place": place_id, "role": role,
                                          "until": t + (days or E["camp"]["days"]) * 1440, "before": list(ps.residents)})
    ps.extra_roles[role] = ps.extra_roles.get(role, 0) + 1
    store.save_place(ps)
    return True


def expire_camps(store, world, state, t: int) -> None:
    pulse = _pulse()
    keep = []
    for camp in state.get("camps", []):
        if camp["until"] > t:
            keep.append(camp)
            continue
        ps = store.load_place(camp["place"])
        if ps.extra_roles.get(camp["role"]):
            ps.extra_roles[camp["role"]] -= 1
            if ps.extra_roles[camp["role"]] <= 0:
                del ps.extra_roles[camp["role"]]
            store.save_place(ps)
        for nid in list(ps.residents):
            if nid in camp["before"]:
                continue
            n = store.load_npc(nid)
            if n.role == camp["role"] and n.tier == "background" and not n.gone:
                pulse.remove_npc(store, world, n, "packed up the camp and moved on", t)
                break
    state["camps"] = keep


def apply_big(store, world, catalog, state, e: dict, tier: str, t: int, cause: str, thread_id: str) -> None:
    """spawn / camp / seal effects written by the model. Anything that cannot work is dropped by the caller's try/except."""
    pulse = _pulse()
    kind = e["kind"]
    days = max(1, min(pulse.P["effects"]["max_days"], e.get("days") or 0)) if e.get("days") else 0
    if kind == "spawn":
        c = world.bestiary.get(e.get("creature", ""))
        if c and e.get("place") in world.places:
            lvl = None
            if e.get("boss"):
                zone = nearest_zone(world, e["place"])
                lvl = zone.danger[1] + E["spawn"]["boss_over_band"] if zone else None
            th = next((x for x in state.get("threads", []) if x["id"] == thread_id), None)
            extra = {"tier": "campaign", "lines": (th or {}).get("boss_lines") or {}} if e.get("boss") and tier in ("campaign", "cataclysm") else {}
            s = add_spawn(store, world, state, thread_id, e["place"], c.id, bool(e.get("boss")), t, days, lvl, **extra)
            if s:
                console.debug(f"event: {s['name']} now haunts {s['place']}")
    elif kind == "camp":
        add_camp(store, world, state, thread_id, e.get("place", ""), e.get("role", ""), t, days)
    elif kind == "seal" and pulse.known(world, e.get("place")):
        state["effects"].append({"kind": "closed", "place": e["place"], "value": 0,
                                 "until": t + (days or E["seal"]["days"]) * 1440,
                                 "text": e.get("text") or "sealed off", "cause": cause, "seal": True})


# ---------- resolution paths ----------

def build_paths(store, world, state, proposed, thread: dict, contract_posted: bool) -> list[dict]:
    """The real ways to end this event: the model's suggestions the engine can check, plus the ones it can always check."""
    out, seen = [], set()

    def add(p):
        key = (p["kind"], p.get("target", ""), p.get("spawn", ""))
        if key not in seen and len(out) < 6:
            seen.add(key)
            out.append(p)

    for s in state.get("spawns", []):
        if s["thread"] == thread["id"] and s["boss"]:
            add({"id": f"kill_{s['id']}", "name": f"Defeat {s['name']}", "how": f"{s['name']} must fall.", "kind": "kill",
                 "target": s["creature"], "spawn": s["id"], "done": False})
    for p in proposed or []:
        if p.kind == "kill" and p.target in world.bestiary:
            add({"id": f"kill_{p.target}", "name": p.name, "how": p.how, "kind": "kill", "target": p.target, "spawn": "", "done": False})
        elif p.kind == "persuade" and p.target and store.npc_exists(p.target) and not store.load_npc(p.target).gone:
            add({"id": f"talk_{p.target}", "name": p.name, "how": p.how, "kind": "persuade", "target": p.target, "spawn": "", "done": False})
        elif p.kind == "clear" and p.target in world.places and world.places[p.target].danger:
            add({"id": f"clear_{p.target}", "name": p.name, "how": p.how, "kind": "clear", "target": p.target, "spawn": "", "done": False})
        elif p.kind == "contract" and contract_posted:
            add({"id": "contract", "name": p.name, "how": p.how, "kind": "contract", "target": "", "spawn": "", "done": False})
    if contract_posted:
        add({"id": "contract", "name": "Finish the guild's job", "how": "Complete the contract the guild posted.",
             "kind": "contract", "target": "", "spawn": "", "done": False})
    return out


def sync_paths(state: dict, th: dict) -> None:
    """A boss that turned up in a later stage becomes a way to end the event."""
    have = {p.get("spawn") for p in th.get("paths", [])}
    for s in state.get("spawns", []):
        if s["thread"] == th["id"] and s["boss"] and s["id"] not in have:
            th.setdefault("paths", []).append({"id": f"kill_{s['id']}", "name": f"Defeat {s['name']}", "how": f"{s['name']} must fall.",
                                               "kind": "kill", "target": s["creature"], "spawn": s["id"], "done": False})


def _won_over(state: dict, since: int, npc_id: str) -> bool:
    mine = [d for d in deeds.since(state, since, ["persuade"]) if d.get("npc") == npc_id]
    return any(d.get("degree") == "strong success" for d in mine) or len(mine) >= 2


def path_met(path: dict, state: dict, thread: dict) -> bool:
    made = thread["made"]
    if path["kind"] == "kill":
        if path.get("spawn"):
            s = next((x for x in state.get("spawns", []) if x["id"] == path["spawn"]), None)
            return bool(s and s["defeated"])
        return any(d.get("creature") == path["target"] for d in deeds.since(state, made, ["kill"]))
    if path["kind"] == "horde":
        ids = [i for i in path.get("spawn", "").split(",") if i]
        found = [x for x in state.get("spawns", []) if x["id"] in ids]
        return bool(found) and all(x["defeated"] for x in found)
    if path["kind"] == "persuade":
        return _won_over(state, made, path["target"])
    if path["kind"] == "treaty":
        ids = [i for i in path["target"].split(",") if i]
        return bool(ids) and all(_won_over(state, made, i) for i in ids)
    if path["kind"] == "clear":
        return any(d.get("place") == path["target"] for d in deeds.since(state, made, ["dungeon_cleared"]))
    if path["kind"] == "contract":
        return any(d.get("thread") == thread["id"] for d in deeds.since(state, made, ["quest_done"]))
    return False


# ---------- after a deed: paths, then the judge ----------

def after_deed(ws, deed: dict) -> None:
    """Called by the game after something the world could notice. May end an event, or move it."""
    pulse = _pulse()
    store, world = ws.store, ws.world
    state = store.load_world_state()
    if not state:
        return
    changed = False
    for th in [x for x in state.get("threads", []) if x["status"] == "active"]:
        if th["tier"] not in ("normal", "uncommon") and th.get("paths"):
            met = next((p for p in th["paths"] if not p["done"] and path_met(p, state, th)), None)
            if met:
                met["done"] = True
                th["won_path"] = met
                finish(ws, state, th, f"by way of '{met['name']}'", "truce" if met["kind"] == "treaty" else "victory")
                changed = True
                continue
        elif deed["kind"] == "quest_done" and deed.get("thread") == th["id"]:
            pulse.end_thread(store, state, th, "resolved", f"{th['title']} - settled by {ws.player.character.name}.", ws.minutes)
            th["result"] = "player"
            changed = True
            continue
        if judge_ok(world, state, th, deed, ws.minutes):
            changed |= judge(ws, state, th, deed)
    if changed or deed.get("dirty"):
        store.save_world_state(state)


def _scope_regions(world, th: dict) -> set[str]:
    regs = set()
    for pid in [th["place"], *th.get("scope_places", [])]:
        if pid in world.places:
            regs.add(world.places[pid].region)
    return regs


def judge_ok(world, state, th, deed, now) -> bool:
    J = E["judge"]
    if th["tier"] not in J["tiers"] or th["stage"] < J["min_stage"] or deed["kind"] not in J["relevant_deeds"]:
        return False
    if th.get("judge_calls", 0) >= J["max_calls"] or now - th.get("judge_last", -10 ** 9) < J["per_day"] * 1440:
        return False
    place = world.places.get(deed.get("place") or "")
    return bool(place and place.region in _scope_regions(world, th))


def judge(ws, state, th, deed) -> bool:
    """Ask the model whether the ledger ended this event. Returns True if the state changed."""
    pulse = _pulse()
    world = ws.world
    th["judge_calls"] = th.get("judge_calls", 0) + 1
    th["judge_last"] = ws.minutes
    mine = [d for d in deeds.since(state, th["made"], E["judge"]["relevant_deeds"])
            if world.places.get(d.get("place") or "") and world.places[d["place"]].region in _scope_regions(world, th)]
    live = "; ".join(f"{s['name']} (boss)" if s["boss"] else f"{s['name']} (kills {s['kills']}/{s['need']})"
                     for s in live_spawns(state, ws.minutes, th["id"])) or ""
    try:
        v = generate("event_judge", pp.JUDGE_SYSTEM, pp.judge_request(th, [deeds.describe(d) for d in mine[-14:]], live),
                     JudgeVerdict, temperature=0.3, max_tokens=300)
    except LLMError as e:
        console.debug(f"event judge: no verdict ({e})")
        return False
    console.debug(f"event judge: {th['title']} -> {v.verdict} ({v.ending}): {v.reason}")
    kinds = {d["kind"] for d in mine}
    if v.verdict == "resolved":
        # hard checks the model cannot talk its way past: a live boss needs more than one kind of deed
        if live_spawns(state, ws.minutes, th["id"]) and any(s["boss"] for s in live_spawns(state, ws.minutes, th["id"])) and len(kinds) < 2:
            v.verdict = "partial"
        elif not mine:
            v.verdict = "no"
    if v.verdict == "resolved":
        finish(ws, state, th, v.reason.rstrip("."), v.ending)
        return True
    if v.verdict == "partial":
        left = th["times"][-1] - ws.minutes
        for i in range(th["stage"] + 1, len(th["times"])):
            th["times"][i] += round(left * E["judge"]["partial_delay"])
        th["partial"] = th.get("partial", 0) + 1
        pulse.add_news(state, f"{th['title']}: word is that {v.reason.rstrip('.').lower()} - it has bought some time.",
                       th["place"], ws.minutes, th["groups"])
        console.note(f"What you have done has set {th['title']} back. It is not over.")
        return True
    return False


def finish(ws, state, th, how: str, ending: str) -> None:
    """The player ended an event. Lift what it did, tell the world, and pay the grand reward for the big ones."""
    pulse = _pulse()
    store, world, t = ws.store, ws.world, ws.minutes
    name = ws.player.character.name
    for e in state.get("effects", []):
        if e.get("cause") == th["title"] and e["kind"] in ("danger", "closed", "prices"):
            e["until"] = min(e["until"], t)
    for s in state.get("spawns", []):
        if s["thread"] == th["id"]:
            s["defeated"] = True
    for camp in state.get("camps", []):
        if camp["thread"] == th["id"]:
            camp["until"] = min(camp["until"], t + 2 * 1440)
    if th.get("triumph"):
        pulse.apply_effects(store, world, ws.catalog, state, th["triumph"].get("effects", []), th["tier"], t, th["title"],
                            raw=True, thread_id=th["id"])
        pulse.add_news(state, th["triumph"]["description"], th["place"], t, th["groups"])
    won = th.get("won_path") or {}
    if won.get("side"):
        loser = world.places[won["side"]].name
        pulse.add_news(state, f"{loser}'s host is broken and its leader is dead; the war is over.", won["side"], t, ["everyone"])
        ps = store.load_place(won["side"])
        ps.marks = (ps.marks + [f"broken in the war ({th['title']})"])[-12:]
        store.save_place(ps)
    pulse.end_thread(store, state, th, "resolved", f"{th['title']} - ended; {name} {how}.", t)
    th["result"] = "player"
    th["ending"] = ending
    if th["tier"] == "cataclysm":
        state["cataclysm_end"] = t
    for pid in {th["place"], *th.get("hit_towns", [])}:
        if pid in world.places:
            try:
                ws.reputation_add(pulse.town_of(world, pid), 6 if th["tier"] == "rare" else 12)
            except Exception:
                pass
    console.note(f"{th['title']} is ended - {how}.")
    if th["tier"] in ("campaign", "cataclysm"):
        grand_reward(ws, state, th)
    store.save_player(ws.player)


# ---------- the grand reward ----------

def _pick_kind(th: dict, rng, exclude: set[str] | None = None) -> str:
    weights = dict(E["grand"][th["tier"]]["kinds"])
    hint = [h for h in th.get("reward_hint", []) if h in weights]
    for k in list(weights):
        if exclude and k in exclude:
            del weights[k]
        elif hint and k not in hint:
            weights[k] = weights[k] * 0.15
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def grand_reward(ws, state, th: dict) -> list[str]:
    """Pay what the survivors owe. Gold always; a keepsake of one kind (two for a cataclysm); a title; reputation."""
    from engine import money, quests
    tier = th["tier"]
    cfg = E["grand"][tier]
    c = ws.player.character
    rng = random.Random(f"{ws.store.meta.seed}:grand:{th['id']}")
    lines = []
    letter = quests.letter_for_level(c.level)
    coins, xp = quests.reward(letter, True)
    gold = coins * cfg["gold_levels"]
    c.coins += gold
    lines.append(f"{money.fmt(gold)}")
    from engine import leveling
    leveling.gain_xp(c, xp * cfg["gold_levels"] // 2)
    kinds = [_pick_kind(th, rng)]
    if cfg.get("second"):
        kinds.append(_pick_kind(th, rng, set(kinds)))
    for kind in kinds:
        text = _grant(ws, state, th, kind, rng, cfg)
        if text:
            lines.append(text)
    title = rng.choice(E["grand"]["titles"])
    where = ws.world.places[_pulse().town_of(ws.world, th["place"])].name if th["place"] in ws.world.places else "the realm"
    full = f"{title} of {where}"
    if full not in ws.player.titles:
        ws.player.titles.append(full)
        lines.append(f"the title {full}")
    ws.reputation_add(_pulse().town_of(ws.world, th["place"]), cfg["reputation"])
    console.note("The survivors give what they can: " + "; ".join(lines) + ".")
    ws.weight_hint = "major"
    ws.narrate(f"The player has ended '{th['title']}'. The people it threatened gather to thank them and press gifts into their "
               f"hands: {'; '.join(lines)}. Describe the moment in two or three sentences, warm and a little awed.")
    ws.store.save_player(ws.player)
    return lines


def _grant(ws, state, th, kind: str, rng, cfg) -> str:
    from engine import items, loot, property as prop
    pulse = _pulse()
    c = ws.player.character
    if kind == "item":
        item = loot.make_drop(c.level + cfg["item_over"], "legendary", rng, loot.keeps_companions(c))
        keep = th.get("keepsake") or ""
        if keep:
            item.name = keep
        item.title = f"relic of {th['title']}"
        ws.to_pack(item)
        return f"{items.display_name(item)}"
    if kind == "deed":
        home_towns = [t for t in prop.P["homes"] if t in ws.world.places and prop.for_sale(t)]
        mine = pulse.town_of(ws.world, th["place"])
        if mine not in home_towns:
            dist = distances(ws.world, th["place"]) if th["place"] in ws.world.places else {}
            home_towns.sort(key=lambda t: dist.get(t, 10 ** 9))
            mine = home_towns[0] if home_towns else ""
        if not mine:
            return ""
        if mine in ws.player.homes:
            h = ws.player.homes[mine]
            if h.get("ruined"):
                h["ruined"] = False
                ws.ensure_homes()
                return f"your ruined house in {ws.world.places[mine].name} rebuilt at their cost"
            owned = set(h["upgrades"])
            free = next((u for u in ("strongroom", "reliquary", "hearth", "workshop", "garden") if u in prop.P["upgrades"] and u not in owned), None)
            if free:
                h["upgrades"].append(free)
                ws.ensure_homes()
                return f"a {prop.P['upgrades'][free]['name']} built free at your house in {ws.world.places[mine].name}"
            return ""
        ws.player.homes[mine] = {"day": clock.day(ws.minutes), "upgrades": [], "last_garden": -1, "last_hearth": -1}
        ws.ensure_homes()
        return f"the deed to {prop.P['homes'][mine]['name']} in {ws.world.places[mine].name}"
    if kind == "mount":
        have = {m["id"] for m in ws.player.mounts}
        pool = {k: v for k, v in E["grand"]["mounts"].items() if v["min_level"] <= c.level and k not in have}
        if not pool:
            return ""
        best = [k for k, v in pool.items() if v["speed"] >= max(x["speed"] for x in pool.values()) - 0.15] or list(pool)
        key = rng.choice(best)
        m = dict(pool[key], id=key)
        ws.player.mounts.append(m)
        if not ws.player.mount:
            ws.player.mount = key
        return f"{m['name']}, yours to ride (it speeds your travel)"
    return ""


# ---------- allies ----------

def recruit_allies(ws, enemies) -> None:
    """Before a fight with an event's boss: people of the realm who trust the player and are in the path come to fight beside them."""
    pulse = _pulse()
    cfg = E["allies"]
    spawn_ids = {getattr(e, "spawn", "") for e in enemies} - {""}
    if not spawn_ids:
        return
    state = ws.store.load_world_state()
    s = next((x for x in state.get("spawns", []) if x["id"] in spawn_ids and x["boss"]), None)
    th = next((x for x in state.get("threads", []) if s and x["id"] == s["thread"] and x["status"] == "active"), None)
    if not th or th["tier"] not in ("campaign", "cataclysm"):
        return
    from engine import party
    room = party.P["max_party"] - len(ws.player.party)
    if room <= 0:
        return
    towns = {pulse.town_of(ws.world, th["place"]), *th.get("hit_towns", [])} - {s.get("side")}
    cands = []
    for nid in ws.store.list_npcs():
        n = ws.store.load_npc(nid)
        if n.gone or n.tier == "background" or n.trust < cfg["min_trust"] or n.role not in cfg["roles"]:
            continue
        if pulse.town_of(ws.world, n.location) in towns and not any(m.get("npc") == n.id for m in ws.player.party):
            cands.append(n)
    cands.sort(key=lambda n: -n.trust)
    lvl = ws.player.character.level
    joined = []
    for n in cands[:min(room, cfg["max_join"])]:
        r = cfg["roles"][n.role]
        ws.player.party.append({"id": f"npc_{n.id}", "name": n.name, "role": r["party"], "level": max(1, round(lvl * r["share"])),
                                "blurb": f"{n.name}, {n.role.replace('_', ' ')}", "npc": n.id, "event": th["id"]})
        joined.append(n.name)
    if joined:
        console.note(f"{', '.join(joined)} {'comes' if len(joined) == 1 else 'come'} to stand with you against {s['name']}.")
        ws.store.save_player(ws.player)


def fallen_allies(ws, fallen_ids: set[str]) -> None:
    """A realm-ally who went down may die (a roll), or be carried out. Called after every fight."""
    pulse = _pulse()
    rng = random.Random()
    for m in [m for m in ws.player.party if m.get("npc")]:
        if f"ally_{m['id']}" in fallen_ids:
            n = ws.store.load_npc(m["npc"])
            if rng.random() < E["allies"]["death_when_down"]:
                pulse.remove_npc(ws.store, ws.world, n, f"died fighting beside {ws.player.character.name}", ws.minutes)
                console.note(f"{n.name} is dead. They gave their life in the fight.")
                _vacancy(ws.store, ws.world, n, ws.minutes, random.Random())
                pulse.add_news(ws.store.load_world_state() or {}, f"{n.name} fell fighting beside {ws.player.character.name}.",
                               n.location, ws.minutes, ["everyone"])
            else:
                console.note(f"{n.name} is carried out of the fight, badly hurt but alive.")
                n.mood = "badly wounded, but alive"
                ws.store.save_npc(n)


def release_allies(ws) -> None:
    """The fight is over; realm-allies go home."""
    left = [m for m in ws.player.party if m.get("npc")]
    if not left:
        return
    ws.player.party = [m for m in ws.player.party if not m.get("npc")]
    alive = [m["name"] for m in left if not ws.store.load_npc(m["npc"]).gone]
    if alive:
        console.note(f"{', '.join(alive)} {'goes' if len(alive) == 1 else 'go'} back to the work of rebuilding.")
    ws.store.save_player(ws.player)


# ---------- cataclysm: when ----------

def cataclysm_due(state: dict, t: int, level: int, rng: random.Random) -> bool:
    if level < C["gate_level"]:
        return False
    if t - state.get("cataclysm_end", -10 ** 9) < C["min_gap_days"] * 1440:
        return False
    if not state.get("cataclysms") and level >= C["guaranteed_by_level"]:
        return True
    ch = C["chance"]
    frac = min(1.0, max(0.0, (level - C["gate_level"]) / max(1, ch["end_level"] - C["gate_level"])))
    return rng.random() < ch["start"] + (ch["end"] - ch["start"]) * frac


# ---------- cataclysm: the structure ----------

def _boss_creature(world, kind: dict, level: int, rng: random.Random):
    pool = [c for c in world.bestiary.values() if c.roster and not c.unique and c.category in kind["boss_categories"]
            and c.levels[1] >= level - 5]
    if not pool:
        pool = [c for c in world.bestiary.values() if c.roster and not c.unique and c.levels[1] >= level - 5]
    pool.sort(key=lambda c: abs(((c.levels[0] + c.levels[1]) // 2) - (level + 4)) - (8 if c.rarity == "legendary" else 3 if c.rarity == "rare" else 0))
    return rng.choice(pool[:6]) if pool else None


def _human(world, pool: list[str], level: int, rng: random.Random, avoid: set | None = None):
    """A person-shaped creature for a war captain or leader: the template whose levels sit nearest the wanted level."""
    ok = [world.bestiary[i] for i in pool if i in world.bestiary]
    ok.sort(key=lambda c: (abs((c.levels[0] + c.levels[1]) // 2 - level) + (6 if avoid and c.id in avoid else 0), c.id))
    return rng.choice(ok[:3]) if ok else None


def _leaders(store, world, catalog, kind: dict, origin, chosen: list, rng: random.Random) -> list[dict]:
    """The two sides of a war: someone of standing in the origin town and in a rival town. Returns [{id, name, role, town}]."""
    from npc.life import populate_place
    pulse = _pulse()
    rivals = [world.places[o] for o in kind["origin"] if o in world.places and o != origin.id]
    dist = distances(world, origin.id)
    rivals.sort(key=lambda p: (dist.get(p.id, 10 ** 9), p.id))
    towns = [origin] + (rivals[:1] or [p for p in chosen if p.id != origin.id][:1])
    out = []
    for town in towns:
        if town.id not in {p.id for p in settlements(world)}:
            continue
        spots = [p for p in world.places.values() if pulse.town_of(world, p.id) == town.id and p.residents]
        for spot in spots:
            try:
                populate_place(store, world, spot.id, None)
            except Exception as err:
                console.debug(f"war leaders: could not populate {spot.id} ({err})")
        best = None
        for role in C["leader_roles"]:
            for spot in spots:
                for nid in store.load_place(spot.id).residents:
                    n = store.load_npc(nid)
                    if not n.gone and n.role == role:
                        best = n
                        break
                if best:
                    break
            if best:
                break
        if best:
            out.append({"id": best.id, "name": best.name, "role": best.role, "town": town.id})
    return out


def start_cataclysm(store, world, catalog, state, t: int, rng: random.Random) -> bool:
    pulse = _pulse()
    level = player_level(store)
    kinds = {k: v for k, v in C["kinds"].items() if any(o in world.places for o in v["origin"])}
    if not kinds:
        return False
    kid = rng.choices(list(kinds), weights=[kinds[k]["weight"] for k in kinds])[0]
    kind = kinds[kid]
    origin = world.places[rng.choice([o for o in kind["origin"] if o in world.places])]
    dist = distances(world, origin.id)
    towns = [p for p in settlements(world)]
    towns.sort(key=lambda p: (dist.get(p.id, 10 ** 9), p.id))
    chosen = [p for p in towns if p.id != origin.id][:kind["towns"]]
    if not origin.danger and origin.id in {p.id for p in towns}:
        chosen = [origin] + chosen[:kind["towns"] - 1]
    stages_n = C["stages"]
    hits: list[list[str]] = []
    idx = 0
    for n in C["spread"][:stages_n]:
        hits.append([p.id for p in chosen[idx:idx + n]])
        idx += n
    if idx < len(chosen):
        hits[-1].extend(p.id for p in chosen[idx:])
    has_boss = rng.random() < kind.get("boss_chance", 1.0)
    boss_c = _boss_creature(world, kind, level, rng) if has_boss else None
    if has_boss and not boss_c:
        return False
    boss_zone = nearest_zone(world, origin.id, level)
    days = [rng.randint(*C["stage_days"]) for _ in range(stages_n)]
    times = [t]
    for d in days:
        times.append(times[-1] + d * 1440)
    boss_stage = min(2, stages_n - 1)
    boss_level = level + rng.randint(*C["boss_levels_over"])
    thread_id = uuid.uuid4().hex[:8]
    boss = add_spawn(store, world, state, thread_id, boss_zone.id, boss_c.id, True, t, days=sum(days) + 60, level=boss_level,
                     live_from=times[boss_stage], tier="cataclysm") if boss_c else None
    host_cat = boss_c.category if boss_c else rng.choice(kind["boss_categories"])
    minions = []
    for tid in [h for step in hits for h in step][:2]:
        zone = nearest_zone(world, tid, level)
        cands = [c for c in world.bestiary.values() if c.roster and not c.unique and c.category == host_cat
                 and c.levels[1] >= level - 20 and (not boss_c or c.id != boss_c.id)] or \
                [c for c in world.bestiary.values() if c.roster and not c.unique and c.levels[1] >= level - 20 and (not boss_c or c.id != boss_c.id)]
        if zone and cands:
            m = add_spawn(store, world, state, thread_id, zone.id, rng.choice(cands).id, False, t, days=sum(days) + 30,
                          level=max(1, level - rng.randint(0, 6)), live_from=times[min(1, stages_n - 1)], need=3)
            if m:
                minions.append(m)
    leaders = _leaders(store, world, catalog, kind, origin, chosen, rng) if kind.get("leaders") else []
    hosts = {}                     # leader's town -> the spawn ids of that side's war captains and then its leader
    if len(leaders) >= 2:
        for lead in leaders:
            caps = []
            for k in range(kind.get("captains", 2)):
                cc = _human(world, kind.get("captain_pool", []), level, rng) or _boss_creature(world, kind, level, rng)
                if cc:
                    cap = add_spawn(store, world, state, thread_id, lead["town"], cc.id, True, t, days=sum(days) + 60,
                                    level=max(1, boss_level - 3), live_from=times[min(1, stages_n - 1)],
                                    name=f"a war captain of {world.places[lead['town']].name}", hp_mult=kind.get("captain_health", 2.5),
                                    side=lead["town"], tier="captain", kit="person")
                    if cap:
                        caps.append(cap["id"])
            lc = _human(world, kind.get("leader_pool", []), level + 8, rng) or _boss_creature(world, kind, level, rng)
            ls = add_spawn(store, world, state, thread_id, lead["town"], lc.id, True, t, days=sum(days) + 60, level=boss_level,
                           live_from=times[min(2, stages_n - 1)], name=lead["name"], after=caps, side=lead["town"], npc=lead["id"], tier="leader", kit="person") if lc else None
            if ls:
                hosts[lead["town"]] = ls["id"]
    # ask the model for the telling
    path_ids = (["kill_boss"] if boss else []) + (["peace"] + [f"fight_{l['town']}" for l in leaders] if len(leaders) >= 2 else []) + (["break_the_host"] if minions else []) + \
               (["guild_job"] if boss else [])
    names = {p.id: p.name for p in world.places.values()}
    lines = []
    for i in range(stages_n):
        if i == 0:
            lines.append(f"  1: omens only, around {origin.name}; no town is hit yet")
        else:
            lines.append(f"  {i + 1}: " + (", ".join(names[h] for h in hits[i]) or "the trouble deepens around the origin") + " are hit")
    request = (f"KIND: {kid} - {kind['about']}\nORIGIN: {origin.id} - {origin.name} ({origin.type}), {world.regions[origin.region].name}\n" +
               (f"BOSS: {boss_c.name} ({boss_c.category}) - it will be found in {boss_zone.name} from stage {boss_stage + 1}\n" if boss_c else
                "BOSS: none - there is no single monster to slay; the trouble is carried by people and armies\n") +
               (("LEADERS (each can end it by being won over): " + "; ".join(f"{l['name']}, {l['role'].replace('_', ' ')} of {world.places[l['town']].name}" for l in leaders) + "\n" +
                 "PEACE: talk both leaders round.  FIGHT_<town>: take the other side and break that town's host - its war captains first, then its leader.\n") if leaders else "") +
               f"MINIONS: {', '.join(sorted({world.bestiary[m['creature']].name for m in minions})) or 'none'}\n"
               f"PATHS (write one for each id): {', '.join(path_ids)}\nSTAGES: {stages_n}\n" + "\n".join(lines) +
               f"\nPLAYER LEVEL: {level}")
    try:
        proposal = generate("pulse_cataclysm", pp.CATACLYSM_SYSTEM, request, CataclysmProposal, temperature=0.9, max_tokens=2400,
                            validation_context={"stages": stages_n})
    except LLMError as e:
        console.debug(f"cataclysm: not this time ({e})")
        state["spawns"] = [s for s in state.get("spawns", []) if s["thread"] != thread_id]
        return False
    pathtext = {p.id: p for p in proposal.paths}
    if boss and proposal.boss_lines:
        boss["lines"] = proposal.boss_lines.model_dump()
    for lead, ln in zip(leaders, proposal.side_lines):
        for sid in state.get("spawns", []):
            if sid.get("side") != lead["town"] or sid["thread"] != thread_id:
                continue
            d = ln.model_dump()
            if sid.get("tier") == "captain":
                sid["lines"] = {"intro": d.get("captain_intro", "")}
            elif sid.get("tier") == "leader":
                d.pop("captain_intro", None)
                sid["lines"] = d
    # engine-built effects for each stage
    stage_rows = []
    town_stage = {}
    for i, step in enumerate(hits):
        for h in step:
            town_stage.setdefault(h, i)
    for i, cs in enumerate(proposal.stages):
        eff = []
        for h in hits[i]:
            eff.append({"kind": "prices", "place": h, "value": rng.randint(*C["towns_prices"]), "days": days[i] + 5})
            eff.append({"kind": "danger", "place": h, "value": rng.randint(*C["towns_danger"]), "days": days[i] + 5})
        if i == 0:
            eff.append({"kind": "danger", "place": origin.id, "value": 40, "days": days[0] + 5})
        stage_rows.append({"description": f"{cs.name}: {cs.description}", "effects": eff, "name": cs.name, "signs": cs.signs})
    paths = []
    if boss:
        txt = pathtext.get("kill_boss")
        paths.append({"id": "kill_boss", "name": txt.name if txt else f"Slay {boss['name']}",
                      "how": (txt.how if txt else f"{boss['name']} must fall."), "kind": "kill", "target": boss_c.id,
                      "spawn": boss["id"], "done": False})
    if len(leaders) >= 2:
        txt = pathtext.get("peace")
        paths.append({"id": "peace", "name": txt.name if txt else "Make peace", "kind": "treaty", "target": ",".join(l["id"] for l in leaders),
                      "how": (txt.how if txt else "Win over " + " and ".join(l["name"] for l in leaders) + "."), "spawn": "", "done": False})
    for lead in leaders:
        if lead["town"] in hosts:
            other = next(l for l in leaders if l is not lead)
            txt = pathtext.get(f"fight_{lead['town']}")
            tname = world.places[lead["town"]].name
            paths.append({"id": f"fight_{lead['town']}", "kind": "kill", "target": "", "spawn": hosts[lead["town"]], "done": False,
                          "side": lead["town"], "name": txt.name if txt else f"Side with {world.places[other['town']].name}: break {tname}",
                          "how": txt.how if txt else f"Take {world.places[other['town']].name}'s side: cut down the war captains of {tname}, then {lead['name']}."})
    if minions:
        txt = pathtext.get("break_the_host")
        paths.append({"id": "break_the_host", "name": txt.name if txt else "Break the host",
                      "how": (txt.how if txt else "Cut down what the power sends out."), "kind": "horde", "target": "",
                      "spawn": ",".join(m["id"] for m in minions), "done": False})
    thread = {"id": thread_id, "title": proposal.title, "tier": "cataclysm", "kind": kid, "place": origin.id,
              "pressure": "", "stage": 0, "times": times, "status": "active", "stages": stage_rows,
              "fallout": {"description": proposal.ignored or "The land is changed for good.",
                          "effects": [{"kind": "mark", "place": origin.id, "text": f"scarred by {proposal.title}"}]},
              "resolution": "; ".join(f"{p['name']}: {p['how']}" for p in paths), "made": t,
              "groups": ["everyone"], "paths": paths, "hit_towns": [h for step in hits for h in step], "hits": hits,
              "scope_places": [h for step in hits for h in step] + [boss_zone.id] + [l["town"] for l in leaders],
              "boss": boss["id"] if boss else "", "leaders": leaders,
              "antagonist": proposal.antagonist or (boss_c.name if boss_c else "the war"), "keepsake": proposal.keepsake, "fallen": [], "level": level,
              "triumph": {"description": proposal.triumph or "The danger passes, and the survivors begin to rebuild.",
                          "effects": [{"kind": "mark", "place": origin.id, "text": f"{proposal.title} was ended here"}]}}
    state["threads"].append(thread)
    state["campaign"] = thread_id
    state["cataclysms"] = state.get("cataclysms", 0) + 1
    pulse.add_news(state, proposal.news, origin.id, t, ["everyone"])
    pulse.apply_effects(store, world, catalog, state, stage_rows[0]["effects"], "cataclysm", t, thread["title"], raw=True, thread_id=thread_id)
    console.debug(f"cataclysm: [{kid}] {proposal.title} from {origin.id}, boss {boss_c.id + ' L' + str(boss_level) if boss_c else 'none'}")
    return True


# ---------- cataclysm: stages, falls, deaths ----------

def on_stage(store, world, catalog, state, th: dict, t: int, rng: random.Random) -> None:
    """A cataclysm has moved on to th['stage']. Roll what happens to the towns it reaches and warn the ones in its path."""
    pulse = _pulse()
    i = th["stage"]
    hits = th["hits"]
    sig = th["stages"][i].get("signs")
    if sig:
        pulse.add_news(state, sig, th["place"], t, th["groups"])
    for town in hits[i] if i < len(hits) else []:
        town_outcome(store, world, catalog, state, th, town, i, t, rng)
    ahead = i + C["warn_stages"]
    if ahead < len(hits):
        for town in hits[ahead]:
            name = world.places[town].name
            pulse.add_news(state, f"{name} lies in the path of {th['title']}. Those who can are leaving, and those who cannot are "
                                  f"making ready.", town, t, ["everyone"])
            state.setdefault("player_events", []).append({"kind": "warn", "town": town, "title": th["title"]})
    if i == min(2, len(th["stages"]) - 1):
        post_boss_contract(store, world, state, th, t)


def post_boss_contract(store, world, state, th: dict, t: int) -> None:
    from engine import quests
    boss = next((s for s in state.get("spawns", []) if s["id"] == th.get("boss")), None)
    if not boss:
        return
    pulse = _pulse()
    halls = [p.id for p in world.places.values() if p.type == "guild"]
    if not halls:
        return
    dist = distances(world, boss["place"])
    gid = min(halls, key=lambda h: dist.get(h, 10 ** 9))
    c = world.bestiary[boss["creature"]]
    letter = quests.letter_for_level(boss["level"] or th["level"])
    q = quests._quest("hunt", letter, f"Slay {boss['name']} ({th['title']})", t, place=boss["place"], creature=c.id, count=1,
                      guild=True, issuer="guild", issuer_name="the guild")
    q["thread"] = th["id"]
    q["multiplier"] = pulse_mult("cataclysm")
    gs = store.load_place(gid)
    gs.board.append(q)
    store.save_place(gs)
    th["paths"].append({"id": "guild_job", "name": "Finish the guild's job", "how": "Complete the contract the guild posted.",
                        "kind": "contract", "target": "", "spawn": "", "done": False})


def pulse_mult(tier: str) -> float:
    return E["contract_tier_mult"].get(tier, 1.0)


def boss_dead(state: dict, th: dict) -> bool:
    s = next((x for x in state.get("spawns", []) if x["id"] == th.get("boss")), None)
    return bool(s and s["defeated"])


def town_outcome(store, world, catalog, state, th, town: str, stage_i: int, t: int, rng: random.Random) -> None:
    """A town is hit. It falls or holds by a roll; people are caught by the result; homes may be ruined."""
    pulse = _pulse()
    cfg = C["fall"]
    kind = C["kinds"][th["kind"]]
    p = (cfg["base"] + cfg["per_stage"] * stage_i) * kind["fall_mult"]
    if boss_dead(state, th):
        p *= cfg["boss_dead"]
    for path in th.get("paths", []):
        if path["kind"] == "treaty":
            won = sum(1 for i in path["target"].split(",") if i and _won_over(state, th["made"], i))
            p *= C["treaty_fall_halving"] ** won
    present = False
    if store.player_exists():
        try:
            present = pulse.town_of(world, store.load_player().location) == town
        except Exception:
            pass
    if present:
        p *= cfg["player_present"]
    fell = rng.random() < p
    name = world.places[town].name
    refuge = _refuge(world, th, town)
    caught = _catch_people(store, world, state, th, town, fell, refuge, t, rng)
    if fell:
        state.setdefault("effects", []).append({"kind": "danger", "place": town, "value": 40, "until": t + 40 * 1440, "cause": th["title"]})
        ps = store.load_place(town)
        ps.marks = (ps.marks + [f"half in ruin after {th['title']}"])[-12:]
        store.save_place(ps)
        th.setdefault("fallen", []).append(town)
        pulse.add_news(state, f"{name} has fallen. {_toll_text(caught)}", town, t, ["everyone"])
        state.setdefault("player_events", []).append({"kind": "fell", "town": town, "title": th["title"], "present": present,
                                                      "roll": rng.random()})
    else:
        if caught["dead"] or caught["fled"]:
            pulse.add_news(state, f"{name} held. {_toll_text(caught)}", town, t, ["everyone"])
        else:
            pulse.add_news(state, f"{name} held against {th['title']}.", town, t, ["everyone"])


def _toll_text(caught: dict) -> str:
    bits = []
    if caught["dead"]:
        shown = ", ".join(caught["dead"][:4]) + (f" and {len(caught['dead']) - 4} more" if len(caught["dead"]) > 4 else "")
        bits.append(f"The dead include {shown}.")
    if caught["fled"]:
        bits.append(f"{len(caught['fled'])} fled.")
    return " ".join(bits) or "No one of note was lost."


def _refuge(world, th: dict, town: str) -> str:
    unhit = [p for p in settlements(world) if p.id not in th.get("hit_towns", []) and world.peoples_at(p.id)]
    if not unhit:
        return ""
    dist = distances(world, town)
    return min(unhit, key=lambda p: dist.get(p.id, 10 ** 9)).id


def _catch_people(store, world, state, th, town: str, fell: bool, refuge: str, t: int, rng: random.Random) -> dict:
    pulse = _pulse()
    out = {"dead": [], "fled": []}
    base = C["toll"]["falls" if fell else "holds"]
    lost_roles = []
    for nid in store.list_npcs():
        n = store.load_npc(nid)
        if n.gone or pulse.town_of(world, n.location) != town:
            continue
        risk = base * C["role_risk"].get(n.role, 1.0)
        if n.tier != "background":
            risk *= C["met_risk"]
        risk *= 1 - min(0.4, max(0.0, (n.trust - 50) * C["trust_shield"]))
        if rng.random() >= risk:
            continue
        if refuge and rng.random() < C["flee_share"]:
            n.mood = f"shaken, a refugee from {world.places[town].name}"
            n.memories.append(_memory(t, f"Fled {world.places[town].name} when {th['title']} came."))
            store.save_npc(n)
            pulse.move_npc(store, n, refuge)
            out["fled"].append(n.name)
        else:
            how = (f"killed when {world.places[town].name} fell to {th['antagonist']}" if fell
                   else f"killed defending {world.places[town].name} against {th['antagonist']}")
            pulse.remove_npc(store, world, n, how, t)
            out["dead"].append(n.name + (f" ({n.role.replace('_', ' ')})" if n.role.startswith("guild") or n.role in ("priest", "smith") else ""))
        lost_roles.append((n.role, n.location))
    for role, loc in lost_roles:
        _vacancy_for(state, world, loc, role, t, rng)
    if refuge and lost_roles:
        ps = store.load_place(refuge)
        for role, _ in lost_roles[:C["refugees"]]:
            if role in world.roles and not role.startswith("guild"):
                ps.extra_roles[role] = ps.extra_roles.get(role, 0) + 1
        store.save_place(ps)
    return out


def _memory(t: int, text: str):
    from npc.models import Memory
    return Memory(day=clock.day(t), turn=-1, text=text)


def _vacancy_for(state: dict, world, place_id: str, role: str, t: int, rng: random.Random) -> None:
    if place_id not in world.places or role not in world.places[place_id].residents:
        return
    lo, hi = C["vacancy_days"].get(role, C["vacancy_days"]["default"])
    until = t + rng.randint(lo, hi) * 1440
    state.setdefault("vacancies", {}).setdefault(place_id, {})[role] = until


def _vacancy(store, world, npc, t: int, rng: random.Random) -> None:
    state = store.load_world_state()
    if state is None:
        return
    _vacancy_for(state, world, npc.location, npc.role, t, rng)
    store.save_world_state(state)


def vacant_roles(store, place_id: str, now: int) -> dict[str, int]:
    """Roles at this place whose post is still empty after a death or flight (so no replacement is generated yet)."""
    state = store.load_world_state() or {}
    v = state.get("vacancies", {}).get(place_id, {})
    return {r: u for r, u in v.items() if u > now}


# ---------- what the player sees ----------

def apply_player_events(ws) -> None:
    """Pending notices for the player: warnings for homes in the path, homes lost. Called by the scene after the pulse runs."""
    store = ws.store
    state = store.load_world_state()
    if not state or not state.get("player_events"):
        return
    evs, state["player_events"] = state["player_events"], []
    rng = random.Random(f"{store.meta.seed}:homes:{ws.minutes}")
    changed = False
    for ev in evs:
        town = ev["town"]
        name = ws.world.places[town].name
        home = ws.player.homes.get(town)
        if ev["kind"] == "warn" and home and not home.get("ruined"):
            fort = "fortify" in home["upgrades"]
            console.note(f"Word comes that {name} lies in the path of {ev['title']}. Your house there is in danger"
                         + (" - though it is fortified." if fort else ". Walls (the Fortify upgrade) or your own presence would help."))
        elif ev["kind"] == "fell" and home and not home.get("ruined"):
            p = C["home"]["fortified" if "fortify" in home["upgrades"] else "ruin_when_falls"]
            if rng.random() < p:
                home["ruined"] = True
                changed = True
                console.note(f"{name} has fallen - and your house there is a ruin. Your things are safe in the item box. "
                             f"You can rebuild it for {C['home']['rebuild_share']:.0%} of its price.")
            else:
                console.note(f"{name} has fallen, but your house stands.")
    store.save_world_state(state)
    if changed:
        ws.ensure_homes()
        store.save_player(ws.player)


def after_ignored(store, world, state, th: dict, t: int) -> None:
    """A cataclysm ran its course with no one ending it: its creatures stay in the world for good, and the land remembers."""
    for s in state.get("spawns", []):
        if s["thread"] == th["id"] and not s["defeated"]:
            s["until"] = t + 3650 * 1440
            s["from"] = min(s["from"], t)
    for town in th.get("fallen", []):
        state.setdefault("effects", []).append({"kind": "prices", "place": town, "value": 30, "until": t + 60 * 1440, "cause": th["title"]})
