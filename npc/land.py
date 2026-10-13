"""What the people of a place truly know about the land around them: where herbs grow and where game lives, from the world's own data.
Without it the model invents where things are found."""
from engine import clock, inventory as inv, mapview

REACH_MINUTES = 600        # places within about ten hours' walk count as the neighbourhood


def _places_near(world, place_id: str) -> dict[str, int]:
    """{place id (top-level or inside one): minutes from here} for the neighbourhood."""
    g = mapview.graph(world)
    top = mapview.top_of(world, place_id)
    times = mapview.travel_times(g, top)
    out = {}
    for p in world.places.values():
        t = times.get(mapview.top_of(world, p.id))
        if t is not None and t <= REACH_MINUTES:
            out[p.id] = t
    return out


def _where(world, ids: list[str], near: dict[str, int], here_top: str) -> str:
    names = []
    for i in sorted(ids, key=lambda i: near[i])[:3]:
        t = near[i]
        names.append(f"{world.places[i].name} ({'right here' if mapview.top_of(world, i) == here_top else clock.describe_duration(t) + ' away'})")
    return ", ".join(names)


def land_lines(world, place_id: str) -> list[str]:
    near = _places_near(world, place_id)
    here_top = mapview.top_of(world, place_id)
    lines = []
    for g in inv.GOODS.values():
        if g.kind == "herb" and g.grows_in:
            strong = sorted(g.grows_in.items(), key=lambda kv: -kv[1])
            parts = []
            for biome, chance in strong:
                ids = [i for i in near if world.places[i].biome == biome and world.places[i].type != "dungeon"]
                if ids:
                    parts.append(f"{'often' if chance >= 0.4 else 'now and then' if chance >= 0.25 else 'rarely'} in the {biome}: {_where(world, ids, near, here_top)}")
            lines.append(f"{g.name} - " + ("; ".join(parts) if parts else "none that you know of within a day's walk"))
    for g in inv.GOODS.values():
        if g.kind == "food" and g.drops_from:
            biomes = set()
            for cid in g.drops_from:
                c = world.bestiary.get(cid)
                if c:
                    biomes |= set(c.biomes)
            ids = [i for i in near if world.places[i].biome in biomes and world.places[i].danger]
            if ids:
                lines.append(f"{g.name} (the animals {', '.join(g.drops_from)}) - hunted around: {_where(world, ids, near, here_top)}")
    return lines
