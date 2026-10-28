"""(f367) Starting points: shape a save as if a character had already lived part of the game.

Why: every night run began the same way, level 13, nobody's acquaintance, no past, so the systems that key on a history (the summons
that needs a reputation, the hall that notices finished jobs, townsfolk who know a name, a campaign earned by what was settled before)
were never exercised. data/rules/starts.yaml names starting points; apply() makes the save match one: the clock moved on, the guild's
record, reputation, standing and heat by town, people already met, titles, and situations already over, built by the engine from the
town's own pressures and remembered by the town as settled by the player or let be. Nothing here calls a model but the making of
townsfolk to have met."""
from __future__ import annotations

import random
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "starts.yaml").read_text(encoding="utf-8"))
TOWN_KEYS = ("home", "near", "region")


def names() -> list[str]:
    return list(S.get("starts") or {})


def rotation() -> list[str]:
    return list(S.get("rotation") or names())


def spec(name: str) -> dict:
    return dict((S.get("starts") or {}).get(name) or {})


def towns_for(world, start_location: str) -> dict[str, list[str]]:
    """The town keys a start may name: home (the start's town, or the nearest town when play begins in the open, as it does in the south
    fields outside Parth), near (the nearest other town), region (the home region's others)."""
    from engine import pulse
    settled = [p for p in world.places.values() if not p.parent and p.type not in ("dungeon", "road", "home") and not p.danger and world.peoples_at(p.id)]

    def walk(a: str, b: str) -> int:
        found = world.path(a, b) if a != b else ([a], 0)
        return found[1] if found else 10 ** 9
    start_town = pulse.town_of(world, start_location)
    home = start_town if any(p.id == start_town for p in settled) else min(settled, key=lambda p: walk(start_location, p.id)).id
    towns = [p for p in settled if p.id != home]
    near = sorted(towns, key=lambda p: walk(home, p.id))[:1]
    region = [p.id for p in towns if p.region == world.places[home].region and p not in near]
    return {"home": [home], "near": [p.id for p in near], "region": region}


def resolve(world, key: str, towns: dict) -> list[str]:
    if key in towns:
        return list(towns[key])
    return [key] if key in world.places else []


def apply(store, world, catalog, player, name: str, rng: random.Random, who: str) -> dict:
    """Make the save match the start. The player is saved at their start location already; their level, gear and rank are the caller's
    (they need the class). Returns what was done: the days, the situations made, the people met."""
    from engine import clock, pulse, standing
    from npc.life import populate_place
    sp = spec(name)
    if not sp:
        raise KeyError(f"no start named '{name}' (data/rules/starts.yaml)")
    now = max(store.meta.minutes, int(sp.get("days", 0)) * 1440 + 8 * 60)
    store.meta.minutes = now
    store.save_meta()
    day = clock.day(now)
    towns = towns_for(world, player.location)
    state = store.load_world_state() or pulse.empty_state(now)
    done = {"start": name, "days": int(sp.get("days", 0)), "situations": [], "met": 0}
    if sp.get("rank"):
        player.guild_rank = sp["rank"]
    if sp.get("contracts_done"):
        player.guild_done = {k: int(v) for k, v in sp["contracts_done"].items()}
    if sp.get("titles"):
        player.titles = list(sp["titles"])
    for key, value in (sp.get("reputation") or {}).items():
        for town in resolve(world, key, towns):
            player.reputation[town] = int(value)
    for key, groups in (sp.get("standing") or {}).items():
        for town in resolve(world, key, towns):
            for group, value in (groups or {}).items():
                standing.add(player, town, group, float(value), day)
    for key, value in (sp.get("heat") or {}).items():
        for town in resolve(world, key, towns):
            player.heat[town] = {"heat": int(value), "day": day}
    for key, m in (sp.get("met") or {}).items():
        for town in resolve(world, key, towns):
            residents = populate_place(store, world, town, catalog, first_batch=None)
            for n in residents[:int((m or {}).get("people", 4))]:
                n.met_player = True
                n.name_known_to_player = True
                n.trust = max(0, min(100, int((m or {}).get("trust", 55)) + rng.randint(-6, 6)))
                n.last_talk_day = max(0, day - rng.randint(1, 20))
                store.save_npc(n)
                done["met"] += 1
    for p in sp.get("past") or []:
        for town in resolve(world, (p or {}).get("where", "home"), towns)[:1]:
            th = past_situation(store, world, state, player, town, p, now, rng, who)
            if th:
                done["situations"].append(f"{th['title']} ({th['tier']}, {p.get('how', 'settled')})")
    store.save_world_state(state)
    store.save_player(player)
    return done


