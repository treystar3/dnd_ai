"""Show which creatures can appear in each dangerous place, and how likely each is.

Usage:
    python bestiary_check.py              every place with a danger range
    python bestiary_check.py greywood     one place
"""

import sys
from pathlib import Path

import yaml

from world.loader import WorldError, load_world

RARITY = yaml.safe_load((Path("data/rules/creatures.yaml")).read_text(encoding="utf-8"))["rarity_weight"]


def main():
    try:
        world = load_world()
    except WorldError as e:
        print(e)
        sys.exit(1)
    print(f"Bestiary: {len(world.bestiary)} creatures")
    places = [world.places[sys.argv[1]]] if len(sys.argv) > 1 else [p for p in world.places.values() if p.danger]
    for place in places:
        found = world.creature_candidates(place.id, RARITY)
        total = sum(w for _, w in found) or 1
        print(f"\n{place.name} - {place.biome}, levels {place.danger[0]}-{place.danger[1]}: {len(found)} possible creatures")
        for c, w in sorted(found, key=lambda x: -x[1]):
            group = f" in groups of {c.group[0]}-{c.group[1]}" if c.group[1] > 1 else ""
            print(f"  {100 * w / total:5.1f}%  {c.name:<26} lv {c.levels[0]}-{c.levels[1]:<4} {c.rarity:<10} {c.temperament}{group}")


if __name__ == "__main__":
    main()
