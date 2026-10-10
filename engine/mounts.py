"""Mounts: what a city stable sells and which mount is ridden. The mounts themselves live in events.yaml (grand.mounts)."""

import random
import re
from pathlib import Path

import yaml

from engine import events, property as prop

M = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "mounts.yaml").read_text(encoding="utf-8"))
CATALOG = {k: dict(v, id=k) for k, v in events.E["grand"]["mounts"].items()}
WORDS = re.compile(r"\b(mount|mounts|horse|horses|steed|steeds|stable|stables|pony|ponies|palfrey|courser|destrier|strider|charger|ride|riding)\b", re.I)


def stable_town(world, place_id: str) -> str:
    """The city whose stable serves this place, or '' when it is not in one."""
    town = prop.town_of(world, place_id)
    p = world.places.get(town)
    return town if p and p.type in M["stable_place_types"] else ""


def stock(world, seed: int, town: str) -> list[dict]:
    """The mounts this city's stable has for sale: a fixed few, always including a cheap one."""
    if not town:
        return []
    for_sale = sorted((m for m in CATALOG.values() if m.get("price")), key=lambda m: m["price"])
    rng = random.Random(f"{seed}:stable:{town}")
    cheap = [m for m in for_sale if m["price"] <= M["always_stock_up_to"]]
    picks = [rng.choice(cheap)] if cheap else []
    rest = [m for m in for_sale if m not in picks]
    rng.shuffle(rest)
    picks += rest[:max(0, M["stock_size"] - len(picks))]
    return sorted(picks, key=lambda m: m["price"])


def find(candidates: list[dict], words: str) -> dict | None:
    """The mount a phrase names ('the courser', 'a pony', 'swift')."""
    w = words.lower()
    best = None
    for m in candidates:
        name = m["name"].lower()
        keys = [m["id"].replace("_", " "), *[t for t in re.findall(r"[a-z]+", name) if t not in ("a", "an", "the", "war", "tamed", "to", "grown", "long", "legged", "sure", "footed", "swift", "gentle", "trained", "hatchling")]]
        if any(re.search(rf"\b{re.escape(k)}s?\b", w) for k in keys):
            best = best or m
    return best


def owned(player) -> list[dict]:
    return list(player.mounts)


def ride(player, mount_id: str) -> dict | None:
    """Pick the mount to ride ('' to go on foot). Returns the mount, or None."""
    if not mount_id:
        player.mount = ""
        return None
    m = next((x for x in player.mounts if x["id"] == mount_id), None)
    if m:
        player.mount = mount_id
    return m


def buy(player, character, mount: dict, price: int) -> str:
    """Why the purchase can't happen, or '' after it is made."""
    if any(m["id"] == mount["id"] for m in player.mounts):
        return "You already own one."
    if character.level < mount["min_level"]:
        return f"It needs a rider of level {mount['min_level']}; you are level {character.level}."
    if character.coins < price:
        return "short"
    character.coins -= price
    entry = {k: mount[k] for k in ("id", "name", "speed", "stamina")}
    player.mounts.append(entry)
    if not player.mount:
        player.mount = mount["id"]
    return ""
