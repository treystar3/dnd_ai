"""Balance simulator: runs thousands of fights and reports how they go.

    python tools/balance.py

Edit the SCENARIOS list to test what you care about. Tune numbers in data/rules/combat.yaml
until the results match how you want fights to feel.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import Ability, Archetype, Attributes, Character  # noqa: E402
from engine import combat, items  # noqa: E402
from world.loader import load_world  # noqa: E402

RUNS = 400


def test_player(level: int, gear: str = "starter") -> Character:
    """A Dragoon-like fighter: 'strong and nimble' build, points spread like a typical player."""
    extra = 5 * (level - 1)
    a = Attributes(strength=26 + extra * 35 // 100, dexterity=22 + extra * 30 // 100, constitution=18 + extra * 25 // 100,
                   intelligence=14 + extra * 4 // 100, wisdom=10 + extra * 4 // 100, charisma=10 + extra * 2 // 100)
    c = Character(name="you", archetype=Archetype.WARRIOR, custom_class="Dragoon", level=level, attributes=a)
    c.actives = [
        Ability(id="plunge", name="Plunging Strike", description="", effect="damage", tier="moderate", reach="melee",
                resource="stamina", context="combat", cost=10, cooldown=1),
        Ability(id="thrust", name="Lunging Thrust", description="", effect="damage", tier="light", reach="extended",
                resource="stamina", context="combat", cost=5, cooldown=0),
    ]
    if gear == "starter":
        c.equipment = {"main_hand": items.make("spear", "crude")}
    else:
        rarity = "common"
        c.equipment = {"main_hand": items.make("spear", rarity, level), "body": items.make("leather", rarity, level),
                       "off_hand": items.make("wooden_shield", rarity, level), "head": items.make("leather_cap", rarity, level)}
    return c


def run(world, level: int, gear: str, creature_id: str, enemy_level: int, count: int, rank: str = "normal"):
    creature = world.bestiary[creature_id]
    rng = random.Random(1)
    results = []
    for _ in range(RUNS):
        player = combat.fighter_from_character(test_player(level, gear))
        enemies = [combat.fighter_from_creature(creature, enemy_level, rank, f"e{i}", band="near") for i in range(count)]
        out = combat.simulate(combat.Combat(fighters=[player] + enemies), rng)
        results.append((out.over, out.round - 1, out.player.hp / out.player.max_hp))
    wins = [r for r in results if r[0] == "victory"]
    win_rate = len(wins) / RUNS
    rounds = sum(r[1] for r in results) / RUNS
    hp_left = sum(r[2] for r in wins) / len(wins) if wins else 0
    return win_rate, rounds, hp_left


SCENARIOS = [
    # (label, player level, gear, creature, enemy level, how many, rank)
    ("lv1 starter vs 1 wolf lv1", 1, "starter", "wolf", 1, 1, "normal"),
    ("lv1 starter vs 2 wolves lv1", 1, "starter", "wolf", 1, 2, "normal"),
    ("lv1 starter vs 4 wolves lv1", 1, "starter", "wolf", 1, 4, "normal"),
    ("lv1 starter vs bandit lv1", 1, "starter", "bandit", 1, 1, "normal"),
    ("lv1 starter vs black bear lv2", 1, "starter", "black_bear", 2, 1, "normal"),
    ("lv5 geared vs brown bear lv5", 5, "geared", "brown_bear", 5, 1, "normal"),
    ("lv5 geared vs 3 wolves lv5", 5, "geared", "wolf", 5, 3, "normal"),
    ("lv20 geared vs owlbear lv20", 20, "geared", "owlbear", 20, 1, "normal"),
    ("lv50 geared vs troll lv50", 50, "geared", "troll", 50, 1, "normal"),
    ("lv50 geared vs troll lv50 elite", 50, "geared", "troll", 50, 1, "elite"),
    ("lv100 geared vs troll lv100", 100, "geared", "troll", 100, 1, "normal"),
    ("lv300 geared vs wyvern lv300", 300, "geared", "wyvern", 300, 1, "normal"),
    ("lv300 geared vs 6 wolves lv2", 300, "geared", "wolf", 2, 6, "normal"),
    ("lv50 geared vs 2 wolves lv80", 50, "geared", "wolf", 80, 2, "normal"),
]


def main():
    world = load_world()
    print(f"{'scenario':<38} {'win':>6} {'rounds':>7} {'hp left':>8}")
    for label, lv, gear, cid, elv, n, rank in SCENARIOS:
        w, r, hp = run(world, lv, gear, cid, elv, n, rank)
        print(f"{label:<38} {w:>5.0%} {r:>7.1f} {hp:>7.0%}")


if __name__ == "__main__":
    main()
