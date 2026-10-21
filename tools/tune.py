"""Gear-aware difficulty survey: a typically geared character at each level against level-appropriate creatures.

    python tools/tune.py [rank] [count]       rank: normal | elite | boss   count: enemies per fight (default 1)

"Typically geared" = a mix of rarities weighted the way a player really ends up (a little better than raw drops, because
players pick the best and buy and craft), with an item level a little behind the character's level.
"""
import random, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import combat, items, loot, equipment
from world.loader import load_world
from tools.balance import test_player

LEVELS = [1, 3, 8, 15, 25, 40, 60, 90, 130, 180, 250, 350]
RARITY_MIX = {"common": 25, "uncommon": 40, "rare": 28, "epic": 6, "legendary": 1}
SLOTS = [("main_hand", ["longsword", "spear", "mace", "greatsword", "battleaxe"]), ("body", ["chainmail", "scale", "leather", "plate"]),
         ("head", ["iron_helm", "leather_cap"]), ("hands", ["gauntlets", "leather_gloves"]), ("feet", ["iron_boots", "boots"]),
         ("off_hand", ["wooden_shield", "tower_shield", "buckler"]), ("neck", ["amulet"]), ("ring_1", ["ring"]), ("ring_2", ["ring"])]


EARLY_MIX = {"crude": 40, "common": 45, "uncommon": 15}


def mix_for(level: int, mix=RARITY_MIX) -> dict:
    """Early characters wear what they started with and a few finds; by level 40 they wear the full typical mix."""
    t = min(1.0, max(0.0, (level - 1) / 39))
    keys = set(mix) | set(EARLY_MIX)
    return {k: EARLY_MIX.get(k, 0) * (1 - t) + mix.get(k, 0) * t for k in keys}


def geared(level: int, rng: random.Random, mix=RARITY_MIX, lag: float = 0.9):
    c = test_player(level, "starter")
    c.equipment = {}
    weights = mix_for(level, mix)
    fill = min(1.0, 0.35 + level / 30)                  # not every slot is filled early on
    for slot, bases in SLOTS:
        if slot != "main_hand" and rng.random() > fill:
            continue
        rarity = rng.choices(list(weights), weights=list(weights.values()))[0]
        ilvl = max(1, round(level * lag) - rng.randint(0, max(1, level // 10)))
        pool = [b for b in bases if items.CATALOG[b].min_level <= ilvl] or bases[:1]
        it = items.make(rng.choice(pool), rarity, ilvl, rng=rng)
        loot.roll_gear(it, rng)
        c.equipment[slot] = it
    if "off_hand" in c.equipment and items.base_of(c.equipment["main_hand"]).hands == 2:
        c.equipment.pop("off_hand", None)
    return c


def pack_size(cr, level, rng):
    """How many of a pack creature an encounter sends (engine/encounters.py): mostly the smallest group, capped by how dangerous the place is."""
    cap = max(cr.group[0], 2 + level // 10)
    sizes = list(range(cr.group[0], min(cr.group[1], cap) + 1))
    return rng.choices(sizes, weights=[combat.RULES["creatures"].get("group_size_falloff", 1.0) ** i for i in range(len(sizes))])[0]


def survey(world, rank="normal", count=1, runs=12, per_level=18, mix=RARITY_MIX, seed=5, levels=None, pack=False):
    rows = []
    for lv in levels or LEVELS:
        rng = random.Random(seed * 1000 + lv)
        cands = [c for c in world.bestiary.values() if c.levels[0] <= lv <= c.levels[1] and not c.unique and (c.group[0] >= 2) == pack]
        if not cands:
            cands = [c for c in world.bestiary.values() if not c.unique and c.levels[0] <= lv * 1.5 and (c.group[0] >= 2) == pack][-40:]
        picks = rng.sample(cands, min(per_level, len(cands)))
        wins = rounds = lost = n = 0
        for cr in picks:
            for _ in range(runs):
                p = combat.fighter_from_character(geared(lv, rng, mix))
                foes = [combat.fighter_from_creature(cr, lv, rank, f"e{i}", start="near") for i in range(count if not pack else pack_size(cr, lv, rng))]
                out = combat.simulate(combat.Combat(fighters=[p] + foes), rng)
                n += 1; rounds += out.round - 1
                lost += 1 - (out.player.hp / out.player.max_hp if out.over == "victory" else 0)
                wins += out.over == "victory"
        rows.append((lv, wins / n, rounds / n, lost / n))
    return rows


def main():
    rank = sys.argv[1] if len(sys.argv) > 1 else "normal"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    world = load_world()
    print(f"{rank} x{count}: level  win  rounds  hp lost")
    for lv, w, r, h in survey(world, rank, count):
        print(f"  {lv:>4}  {w:>5.0%}  {r:>5.1f}  {h:>5.0%}")


if __name__ == "__main__":
    main()
