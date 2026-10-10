"""Property and relics: the places the player's gold can go. A home is a Place of its own, registered in the world when
owned; relics are fixed, named legendary items sold by a relic dealer, one of each."""

import random

import yaml

from core.models import Item
from engine import items
from core.models import ItemProperty
from world.loader import Place

P = yaml.safe_load(open(__import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "rules" / "property.yaml", encoding="utf-8"))
RELICS = {r["id"]: r for r in yaml.safe_load(open(__import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "world" / "relics.yaml", encoding="utf-8"))}


def home_id(town: str) -> str:
    return f"home_{town}"


def town_of(world, place_id: str) -> str:
    p = world.places.get(place_id)
    while p and p.parent and p.parent in world.places:
        p = world.places[p.parent]
    return p.id if p else place_id


def register(world, player) -> None:
    """Put every owned home on the map."""
    for town, h in player.homes.items():
        if town not in world.places or town not in P["homes"]:
            continue
        pid = home_id(town)
        t = world.places[town]
        ruined = h.get("ruined")
        stations = P["workshop_stations"] if "workshop" in h["upgrades"] and not ruined else {}
        visible = ([f"What is left of {P['homes'][town]['name']}: blackened beams, a fallen roof, a door that no longer shuts. "
                    "The item box in the cellar is untouched. Say 'rebuild the house' to restore it."] if ruined else
                   [f"{P['homes'][town]['name'].capitalize()}, bought and paid for - yours.",
                    "A bed, a table, a hearth that is yours to light, and a door that locks from the inside."]
                   + [f"A {P['upgrades'][u]['name']}, built to your orders." for u in h["upgrades"]])
        world.places[pid] = Place(
            id=pid, name=f"your {'ruined ' if ruined else ''}house in {t.name}", type="home", region=t.region, parent=town,
            visible=visible,
            storage=True, biome=t.biome, trade_level=t.trade_level, stations=stations, locals_group=t.locals_group)


def stash_bonus(player) -> int:
    ups = {u for h in player.homes.values() for u in h["upgrades"]}
    return sum(P["upgrades"][u].get("stash_bonus", 0) for u in ups)


def find_upgrade(words: str) -> str | None:
    w = words.lower()
    for uid, u in P["upgrades"].items():
        if any(k in w for k in u["words"]):
            return uid
    return None


def relic_item(rid: str) -> Item:
    r = RELICS[rid]
    it = items.make(r["base"], "legendary", r["level"], name=r["name"], description=r["description"], material=r["material"])
    it.uid = f"relic_{rid}"
    it.title = r.get("title", "")
    it.legendary_effect = r["effect"]
    it.properties = [ItemProperty(modifies=p["modifies"], trigger=p.get("trigger", "always"), magnitude=p["magnitude"])
                     for p in r["properties"]]
    return it


def dealer_towns(world) -> list[str]:
    return sorted(p.id for p in world.places.values() if "relic_dealer" in (p.residents or {}))


def stock(world, seed) -> dict[str, str]:
    """Which relic is on which dealer's shelf in this campaign. Fixed for the campaign (same seed, same shelves) but different
    in every new one. A relic with a home (far-lands relics) is only ever sold in its home town and is left out of a run whose
    shelves there are already full; the rest are drawn from the whole pool. Far-lands dealers keep more shelves (property.yaml)."""
    rng = random.Random(f"{seed}:relics")
    towns = dealer_towns(world)
    pool = sorted(RELICS)
    rng.shuffle(pool)
    room = {t: P.get("relic_shelves", {}).get(t, 1) for t in towns}
    placed: dict[str, str] = {}
    for rid in pool:
        homes = [h for h in RELICS[rid].get("home", []) if room.get(h, 0) > 0]
        if homes:
            town = rng.choice(homes)
            placed[rid] = town
            room[town] -= 1
    for rid in pool:
        if rid in placed or RELICS[rid].get("home"):
            continue
        open_towns = [t for t in towns if room[t] > 0]
        if not open_towns:
            break
        town = rng.choice(open_towns)
        placed[rid] = town
        room[town] -= 1
    return placed


def relics_in(world, seed, town: str, bought: list[str]) -> list[tuple[Item, int]]:
    return [(relic_item(rid), RELICS[rid]["price"]) for rid, t in stock(world, seed).items() if t == town and rid not in bought]
