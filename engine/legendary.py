"""(f509) Legendary effects held to the code that runs them (data/rules/legendary_effects.yaml, engine/items.py LEGENDARY). An effect
is handled one of three ways: by name (the code names its id: engine/combat.py mechanics and the perks read `"hex" in A`, the scenes
read a wonder's id), by category (a slayer's or a ward's category folds into the fighter's slays or wards, engine/combat.py
fighter_from_character: the category must be one the bestiary has), or by a world mechanic (a wonder's `world` names a passive mechanic
the engine runs outside fights, core/rules.py ENGINE_WORLD_MECHANICS). An enabled effect handled no way is a promise the code cannot
keep: it must say enabled: false (and then never rolls, engine/items.py legendary_options). engine/data_check.py runs this, the
names read from the game's code (data_check.scan_code)."""
from __future__ import annotations

def how_handled(effect, named: set[str], categories: set[str], world_mechanics: set[str]) -> str:
    """'named', 'category', 'world', or '' when nothing runs it. A category or a world mechanic the game lacks counts as nothing."""
    if effect.id in named:
        return "named"
    if effect.category and effect.category in categories:
        return "category"
    if effect.world and effect.world in world_mechanics:
        return "world"
    return ""


def problems(effects: dict, named: set[str], categories: set[str], world_mechanics: set[str]) -> list[str]:
    """Every enabled effect handled; a category effect's category and a wonder's world mechanic real, enabled or not."""
    out = []
    for e in effects.values():
        if e.category and e.category not in categories:
            out.append(f"legendary_effects.yaml {e.id}: category '{e.category}' is no creature category the bestiary has")
        if e.world and e.world not in world_mechanics:
            out.append(f"legendary_effects.yaml {e.id}: world mechanic '{e.world}' is none the engine runs")
        if e.enabled and not how_handled(e, named, categories, world_mechanics):
            out.append(f"legendary_effects.yaml {e.id}: nothing runs it (no code names it, no category, no world mechanic): mark it enabled: false")
    return out
