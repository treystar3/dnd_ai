"""Tune each creature family's `power` so its tricks leave fights about as hard as a plain creature of that level.

    python tools/calibrate_families.py [rounds]       rewrites data/world/families.yaml (the `power:` lines)

Method: for each family, fights against typically geared characters with the family's behaviours off and on. The metric is the share
of the character's health lost (a lost fight counts as all of it); `power` is moved toward matching the plain creature, within bounds."""
import random, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import behaviors, combat
from tools import tune
from world.loader import load_world

LV = [8, 25, 60]
LOW, HIGH = 0.7, 1.15
real = behaviors.apply


def lost_share(w, fam, on, runs=14, rank="normal"):
    behaviors.apply = real if on else (lambda f, c: None)
    total = n = 0
    for lv in LV:
        cands = [c for c in w.bestiary.values() if c.family == fam and c.levels[0] <= lv * 1.3 and c.levels[1] >= lv * 0.6 and not c.unique]
        if not cands:
            cands = [c for c in w.bestiary.values() if c.family == fam and not c.unique][:3]
        for cr in cands[:3]:
            lvl = min(max(lv, cr.levels[0]), cr.levels[1]) if cr.levels[0] > lv else lv
            for r in range(runs):
                rng = random.Random(lv * 1000 + r)
                p = combat.fighter_from_character(tune.geared(lvl, rng))
                k = tune.pack_size(cr, lvl, rng) if cr.group[0] >= 2 else 1
                foes = [combat.fighter_from_creature(cr, lvl, rank, f"e{i}", start="near") for i in range(k)]
                out = combat.simulate(combat.Combat(fighters=[p] + foes), random.Random(lv * 7 + r))
                total += 1 - (out.player.hp / out.player.max_hp if out.over == "victory" else 0)
                n += 1
    return total / max(1, n)


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    w = load_world()
    fams = behaviors.FAMILIES
    base = {f: lost_share(w, f, False) for f in fams}
    for it in range(rounds):
        worst = 0
        for f, fam in fams.items():
            on = lost_share(w, f, True)
            ratio = base[f] / max(0.05, on)
            worst = max(worst, abs(1 - ratio))
            fam["power"] = round(min(HIGH, max(LOW, fam.get("power", 1.0) * ratio ** 0.8)), 3)
            print(f"round {it + 1} {f:18} plain {base[f]:.0%} with tricks {on:.0%} -> power {fam['power']}", flush=True)
        print(f"round {it + 1}: worst gap {worst:.0%}", flush=True)
    path = Path(__file__).resolve().parent.parent / "data" / "world" / "families.yaml"
    text = path.read_text(encoding="utf-8")
    for f, fam in fams.items():
        text = re.sub(rf"(\n  {f}:\n    text: [^\n]*\n)(    power: [^\n]*\n)?", lambda m: m.group(1) + f"    power: {fam['power']}\n", text, count=1)
    path.write_text(text, encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
