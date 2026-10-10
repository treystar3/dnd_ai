"""Procedurally generated dungeons beneath wild places. A dungeon is a plain dict, saved per campaign:

  id, name, theme, place (the wild place above), entrance (its place id), seed, made (minute generated),
  floors: [{level, letter, chambers: [{kind, creature, count, level, boss}]}],
  cleared: [floor, chamber] of the deepest cleared chamber, or [-1, -1]
"""

import random
from pathlib import Path

import yaml

from engine import quests

ROOT = Path(__file__).resolve().parent.parent
D = yaml.safe_load((ROOT / "data" / "rules" / "dungeons.yaml").read_text(encoding="utf-8"))


def theme_for(place, world, rng: random.Random) -> str | None:
    fits = [t for t, spec in D["themes"].items() if place.biome in spec["biomes"]
            and any(b.category in spec["categories"] for b in world.bestiary.values())]
    return rng.choice(fits) if fits else None


def creatures_for(world, theme: str, level: int, biome: str | None = None) -> list:
    cats = D["themes"][theme]["categories"]
    pool = [b for b in world.bestiary.values() if b.category in cats and not getattr(b, "unique", False)
            and b.temperament != "passive"]
    local = [b for b in pool if biome in b.biomes]
    pool = local or pool
    near = [b for b in pool if b.levels[0] <= level <= b.levels[1]]
    if near:
        return near
    return sorted(pool, key=lambda b: min(abs(b.levels[0] - level), abs(b.levels[1] - level)))[:3]


def generate(place, world, seed: str, now: int) -> dict | None:
    rng = random.Random(seed)
    theme = theme_for(place, world, rng)
    if not theme:
        return None
    spec = D["themes"][theme]
    lo, hi = place.danger
    base = rng.randint(lo, lo + max(2, (hi - lo) // 8))
    top = base + max(D["depth"]["extra_levels"], round(base * D["depth"]["growth"]))
    n_floors = rng.randint(*D["floors"])
    floors = []
    for f in range(n_floors):
        level = round(base + (top - base) * f / max(1, n_floors - 1))
        chambers = []
        for c in range(rng.randint(*D["chambers_per_floor"])):
            kinds = {k: w for k, w in D["chambers"].items() if not (k == "rest" and any(x["kind"] == "rest" for x in chambers))}
            chambers.append({"kind": rng.choices(list(kinds), weights=list(kinds.values()))[0]})
        chambers[-1] = {"kind": "fight"}
        for ch in chambers:
            if ch["kind"] == "fight":
                choice = rng.choice(creatures_for(world, theme, level, place.biome))
                sizes = list(range(choice.group[0], min(choice.group[1], 3) + 1)) or [1]
                ch.update(creature=choice.id, level=level,
                          count=rng.choices(sizes, weights=[0.4 ** i for i in range(len(sizes))])[0], boss=False)
        floors.append({"level": level, "letter": quests.letter_for_level(level), "chambers": chambers})
    boss_level = top + 2
    sizes = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
    strongest = sorted(creatures_for(world, theme, boss_level, place.biome),
                       key=lambda b: (sizes.index(b.size) if b.size in sizes else 2, b.levels[0]), reverse=True)[:3]
    boss = rng.choice(strongest)
    floors[-1]["chambers"].append({"kind": "fight", "creature": boss.id, "level": boss_level, "count": 1, "boss": True})
    name = f"the {rng.choice(spec['adjectives'])} {rng.choice(spec['nouns'])}"
    return {"id": f"dungeon_{place.id}", "name": name, "theme": theme, "place": place.id,
            "entrance": f"dungeon_{place.id}", "seed": seed, "made": now, "floors": floors, "cleared": [-1, -1],
            "boss_letter": quests.letter_for_level(boss_level), "boss_name": f"the master of {name}"}


def due_for_respawn(d: dict, now: int) -> bool:
    return now >= d["made"] + D["respawn_days"] * 1440


def next_chamber(d: dict) -> tuple[int, int] | None:
    """The chamber after the deepest one cleared, or None if the dungeon is finished."""
    f, c = d["cleared"]
    if f < 0:
        return 0, 0
    if f >= len(d["floors"]) or c >= len(d["floors"][f]["chambers"]):
        d["cleared"] = [-1, -1]
        return 0, 0
    if c + 1 < len(d["floors"][f]["chambers"]):
        return f, c + 1
    if f + 1 < len(d["floors"]):
        return f + 1, 0
    return None


def letters(d: dict) -> str:
    seen = []
    for fl in d["floors"]:
        if fl["letter"] not in seen:
            seen.append(fl["letter"])
    return "-".join(seen) + (f", boss {d['boss_letter']}" if d["boss_letter"] not in seen else "")


def entrance_place(d: dict, world):
    from world.loader import Place
    above = world.places[d["place"]]
    return Place(id=d["entrance"], name=f"{d['name']} (beneath {above.name})", type="dungeon", region=above.region,
                 connects={above.id: 10}, biome=above.biome,
                 visible=[f"The entrance to {d['name']}, a {d['theme']} beneath {above.name}.",
                          "Steps lead down into the dark."])
