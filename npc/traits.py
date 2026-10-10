"""Personality traits.

An NPC rolls TRAIT_COUNT traits the first time the player meets them. After that the
traits are permanent: assign_traits never rerolls, and the only way to change one is
change_trait, which requires a cause and records it in the NPC's trait history.
"""

import random
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from npc.models import NPC, TraitChange

from core.paths import BUNDLE
TRAITS_PATH = BUNDLE / "data" / "traits.yaml"
TRAIT_COUNT = 3
RARITY_WEIGHT = {"common": 6, "uncommon": 3, "rare": 1}


class Trait(BaseModel):
    id: str
    description: str
    rarity: Literal["common", "uncommon", "rare"] = "common"
    conflicts: list[str] = []


class TraitCatalog:
    def __init__(self, traits: dict[str, Trait]):
        self.traits = traits
        self._conflicts = {t: set() for t in traits}
        for t in traits.values():
            for other in t.conflicts:
                self._conflicts[t.id].add(other)
                self._conflicts[other].add(t.id)

    def conflicts(self, a: str, b: str) -> bool:
        return b in self._conflicts.get(a, set())

    def fits(self, candidate: str, existing: list[str]) -> bool:
        return candidate not in existing and not any(self.conflicts(candidate, e) for e in existing)

    def describe(self, trait_ids: list[str]) -> list[str]:
        return [f"{t}: {self.traits[t].description}" for t in trait_ids]


def load_traits(path: Path = TRAITS_PATH) -> TraitCatalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    traits, problems = {}, []
    for entry in raw:
        t = Trait(**entry)
        if t.id in traits:
            problems.append(f"duplicate trait '{t.id}'")
        traits[t.id] = t
    for t in traits.values():
        for other in t.conflicts:
            if other not in traits:
                problems.append(f"trait '{t.id}' conflicts with unknown trait '{other}'")
    if problems:
        raise ValueError("traits.yaml has problems:\n" + "\n".join(f"  - {p}" for p in problems))
    return TraitCatalog(traits)


def npc_rng(campaign_seed: int, npc_id: str) -> random.Random:
    return random.Random(f"{campaign_seed}:{npc_id}")


def roll_traits(catalog: TraitCatalog, rng: random.Random, count: int = TRAIT_COUNT) -> list[str]:
    chosen: list[str] = []
    while len(chosen) < count:
        candidates = [t for t in catalog.traits.values() if catalog.fits(t.id, chosen)]
        weights = [RARITY_WEIGHT[t.rarity] for t in candidates]
        chosen.append(rng.choices(candidates, weights=weights)[0].id)
    return chosen


def assign_traits(npc: NPC, catalog: TraitCatalog, rng: random.Random) -> bool:
    """Roll traits for an NPC meeting the player for the first time. Never rerolls."""
    if npc.traits:
        return False
    npc.traits = roll_traits(catalog, rng)
    return True


def change_trait(npc: NPC, catalog: TraitCatalog, remove: str, add: str, cause: str, day: int) -> None:
    """Replace one trait because something in the world changed this person."""
    if not cause.strip():
        raise ValueError("a trait change needs a cause")
    if remove not in npc.traits:
        raise ValueError(f"{npc.name} does not have the trait '{remove}'")
    if add not in catalog.traits:
        raise ValueError(f"'{add}' is not a known trait")
    remaining = [t for t in npc.traits if t != remove]
    if not catalog.fits(add, remaining):
        raise ValueError(f"'{add}' conflicts with {npc.name}'s other traits")
    npc.traits = remaining + [add]
    npc.trait_history.append(TraitChange(day=day, removed=remove, added=add, cause=cause.strip()))
