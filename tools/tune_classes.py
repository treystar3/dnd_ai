"""How each class feels at each level with typical gear, against level-appropriate creatures.

    python tools/tune_classes.py [rank] [pack]       rank: normal | elite | boss; add "pack" to fight pack creatures

Uses the simulator's ten classes (simlib.CLASSES), their starting kits, attributes grown the way the bots spend points, a typical gear mix
for the level (tools/tune.py) and the class's companions. No potions, party, or extra abilities - a conservative floor.
"""
import random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import combat, items, loot, taming
from world.loader import load_world
from tools.tune import mix_for, pack_size, RARITY_MIX

CLASSES = "warrior paladin monk ranger smith mage warlock priest bard summoner".split()
LEVELS = [3, 10, 25, 50, 90, 150, 250, 400]
SHIELDS = {"warrior", "paladin", "priest", "smith"}
BODY_WEIGHT = {"clothes": "light", "robe": "light", "leather": "light", "padded": "light", "chain_shirt": "medium", "scale": "medium", "chainmail": "heavy", "plate": "heavy"}
ARMOR_BASES = {"light": dict(head=["leather_cap"], hands=["leather_gloves"], feet=["boots"]),
               "medium": dict(head=["iron_helm"], hands=["gauntlets"], feet=["iron_boots"]),
               "heavy": dict(head=["iron_helm"], hands=["gauntlets"], feet=["iron_boots"])}
CASTER_HEAD = {"mage", "warlock", "priest", "bard", "summoner"}


_BASE = {}


def base_character(cls: str):
    if cls not in _BASE:
        simlib.install(simlib.Stub(cls, 1))              # the stand-in for the language model answers for one class at a time
        _BASE[cls] = simlib.make_character(cls, random.Random(1, perks=True))
    c, spec = _BASE[cls]
    return c.model_copy(deep=True), spec


def build(cls: str, level: int, rng: random.Random):
    c, spec = base_character(cls)
    c.level = level
    extra = 5 * (level - 1)
    total = sum(spec["per_level"].values())
    for a, w in spec["per_level"].items():
        setattr(c.attributes, a, getattr(c.attributes, a) + round(extra * w / total))
    weights = mix_for(level)
    fill = min(1.0, 0.35 + level / 30)
    ilvl_of = lambda: max(1, round(level * 0.9) - rng.randint(0, max(1, level // 10)))

    def piece(base):
        rarity = rng.choices(list(weights), weights=list(weights.values()))[0]
        ilvl = ilvl_of()
        pool = base if isinstance(base, list) else [base]
        pool = [b for b in pool if items.CATALOG[b].min_level <= ilvl] or pool[:1]
        it = items.make(rng.choice(pool), rarity, ilvl, rng=rng)
        loot.roll_gear(it, rng)
        return it

    eq = {"main_hand": piece(spec["weapon"]), "body": piece(spec["armor"][0])}
    weight = BODY_WEIGHT.get(spec["armor"][0], "light")
    for slot in ("head", "hands", "feet"):
        if rng.random() <= fill:
            eq[slot] = piece(ARMOR_BASES[weight][slot])
    if cls in SHIELDS and items.base_of(eq["main_hand"]).hands < 2 and rng.random() <= fill:
        eq["off_hand"] = piece("wooden_shield" if weight != "heavy" else "tower_shield")
    for slot, base in (("neck", "amulet"), ("ring_1", "ring"), ("ring_2", "ring")):
        if rng.random() <= fill and level >= 5:
            eq[slot] = piece(base)
    c.equipment = eq
    for comp in c.companions:
        comp.level = level
    return c


def fight(world, cls, level, rank, pack, per_level=14, runs=4, seed=3):
    rng = random.Random(seed * 1000 + level)
    cands = [c for c in world.bestiary.values() if c.levels[0] <= level <= c.levels[1] and not c.unique and (c.group[0] >= 2) == pack]
    if not cands:
        cands = [c for c in world.bestiary.values() if not c.unique and c.levels[0] <= level * 1.5 and (c.group[0] >= 2) == pack][-40:]
    picks = rng.sample(cands, min(per_level, len(cands)))
    wins = rounds = lost = n = 0
    for cr in picks:
        for _ in range(runs):
            ch = build(cls, level, rng)
            p = combat.fighter_from_character(ch)
            allies = []
            for comp in ch.companions:
                shape = world.bestiary.get(comp.creature)
                if shape:
                    allies.append(combat.companion_fighter(shape, level, f"ally_{comp.id}", comp.name))
            allies = taming.strongest(allies, level)
            foes = [combat.fighter_from_creature(cr, level, rank, f"e{i}", band="near") for i in range(pack_size(cr, level, rng) if pack else 1)]
            out = combat.simulate(combat.Combat(fighters=[p] + allies + foes), rng)
            n += 1; rounds += out.round - 1
            wins += out.over == "victory"
            lost += 1 - (out.player.hp / out.player.max_hp if out.over == "victory" else 0)
    return wins / n, rounds / n, lost / n


def main():
    rank = next((a for a in sys.argv[1:] if a in ("normal", "elite", "boss")), "normal")
    pack = "pack" in sys.argv[1:]
    world = load_world()
    print(f"{rank}{' pack' if pack else ''}: win% / health lost%   (rounds)")
    print(f"{'class':<9}" + "".join(f"{lv:>14}" for lv in LEVELS))
    for cls in CLASSES:
        row = []
        for lv in LEVELS:
            w, r, l = fight(world, cls, lv, rank, pack)
            row.append(f"{w:>4.0%}/{l:>3.0%} ({r:>4.1f})")
        print(f"{cls:<9}" + " ".join(f"{x:>13}" for x in row), flush=True)


if __name__ == "__main__":
    main()
