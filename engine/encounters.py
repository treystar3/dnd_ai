"""Encounters: each dangerous place gets a saved roster of creature kinds on first visit, and
encounters are rolled from it when the player arrives or lingers."""

import random
from pathlib import Path

import yaml

from engine import combat, events

CREATURE_RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "creatures.yaml").read_text(encoding="utf-8"))
E = combat.RULES["encounters"]


def ensure_roster(store, world, place_id: str) -> list[str]:
    state = store.load_place(place_id)
    anchors = world.places[place_id].anchors
    if state.roster:
        missing = [a for a in anchors if a not in state.roster]
        if missing:
            state.roster = missing + state.roster
            store.save_place(state)
        return state.roster
    if not world.places[place_id].danger:
        return state.roster
    found = world.creature_candidates(place_id, CREATURE_RULES["rarity_weight"])
    rng = random.Random(f"{store.meta.seed}:roster:{place_id}")
    roster = list(anchors)
    pool = [f for f in found if f[0].id not in roster]
    while pool and len(roster) < E["roster_size"]:
        pick = rng.choices(pool, weights=[w for _, w in pool])[0]
        roster.append(pick[0].id)
        pool.remove(pick)
    state.roster = roster
    store.save_place(state)
    return roster


def matching(world, roster: list[str], seek: str) -> list[str]:
    """Roster creatures whose name matches what the player is looking for ('wolves' finds wolf, dire wolf...)."""
    def singular(w: str) -> str:
        if w.endswith("ves"):
            return w[:-3] + "f"
        if w.endswith("ies"):
            return w[:-3] + "y"
        return w[:-1] if w.endswith("s") and not w.endswith("ss") else w
    words = [singular(w) for w in seek.lower().split() if len(w) > 2]
    return [r for r in roster if any(w in world.bestiary[r].name.lower() for w in words)]


CREATURE_RULES_COMBAT = combat.RULES["creatures"]


def roll(store, world, place_id: str, chance: float, rng: random.Random, seek: str = "", force: str = "",
         contracts: list | None = None) -> tuple[object, list[combat.Fighter]] | None:
    """Maybe produce an encounter: (creature, fighters). Fighters are all of one kind for now."""
    place = world.places[place_id]
    if not place.danger or rng.random() >= chance:
        return None
    if not force:
        spawned = events.pick_spawn(store, place_id, rng, store.meta.minutes)
        if spawned:
            return events.spawn_fighters(world, spawned, rng, 0)
    roster = ensure_roster(store, world, place_id)
    if not roster and not force:
        return None
    wanted = matching(world, roster, seek) if seek else []
    if force and force in world.bestiary:
        creature = world.bestiary[force]
    else:
        creature = world.bestiary[rng.choice(wanted) if wanted and rng.random() < 0.75 else rng.choice(roster)]
    low = max(place.danger[0], creature.levels[0])
    high = min(place.danger[1], creature.levels[1])
    posted = next((q["scale"] for q in contracts or [] if q.get("scale") and q["kind"] == "hunt" and q.get("place") == place_id
                   and q.get("creature") == creature.id and q["progress"] < q["count"]), None)
    if posted:
        low = high = posted             # a contract posted for this rank is fought at the rank's level
    cap = max(creature.group[0], 2 + place.danger[1] // 10)
    top = creature.group[1]
    falloff = CREATURE_RULES_COMBAT.get("group_size_falloff", 1.0)
    lp = CREATURE_RULES_COMBAT.get("late_pack")
    if lp and high > lp["from_level"]:       # far-land packs run bigger
        t = min(1.0, (high - lp["from_level"]) / max(1, lp["full_level"] - lp["from_level"]))
        falloff += (lp["falloff"] - falloff) * t
        extra = round(lp["extra_cap"] * t)
        cap += extra
        top += extra
    sizes = list(range(creature.group[0], min(top, cap) + 1))
    count = rng.choices(sizes, weights=[falloff ** i for i in range(len(sizes))])[0]
    late = E.get("elite_late")
    chance = E["elite_chance"] + (min(late["cap"] - E["elite_chance"], late["per_level"] * max(0, high - late["start_level"])) if late else 0)
    rank = "elite" if rng.random() < chance else "normal"
    start = "engaged" if creature.temperament == "aggressive" and rng.random() < 0.3 else "near"
    fighters = []
    for i in range(count):
        level = rng.randint(min(low, high), max(low, high))
        name = creature.name.lower() + (f" {i + 1}" if count > 1 else "")
        if rank == "elite" and i == 0:
            name = f"{creature.name.lower()} (elite)"
        fighters.append(combat.fighter_from_creature(creature, level, rank if i == 0 else "normal", f"e{i + 1}", name, start))
    return creature, fighters


def add_member(world, place_id: str, creature_id: str, rng: random.Random, rank: str, fid: str, name: str, start: str = "near"):
    """One more fighter of a given kind, at a level that suits the place (a camp's captain)."""
    c = world.bestiary[creature_id]
    p = world.places[place_id]
    lo, hi = max(p.danger[0], c.levels[0]), min(p.danger[1], c.levels[1])
    level = rng.randint(min(lo, hi), max(lo, hi))
    return combat.fighter_from_creature(c, level, rank, fid, name, start)
