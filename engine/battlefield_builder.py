"""Builds the ground a fight is fought on (data/rules/battlefields.yaml): one main zone and 0-2 side zones from the place's biome
family, joined into a small connected graph and frozen onto the fight. Seeded by the campaign, the place and the day's minute, so the
same ambush in the same place at the same time stands on the same ground, in play and in every simulation of it."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine.battlefield import BattleEdge, Battlefield, BattleZone

ROOT = Path(__file__).resolve().parent.parent
B = yaml.safe_load((ROOT / "data" / "rules" / "battlefields.yaml").read_text(encoding="utf-8"))

# place types that imply a family when the place names no biome
TYPE_FAMILY = {"forest": "forest", "hills": "hills", "mountains": "mountains", "desert": "desert", "jungle": "jungle",
               "coast": "coast", "river": "freshwater", "wetland": "swamp", "tundra": "tundra", "badlands": "wasteland",
               "wasteland": "wasteland", "ruins": "ruins", "underground": "underground", "fields": "farmland",
               "town": "urban", "city": "urban", "village": "urban", "square": "urban", "inn": "urban", "shop": "urban",
               "guild": "urban", "temple": "urban", "smithy": "urban", "workshop": "urban", "yard": "urban", "guardpost": "urban"}

FAMILIES = tuple(k for k in B if k not in ("sides", "side_link", "big"))


def family_of(place, world=None) -> str:
    """The battlefield family for a place: its biome, its parent's, or what its type implies; 'default' when nothing says."""
    biome = getattr(place, "biome", None)
    if not biome and world is not None and getattr(place, "parent", None):
        parent = world.places.get(place.parent)
        biome = getattr(parent, "biome", None) if parent else None
    for key in (biome, TYPE_FAMILY.get(getattr(place, "type", "") or "")):
        if key and key in B:
            return key
    return "default"


def build(family: str, rng: random.Random) -> Battlefield:
    """One main zone and 0-2 sides from this family, drawn and joined by the given rng."""
    fam = B.get(family) or B["default"]
    main = rng.choice(fam["main"])
    zones = {"z1": BattleZone(id="z1", name=main["name"], tags=list(main.get("tags", [])))}
    edges: list[BattleEdge] = []
    roll, S = rng.random(), B["sides"]
    count = 0 if roll < S["none"] else (1 if roll < S["none"] + S["one"] else 2)
    sides = rng.sample(fam["side"], min(count, len(fam["side"]))) if count else []
    for i, s in enumerate(sides, start=2):
        zid = f"z{i}"
        zones[zid] = BattleZone(id=zid, name=s["name"], tags=list(s.get("tags", [])))
        edges.append(BattleEdge(a="z1", b=zid, tags=[s.get("way", "open")]))
    if len(sides) == 2 and rng.random() < B["side_link"]:
        edges.append(BattleEdge(a="z2", b="z3", tags=["difficult"]))
    return Battlefield(zones=zones, edges=edges, start="z1")


def build_big(family: str, kind: str, rng: random.Random) -> Battlefield:
    """A big fight's field (data/rules/battlefields.yaml big): a camp or a lair from its fixed layout, or this biome's ground made larger
    and chained - a main zone, 2-3 sides, and 1-2 zones beyond a side."""
    G = B["big"]
    if kind in ("camp", "lair"):
        L = G[kind]
        zones = {zid: BattleZone(id=zid, name=z["name"], tags=list(z.get("tags", []))) for zid, z in L["zones"].items()}
        edges = [BattleEdge(a=a, b=b, tags=[way]) for a, b, way in L["edges"]]
        return Battlefield(zones=zones, edges=edges, start=L["enemy"], player_start=L["player"], enemy_start=L["enemy"],
                           back=L["back"], arrivals=L["arrivals"], kind=kind)
    fam = B.get(family) or B["default"]
    main = rng.choice(fam["main"])
    zones = {"z1": BattleZone(id="z1", name=main["name"], tags=list(main.get("tags", [])))}
    edges: list[BattleEdge] = []
    n_sides = 2 if rng.random() < G["sides"]["two"] else 3
    pool = list(fam["side"])
    rng.shuffle(pool)
    sides = pool[:n_sides]
    for i, s in enumerate(sides, start=2):
        zones[f"z{i}"] = BattleZone(id=f"z{i}", name=s["name"], tags=list(s.get("tags", [])))
        edges.append(BattleEdge(a="z1", b=f"z{i}", tags=[s.get("way", "open")]))
    beyond_pool = list(fam.get("beyond") or pool[n_sides:] or fam["side"])
    rng.shuffle(beyond_pool)
    n_beyond = 1 if rng.random() < G["beyond"]["one"] else 2
    side_ids = [f"z{i}" for i in range(2, 2 + len(sides))]
    nxt = 2 + len(sides)
    for b in beyond_pool[:n_beyond]:
        zid = f"z{nxt}"
        nxt += 1
        name = b["name"] if b["name"] not in {z.name for z in zones.values()} else f"{b['name']} further on"
        zones[zid] = BattleZone(id=zid, name=name, tags=list(b.get("tags", [])))
        edges.append(BattleEdge(a=rng.choice(side_ids), b=zid, tags=[b.get("way", "open")]))
    field = Battlefield(zones=zones, edges=edges, start="z1", kind="wild")
    parents = {e.a for e in edges if e.b not in side_ids and e.a in side_ids}
    edge_side = next((z for z in side_ids if z not in parents), side_ids[0])
    field.player_start, field.enemy_start = edge_side, "z1"     # you come in from one side; they hold the middle
    far = max(zones, key=lambda z: (field.steps(edge_side, z), z))
    field.back = field.arrivals = far
    return field


def duel_ground(place_name: str = "") -> Battlefield:
    """A trial of rank is fought on bare, even ground: one zone, no terrain to lean on."""
    z = BattleZone(id="z1", name="the dueling ground", tags=["open"])
    return Battlefield(zones={"z1": z}, start="z1")


def for_scene(ws, duel: bool = False, big: str = "") -> Battlefield:
    """The battlefield for a fight starting now, where the player stands. A big fight (camp, lair, or wild) gets a larger field."""
    if duel:
        return duel_ground(ws.place.name)
    rng = random.Random(f"{ws.store.meta.seed}:{ws.minutes}:{ws.place.id}:field")
    if big:
        return build_big(family_of(ws.place, ws.world), big, rng)
    return build(family_of(ws.place, ws.world), rng)


def big_kind(enemies: list, reserves: list, asked: str = "") -> str:
    """What size of field a fight gets: what the caller asked for (a camp, a lair), else 'wild' for a boss or 6 or more enemies
    (reserves counted), else '' (an ordinary field)."""
    if asked:
        return asked
    if any(getattr(e, "boss", None) or getattr(e, "rank", "") == "boss" for e in enemies) or len(enemies) + len(reserves or []) >= 6:
        return "wild"
    return ""