def past_situation(store, world, state: dict, player, town: str, p: dict, now: int, rng: random.Random, who: str) -> dict | None:
    """A situation already over: built by the engine from one of the town's pressures at its tier, ended days ago, and remembered the
    way a lived one is: a finished record, a line of history, old news, the town's memory, a deed and reputation when the player
    settled it, a cataclysm counted when that is what it was. None when nothing fits the town."""
    from engine import matters, pulse, threads
    tier = p.get("tier", "uncommon")
    how = p.get("how", "settled")
    settled = how == "settled"
    t0 = now - int(p.get("days_ago", 30)) * 1440
    place = world.places[town]
    pool = list(world.pressures.values())
    if tier in ("campaign", "cataclysm"):
        pool = [x for x in pool if x.campaign] or pool
    mine = [x for x in pool if x.place == town or pulse.town_of(world, x.place) == town or x.place == place.region] or pool
    pressure = rng.choice(mine) if mine else None
    built = threads.build(store, world, state, place, pressure, tier, rng, t0)
    if not built:
        return None
    proposal, info = built
    rule = pulse.P["tiers"].get(tier) or {"days": [1, 2]}
    t1 = min(now - 1440, t0 + rng.randint(1, max(2, int(rule["days"][0]))) * 1440)
    n = len(proposal.stages)
    th = {"id": uuid.uuid4().hex[:8], "title": proposal.title, "tier": tier, "place": town,
          "kind": getattr(proposal, "kind", "") or threads.kind_of(info["template"]), "pressure": pressure.id if pressure else "",
          "stage": max(0, n - 1), "status": "resolved" if settled else "ended", "made": t0, "ended_at": t1,
          "stages": [s.model_dump() for s in proposal.stages], "fallout": proposal.fallout.model_dump(),
          "times": [t0 + i * 1440 for i in range(n + 1)], "groups": list(getattr(proposal, "groups", None) or ["everyone"]),
          "paths": [], "contract": None, "made_by": "engine", "told": True, "template": info["template"], "severity": info["severity"],
          "result": "player" if settled else "", "ending": "by the stranger's hand" if settled else "", "started_as": "past"}
    state.setdefault("threads", []).append(th)
    line = (f"{th['title']} - ended; {who} settled it." if settled
            else f"{th['title']} - left alone, so the fallout landed: {proposal.fallout.description[:120]}")
    state.setdefault("history", []).append({"minute": t1, "text": line, "place": town})
    pulse.add_news(state, line, town, t1, th["groups"], thread=th["id"])
    if pressure:
        state.setdefault("cooldowns", {})[pressure.id] = t1
    matters.remember(store, world, th, how, who, t1, 1)
    if settled:
        state.setdefault("deeds", []).append({"kind": "settled", "minute": t1, "place": town, "thread": th["id"], "title": th["title"],
                                              "tier": tier, "how": "by the stranger's hand"})
        player.reputation[town] = player.reputation.get(town, 0) + int(matters.D["memory"]["reputation"].get(tier, 6))
    if tier == "cataclysm":
        state["cataclysm_end"] = max(int(state.get("cataclysm_end", 0) or 0), t1)
        state["cataclysms"] = int(state.get("cataclysms", 0) or 0) + 1
    return th


def problems(groups=(), tiers=(), ranks=()) -> list[str]:
    bad = []
    starts = S.get("starts") or {}
    if not starts:
        bad.append("starts.yaml: needs at least one start")
    for name, sp in starts.items():
        sp = sp or {}
        if not isinstance(sp.get("level", 1), int) or int(sp.get("level", 1)) < 1:
            bad.append(f"starts.yaml {name}: level is a whole number from 1")
        days = sp.get("days", 0)
        if not isinstance(days, int) or days < 0:
            bad.append(f"starts.yaml {name}: days is a whole number")
        if sp.get("rank") and ranks and sp["rank"] not in ranks:
            bad.append(f"starts.yaml {name}: rank '{sp['rank']}' is not a guild rank")
        for town, gs in (sp.get("standing") or {}).items():
            for g in (gs or {}):
                if groups and g not in groups:
                    bad.append(f"starts.yaml {name}: standing group '{g}' is not in standing.yaml")
        for p in sp.get("past") or []:
            p = p or {}
            if tiers and p.get("tier", "uncommon") not in tiers:
                bad.append(f"starts.yaml {name}: past tier '{p.get('tier')}' is not a tier")
            if p.get("how", "settled") not in ("settled", "ignored"):
                bad.append(f"starts.yaml {name}: past how is settled or ignored")
            if int(p.get("days_ago", 30)) >= int(days or 0):
                bad.append(f"starts.yaml {name}: a past situation's days_ago must be within the start's days")
    for r in S.get("rotation") or []:
        if r not in starts:
            bad.append(f"starts.yaml rotation: '{r}' is not a start")
    return bad
